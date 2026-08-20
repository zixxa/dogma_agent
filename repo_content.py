DB_PATH = "dogma_flats.sqlite3"

DDL = """
CREATE TABLE IF NOT EXISTS flats (
    id INTEGER PRIMARY KEY,
    project_name TEXT,
    project_id INTEGER,
    price INTEGER,
    price_without_discount INTEGER,
    area REAL,
    rooms INTEGER,
    floor INTEGER,
    floors_total INTEGER,
    status_code INTEGER,
    status TEXT,
    address TEXT,
    apartment_number TEXT,
    url TEXT,
    updated_at TEXT
);
"""

UPSERT = """
INSERT INTO flats (
    id, project_name, project_id, price, price_without_discount, area, rooms,
    floor, floors_total, status_code, status, address, apartment_number,
    url, updated_at
) VALUES (
    :id, :project_name, :project_id, :price, :price_without_discount, :area, :rooms,
    :floor, :floors_total, :status_code, :status, :address, :apartment_number,
    :url, :updated_at
)
ON CONFLICT(id) DO UPDATE SET
    project_name=excluded.project_name,
    project_id=excluded.project_id,
    price=excluded.price,
    price_without_discount=excluded.price_without_discount,
    area=excluded.area,
    rooms=excluded.rooms,
    floor=excluded.floor,
    floors_total=excluded.floors_total,
    status_code=excluded.status_code,
    status=excluded.status,
    address=excluded.address,
    apartment_number=excluded.apartment_number,
    url=excluded.url,
    updated_at=excluded.updated_at;
"""
