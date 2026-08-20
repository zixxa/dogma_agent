import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

import httpx
import time

from dotenv import load_dotenv

from parser_content import COMMON_FILTER, PAGE_SIZE, API_URL, HEADERS, REQUEST_DELAY_SEC, STATUS_MAP
from repo import Repo

load_dotenv()


@dataclass
class Apartment:
    id: int
    url: str | None = None
    project: str | None = None
    rooms: int | None = None
    area: float | None = None
    price: int | None = None
    floor: int | None = None


class Parser:
    BASE_URL = os.environ["BASE_URL"]

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.client = httpx.Client(headers=HEADERS, timeout=timeout)

    def __enter__(self) -> "Parser":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.__close()

    def __close(self) -> None:
        self.client.close()

    def __iter_raw_objects(self) -> Iterator[dict]:
        offset = 0
        total = None

        while total is None or offset < total:
            payload = {
                **COMMON_FILTER,
                "limit": PAGE_SIZE,
                "offset": offset,
            }

            for attempt in range(3):
                try:
                    print(f"Запрос offset={offset}, попытка {attempt + 1}/3")

                    resp = self.client.post(
                        API_URL,
                        json=payload,
                    )
                    resp.raise_for_status()
                    body = resp.json()
                    break

                except (
                        httpx.RemoteProtocolError,
                        httpx.ConnectError,
                        httpx.ReadTimeout,
                        httpx.WriteError,
                ) as e:
                    print(f"Ошибка запроса: {e}")

                    if attempt == 2:
                        raise

                    time.sleep(5)

            data = body.get("data", {})

            if total is None:
                total = data.get("count", 0)
                print(f"Всего квартир по фильтру: {total}")

            objects = data.get("objects", [])

            if not objects:
                break

            print(
                f"offset={offset}, "
                f"получено={len(objects)}"
            )

            yield from objects

            offset += PAGE_SIZE
            time.sleep(REQUEST_DELAY_SEC)

    def __normalize(self, raw: dict) -> dict:
        status_code = raw.get("status")
        price = raw.get("cost_sale") or raw.get("cost")
        flat_id = raw.get("id")

        return {
            "id": flat_id,
            "project_name": raw.get("project_name"),
            "project_id": raw.get("project_id"),
            "price": price,
            "price_without_discount": raw.get("cost"),
            "area": raw.get("area"),
            "rooms": raw.get("room"),
            "floor": raw.get("floor"),
            "floors_total": raw.get("floor_max"),
            "status_code": status_code,
            "status": STATUS_MAP.get(status_code, f"неизвестно ({status_code})"),
            "address": raw.get("address"),
            "apartment_number": raw.get("object_number"),
            "url": f"{self.BASE_URL}/flat/{flat_id}" if flat_id else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def fetch_all(self) -> list[dict]:
        """Собирает и нормализует все квартиры по текущему фильтру."""
        return [self.__normalize(raw) for raw in self.__iter_raw_objects()]


def fetch_and_store(db_path: str | None = None) -> int:
    """Разовый прогон: скачать все квартиры и сохранить в SQLite.
    Удобно вызывать из Celery-таски по расписанию."""
    repo = Repo(db_path) if db_path else Repo()
    repo.create_db()

    with Parser() as parser:
        flats = parser.fetch_all()

    return repo.save_flats(flats)


if __name__ == "__main__":
    total = fetch_and_store()
    print(f"Готово. Сохранено/обновлено записей: {total}")