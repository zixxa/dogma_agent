import logging

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from repo import Repo

logger = logging.getLogger("dogma_flats_server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="dogma-flats-parser")
repo = Repo()

DEFAULT_TOP_N = 5
MAX_TOP_N = 20

_PUBLIC_FIELDS = (
    "project_name", "price", "area", "rooms", "floor", "status", "url",
)

_ROOMS_LABEL = {0: "Студия"}


def _rooms_label(rooms) -> str:
    if rooms is None:
        return ""
    return _ROOMS_LABEL.get(rooms, f"{rooms}-комн.")


def _to_public(flat: dict) -> dict:
    public = {k: flat[k] for k in _PUBLIC_FIELDS if k in flat}

    price, area = flat.get("price"), flat.get("area")
    if price is not None and area:
        public["price_per_sqm"] = round(price / area)

    parts = [flat.get("project_name") or "ЖК не указан"]
    if rooms_part := _rooms_label(flat.get("rooms")):
        parts.append(rooms_part)
    header = ", ".join(parts)

    price_str = f"{price:,.0f} ₽".replace(",", " ") if price is not None else "цена не указана"
    area_str = f"{area} м²" if area is not None else "площадь не указана"
    floor_str = f"этаж {flat['floor']}" if flat.get("floor") is not None else "этаж не указан"
    url_str = flat.get("url") or ""

    public["summary"] = f"{header} — {price_str}, {area_str}, {floor_str}\n{url_str}".strip()

    return public


@app.on_event("startup")
def on_startup() -> None:
    repo.create_db()


@app.get("/flats")
def get_flats(
        project_id: int | None = Query(None, description="ID ЖК"),
        min_price: float | None = Query(None, description="Минимальная цена, руб."),
        max_price: float | None = Query(None, description="Максимальная цена, руб."),
        min_area: float | None = Query(None, description="Минимальная площадь, м²"),
        max_area: float | None = Query(None, description="Максимальная площадь, м²"),
        rooms: int | None = Query(None, ge=0, description="Количество комнат (0 = студия)"),
        top_n: int | None = Query(None, description="Сколько лучших вариантов вернуть"),
):
    safe_top_n = DEFAULT_TOP_N if top_n is None else max(1, min(top_n, MAX_TOP_N))

    filters = dict(
        project_id=project_id,
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        rooms=rooms,
    )

    try:
        total_count = repo.count_flats(**filters)
        flats = repo.search_flats(**filters, limit=safe_top_n)
    except ValueError as exc:
        # Неверные параметры запроса (например, некорректный order_by) —
        # это ошибка вызывающей стороны, отдаём как есть.
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(exc)},
        )
    except Exception:
        logger.exception("Ошибка при выполнении /flats с фильтрами: %s", filters)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "internal server error"},
        )

    return {
        "success": True,
        "total_count": total_count,
        "returned_count": len(flats),
        "flats": [_to_public(f) for f in flats],
    }


@app.get("/projects")
def get_projects():
    return {"projects": repo.list_projects()}