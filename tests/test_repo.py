import pytest

from repo import Repo


def make_flat(**overrides) -> dict:
    """Фабрика записи квартиры с разумными дефолтами — в тестах
    переопределяем только то, что важно для конкретной проверки."""
    flat = {
        "id": 1,
        "project_name": "ГРЕЙД",
        "project_id": 13,
        "price": 6_000_000,
        "price_without_discount": 6_000_000,
        "area": 40.0,
        "rooms": 1,
        "floor": 5,
        "floors_total": 20,
        "status_code": 2,
        "status": "в продаже",
        "address": "ул. Тестовая",
        "apartment_number": "12",
        "url": "https://dogma.ru/flat/1",
        "updated_at": "2026-01-01T00:00:00",
    }
    flat.update(overrides)
    return flat


@pytest.fixture
def repo(tmp_path):
    db_path = str(tmp_path / "test.sqlite3")
    r = Repo(db_path)
    r.create_db()
    return r


# ---------- create_db / save_flats ----------

def test_create_db_is_idempotent(repo):
    # Повторный вызов не должен падать (CREATE TABLE IF NOT EXISTS).
    repo.create_db()
    repo.create_db()


def test_save_flats_empty_list_returns_zero(repo):
    assert repo.save_flats([]) == 0


def test_save_flats_inserts_new_rows(repo):
    saved = repo.save_flats([make_flat(id=1), make_flat(id=2)])
    assert saved == 2
    assert repo.count_flats() == 2


def test_save_flats_upserts_without_duplicating(repo):
    """Повторное сохранение той же квартиры (тот же id) не создаёт
    вторую строку, а обновляет существующую — ключевая гарантия,
    без которой повторные прогоны парсера плодили бы дубликаты."""
    repo.save_flats([make_flat(id=1, price=10_000_000)])
    repo.save_flats([make_flat(id=1, price=9_500_000)])

    rows = repo.search_flats(only_available=False)
    assert len(rows) == 1
    assert rows[0]["price"] == 9_500_000


# ---------- search_flats: базовые фильтры ----------

def test_search_flats_no_filters_returns_available_only(repo):
    repo.save_flats([
        make_flat(id=1, status_code=2),
        make_flat(id=2, status_code=3, status="забронирована"),
    ])
    rows = repo.search_flats()
    assert [r["id"] for r in rows] == [1]


def test_search_flats_status_overrides_only_available(repo):
    """Если status запрошен явно — он важнее дефолтного
    'только в продаже' (проверяли этот баг руками ранее)."""
    repo.save_flats([
        make_flat(id=1, status_code=2, status="в продаже"),
        make_flat(id=2, status_code=3, status="забронирована"),
    ])
    rows = repo.search_flats(status="забронирована")
    assert [r["id"] for r in rows] == [2]


def test_search_flats_budget_range(repo):
    repo.save_flats([
        make_flat(id=1, price=5_000_000),
        make_flat(id=2, price=7_000_000),
        make_flat(id=3, price=9_000_000),
    ])
    rows = repo.search_flats(min_price=6_000_000, max_price=8_000_000)
    assert [r["id"] for r in rows] == [2]


def test_search_flats_area_range(repo):
    repo.save_flats([
        make_flat(id=1, area=30.0),
        make_flat(id=2, area=50.0),
        make_flat(id=3, area=70.0),
    ])
    rows = repo.search_flats(min_area=40, max_area=60)
    assert [r["id"] for r in rows] == [2]


def test_search_flats_project_id_filters_correctly(repo):
    """Регрессионный тест на баг: агент присылает project_id (число),
    а не project_name (строку) — фильтр должен реально сработать."""
    repo.save_flats([
        make_flat(id=1, project_name="ГРЕЙД", project_id=13),
        make_flat(id=2, project_name="Рекорд 2", project_id=5),
    ])
    rows = repo.search_flats(project_id=13)
    assert [r["id"] for r in rows] == [1]


def test_search_flats_project_id_accepts_list(repo):
    repo.save_flats([
        make_flat(id=1, project_name="ГРЕЙД", project_id=13),
        make_flat(id=2, project_name="Рекорд 2", project_id=5),
        make_flat(id=3, project_name="РИДЗ", project_id=11),
    ])
    rows = repo.search_flats(project_id=[13, 11])
    assert {r["id"] for r in rows} == {1, 3}


