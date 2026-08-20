DB_PATH = "dogma_flats.sqlite3"

DDL = """
CREATE TABLE IF NOT EXISTS flats (
    id INTEGER PRIMARY KEY,
    жк TEXT,
    project_id INTEGER,
    цена INTEGER,
    цена_без_скидки INTEGER,
    площадь REAL,
    комнат INTEGER,
    этаж INTEGER,
    этажей_в_доме INTEGER,
    статус_код INTEGER,
    статус TEXT,
    адрес TEXT,
    номер_квартиры TEXT,
    ссылка TEXT,
    обновлено TEXT
);
"""

UPSERT = """
INSERT INTO flats (
    id, жк, project_id, цена, цена_без_скидки, площадь, комнат,
    этаж, этажей_в_доме, статус_код, статус, адрес, номер_квартиры,
    ссылка, обновлено
) VALUES (
    :id, :жк, :project_id, :цена, :цена_без_скидки, :площадь, :комнат,
    :этаж, :этажей_в_доме, :статус_код, :статус, :адрес, :номер_квартиры,
    :ссылка, :обновлено
)
ON CONFLICT(id) DO UPDATE SET
    жк=excluded.жк,
    project_id=excluded.project_id,
    цена=excluded.цена,
    цена_без_скидки=excluded.цена_без_скидки,
    площадь=excluded.площадь,
    комнат=excluded.комнат,
    этаж=excluded.этаж,
    этажей_в_доме=excluded.этажей_в_доме,
    статус_код=excluded.статус_код,
    статус=excluded.статус,
    адрес=excluded.адрес,
    номер_квартиры=excluded.номер_квартиры,
    ссылка=excluded.ссылка,
    обновлено=excluded.обновлено;
"""