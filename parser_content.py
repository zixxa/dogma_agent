from typing import Any

PAGE_SIZE = 100
REQUEST_DELAY_SEC = 2
API_URL = "https://service.dogma.ru/api/layouts-filter/v4/objects/filter"

COMMON_FILTER: dict[str, Any] = {
    "type": 1,
    "statuses": [2],
    "order": {
        "field": "order",
        "type": "asc"
    },
    "project_ids": [],
    "city_ids": [],
    "rooms": [],
    "layout_id": [],
    "ids": [],
    "letter_ids": [],
    "entrances_ids": [],
    "classes": [],
    "deadlines": [],
    "object_tags": [],
    "project_tags": [],
    "costs": [0, 1000000000],
    "areas": [0, 1000000000],
    "floors": [1, 24],
    "ceiling_heights": [0, 3.3],
    "window_views": [],
    "views": [],
    "glazing_types": [],
    "room_types": [],
    "kitchen_colors": [],
    "kitchen_providers": [],
    "finish_types": [],
    "rotation_angles": [],
    "loggia_count": [],
    "balcony_count": [],
    "has_balcony": None,
    "has_loggia": None,
    "has_duplex": None,
    "has_terrace": None,
    "has_stained_glass": None,
    "has_master_bedroom": None,
    "has_wardrobe": None,
    "has_kitchen_set": None,
    "ceiling_high": None,
    "limit": 12,
    "offset": 0,
    "group_by": ""
}

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://dogma.ru",
    "Referer": "https://dogma.ru/kvartiry",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

STATUS_MAP: dict[int, str] = {
    2: "в продаже",
    # 1: "?",
    # 3: "забронирована",
    # 4: "продана",
}

CITIES : dict[int, str] = {
    1:"Новороссийск",
    2:"Реутов",
    3:"Краснодар",
    4:"Пушкино",
    5:"Калуга",
    6:"Омск",
    7:"Ленинградская область"
}

COMPLEXES : dict[int, str] = {
    1: "Публицист",
    2: "ЭВО",
    3: "МКР Самолет",
    4: "DOGMA ПАРК",
    5: "Рекорд 2",
    6: "Парк Победы",
    7: "Космопарк",
    8: "Порто-Ново",
    9: "Снегири",
    10: "Догма Юкки",
    11: "РИДЗ",
    12: "САМОЛЁТ7",
    13: "ГРЕЙД",
    16: "Парк Победы 3",
}

ACTIVE_PROJECT_IDS = [3, 4, 5, 6, 11, 12, 13, 16]