def test_search_flats_project_name_case_insensitive_cyrillic(repo):
    """COLLATE NOCASE в SQLite не работает с кириллицей — эта проверка
    защищает от возврата бага, который уже один раз ловили руками."""
    repo.save_flats([make_flat(id=1, project_name="Рекорд 2")])
    rows = repo.search_flats(project_name="рекорд 2")
    assert [r["id"] for r in rows] == [1]

    rows = repo.search_flats(project_name="РЕКОРД 2")
    assert [r["id"] for r in rows] == [1]


def test_search_flats_floor_exact_and_range(repo):
    repo.save_flats([
        make_flat(id=1, floor=2),
        make_flat(id=2, floor=5),
        make_flat(id=3, floor=10),
    ])
    assert [r["id"] for r in repo.search_flats(floor=5)] == [2]
    assert {r["id"] for r in repo.search_flats(floor_min=3, floor_max=10)} == {2, 3}


def test_search_flats_rooms_accepts_single_and_list(repo):
    repo.save_flats([
        make_flat(id=1, rooms=1),
        make_flat(id=2, rooms=2),
        make_flat(id=3, rooms=3),
    ])
    assert [r["id"] for r in repo.search_flats(rooms=2)] == [2]
    assert {r["id"] for r in repo.search_flats(rooms=[1, 3])} == {1, 3}


# ---------- сортировка / limit ----------

def test_search_flats_default_order_is_price_ascending(repo):
    repo.save_flats([
        make_flat(id=1, price=9_000_000),
        make_flat(id=2, price=5_000_000),
        make_flat(id=3, price=7_000_000),
    ])
    rows = repo.search_flats()
    assert [r["id"] for r in rows] == [2, 3, 1]


def test_search_flats_limit_caps_result_count(repo):
    repo.save_flats([make_flat(id=i, price=i) for i in range(1, 11)])
    rows = repo.search_flats(limit=3)
    assert len(rows) == 3


def test_search_flats_invalid_order_by_raises(repo):
    with pytest.raises(ValueError):
        repo.search_flats(order_by="not_a_real_column")


def test_search_flats_invalid_order_dir_raises(repo):
    with pytest.raises(ValueError):
        repo.search_flats(order_dir="SIDEWAYS")


# ---------- count_flats ----------

def test_count_flats_matches_unlimited_search_length(repo):
    repo.save_flats([make_flat(id=i) for i in range(1, 6)])
    assert repo.count_flats() == len(repo.search_flats())


def test_count_flats_is_not_affected_by_limit_elsewhere(repo):
    """count_flats должен считать ВСЕ подходящие записи, даже если где-то
    рядом search_flats вызывается с limit — иначе total_count в ответе
    сервера будет врать (как в баге с '3604 квартиры')."""
    repo.save_flats([make_flat(id=i) for i in range(1, 3605)])
    total = repo.count_flats()
    sample = repo.search_flats(limit=5)
    assert total == 3604
    assert len(sample) == 5


# ---------- top_flats ----------

def test_top_flats_is_equivalent_to_search_with_limit(repo):
    repo.save_flats([make_flat(id=i, price=10_000_000 - i * 1000) for i in range(1, 11)])
    top3 = repo.top_flats(top_n=3)
    assert len(top3) == 3
    # top_flats сортирует по цене по возрастанию по умолчанию —
    # самый дешёвый (наибольший id в этой фабрике данных) должен быть первым.
    assert top3[0]["price"] <= top3[1]["price"] <= top3[2]["price"]


# ---------- list_projects ----------

def test_list_projects_returns_distinct_id_and_name(repo):
    repo.save_flats([
        make_flat(id=1, project_name="ГРЕЙД", project_id=13),
        make_flat(id=2, project_name="ГРЕЙД", project_id=13),
        make_flat(id=3, project_name="Рекорд 2", project_id=5),
    ])
    projects = repo.list_projects()
    assert {(p["project_id"], p["project_name"]) for p in projects} == {
        (13, "ГРЕЙД"),
        (5, "Рекорд 2"),
    }