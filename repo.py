import sqlite3
from contextlib import closing

from repo_content import DB_PATH, DDL, UPSERT


_ALLOWED_ORDER_FIELDS = {
    "цена": "цена",
    "площадь": "площадь",
    "этаж": "этаж",
    "комнат": "комнат",
    "цена_за_метр": "(цена * 1.0 / NULLIF(площадь, 0))",
}


class Repo:

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path

    def create_db(self) -> None:
        """Создаёт таблицу flats, если её ещё нет."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(DDL)
            conn.commit()

    def save_flats(self, flats: list[dict]) -> int:
        """Сохраняет (upsert по id) список нормализованных квартир.
        Возвращает количество обработанных записей."""
        if not flats:
            return 0

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executemany(UPSERT, flats)
            conn.commit()

        return len(flats)

    @staticmethod
    def _build_where(
            min_price: float | None,
            max_price: float | None,
            min_area: float | None,
            max_area: float | None,
            project_id: int | list[int] | None,
            project_name: str | list[str] | None,
            rooms: int | list[int] | None,
            floor: int | None,
            floor_min: int | None,
            floor_max: int | None,
            status: str | None,
            only_available: bool,
    ) -> tuple[str, list]:
        """Строит общий WHERE + параметры для search_flats и count_flats,
        чтобы условия фильтрации не расходились между методами."""
        clauses: list[str] = []
        params: list = []

        if min_price is not None:
            clauses.append("цена >= ?")
            params.append(min_price)
        if max_price is not None:
            clauses.append("цена <= ?")
            params.append(max_price)
        if min_area is not None:
            clauses.append("площадь >= ?")
            params.append(min_area)
        if max_area is not None:
            clauses.append("площадь <= ?")
            params.append(max_area)
        if floor is not None:
            clauses.append("этаж = ?")
            params.append(floor)
        if floor_min is not None:
            clauses.append("этаж >= ?")
            params.append(floor_min)
        if floor_max is not None:
            clauses.append("этаж <= ?")
            params.append(floor_max)

        if status is not None:
            clauses.append("LOWER_UNI(статус) = LOWER_UNI(?)")
            params.append(status)
        elif only_available:
            clauses.append("статус_код = 2")

        # Фильтр по project_id (число, надёжный вариант — совпадает с тем,
        # что теперь передаёт агент через enum в tool.py). Если передали ещё
        # и project_name (строка) — оба условия сработают через AND, так что
        # используйте что-то одно.
        if project_id is not None:
            id_values = [project_id] if isinstance(project_id, int) else list(project_id)
            placeholders = ", ".join("?" for _ in id_values)
            clauses.append(f"project_id IN ({placeholders})")
            params.extend(id_values)

        if project_name is not None:
            # COLLATE NOCASE в SQLite приводит к одному регистру только ASCII
            # (A-Z), кириллицу не трогает ("рекорд" != "Рекорд"). Поэтому
            # регистронезависимое сравнение делаем через кастомную функцию
            # LOWER_UNI, а не встроенный LOWER()/COLLATE NOCASE.
            names = [project_name] if isinstance(project_name, str) else list(project_name)
            placeholders = ", ".join("LOWER_UNI(?)" for _ in names)
            clauses.append(f"LOWER_UNI(жк) IN ({placeholders})")
            params.extend(names)

        if rooms is not None:
            room_values = [rooms] if isinstance(rooms, int) else list(rooms)
            placeholders = ", ".join("?" for _ in room_values)
            clauses.append(f"комнат IN ({placeholders})")
            params.extend(room_values)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_sql, params

    def search_flats(
            self,
            min_price: float | None = None,
            max_price: float | None = None,
            min_area: float | None = None,
            max_area: float | None = None,
            project_id: int | list[int] | None = None,
            project_name: str | list[str] | None = None,
            rooms: int | list[int] | None = None,
            floor: int | None = None,
            floor_min: int | None = None,
            floor_max: int | None = None,
            status: str | None = None,
            only_available: bool = True,
            order_by: str = "цена",
            order_dir: str = "ASC",
            limit: int | None = None,
    ) -> list[dict]:
        """Поиск квартир по фильтрам.

        min_price/max_price — диапазон цены (со скидкой, поле "цена").
        min_area/max_area     — диапазон площади в м².
        project_id             — ID ЖК (одно значение или список) — самый
                                  надёжный способ фильтрации по ЖК, т.к. не
                                  зависит от точности написания названия.
        project_name          — название ЖК (одно или список), сравнение
                                 без учёта регистра, точное совпадение.
                                 Используйте project_id, если он известен.
        rooms                 — количество комнат (одно значение или список).
        floor                 — конкретный этаж (точное совпадение).
        floor_min/floor_max   — диапазон этажей.
        status                — текст статуса ("в продаже", "забронирована"
                                 и т.п.), без учёта регистра. Если указан —
                                 имеет приоритет над only_available.
        only_available        — True: только квартиры со статус_код=2
                                 ("в продаже"); игнорируется, если задан status.
        order_by               — "цена" | "площадь" | "этаж" | "комнат" | "цена_за_метр"
        order_dir               — "ASC" | "DESC"
        limit                  — максимум записей; для топ-N просто передайте
                                  limit=3/limit=5 (сортировка — по order_by).
                                  ВАЖНО: limit=None вернёт вообще все подходящие
                                  строки — при широком фильтре это могут быть
                                  тысячи записей. На уровне HTTP-эндпоинта
                                  (server.py) сверху есть жёсткий кап — не
                                  полагайтесь только на вызывающий код.

        Возвращает список словарей — по одному на каждую строку таблицы flats.
        """
        if order_by not in _ALLOWED_ORDER_FIELDS:
            raise ValueError(
                f"order_by должен быть одним из {list(_ALLOWED_ORDER_FIELDS)}, "
                f"получено: {order_by!r}"
            )
        if order_dir.upper() not in ("ASC", "DESC"):
            raise ValueError("order_dir должен быть 'ASC' или 'DESC'")

        where_sql, params = self._build_where(
            min_price, max_price, min_area, max_area,
            project_id, project_name, rooms, floor, floor_min, floor_max,
            status, only_available,
        )

        order_sql = f"ORDER BY {_ALLOWED_ORDER_FIELDS[order_by]} {order_dir.upper()}"
        limit_sql = "LIMIT ?" if limit is not None else ""

        sql = f"SELECT * FROM flats {where_sql} {order_sql} {limit_sql}".strip()
        if limit is not None:
            params = [*params, limit]

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.create_function("LOWER_UNI", 1, lambda s: s.lower() if s is not None else s)
            rows = conn.execute(sql, params).fetchall()

        return [dict(row) for row in rows]

    def count_flats(
            self,
            min_price: float | None = None,
            max_price: float | None = None,
            min_area: float | None = None,
            max_area: float | None = None,
            project_id: int | list[int] | None = None,
            project_name: str | list[str] | None = None,
            rooms: int | list[int] | None = None,
            floor: int | None = None,
            floor_min: int | None = None,
            floor_max: int | None = None,
            status: str | None = None,
            only_available: bool = True,
    ) -> int:
        """Считает, сколько квартир подходит под фильтр — без выгрузки самих
        строк. Дёшево даже при тысячах совпадений: используется, чтобы
        честно сказать пользователю "найдено N", не таская N записей целиком."""
        where_sql, params = self._build_where(
            min_price, max_price, min_area, max_area,
            project_id, project_name, rooms, floor, floor_min, floor_max,
            status, only_available,
        )

        sql = f"SELECT COUNT(*) FROM flats {where_sql}".strip()

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.create_function("LOWER_UNI", 1, lambda s: s.lower() if s is not None else s)
            (count,) = conn.execute(sql, params).fetchone()

        return count

    def top_flats(
            self,
            min_price: float | None = None,
            max_price: float | None = None,
            min_area: float | None = None,
            max_area: float | None = None,
            project_id: int | list[int] | None = None,
            project_name: str | list[str] | None = None,
            rooms: int | list[int] | None = None,
            floor: int | None = None,
            floor_min: int | None = None,
            floor_max: int | None = None,
            status: str | None = None,
            top_n: int = 5,
            order_by: str = "цена",
            order_dir: str = "ASC",
    ) -> list[dict]:
        """Топ-N подходящих квартир по фильтрам.

        Оставлен как удобный алиас — то же самое, что
        search_flats(..., limit=top_n). По умолчанию сортирует по
        возрастанию цены (самые доступные варианты первыми).
        """
        return self.search_flats(
            min_price=min_price,
            max_price=max_price,
            min_area=min_area,
            max_area=max_area,
            project_id=project_id,
            project_name=project_name,
            rooms=rooms,
            floor=floor,
            floor_min=floor_min,
            floor_max=floor_max,
            status=status,
            order_by=order_by,
            order_dir=order_dir,
            limit=top_n,
        )

    def list_projects(self) -> list[dict]:
        """Список всех уникальных ЖК (id + название), встречающихся в базе.
        Используйте это, чтобы актуализировать enum в agent/tool.py —
        значения project_id зависят от реальных данных на dogma.ru."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT DISTINCT project_id, жк FROM flats "
                "WHERE project_id IS NOT NULL ORDER BY жк"
            ).fetchall()
        return [dict(row) for row in rows]
