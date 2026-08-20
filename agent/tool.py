"""
Схема инструмента get_flats в формате OpenAI function calling.
"""

from parser_content import ACTIVE_PROJECT_IDS, COMPLEXES


def _complexes_description() -> str:
    parts = [f"{pid} — {COMPLEXES[pid]}" for pid in ACTIVE_PROJECT_IDS]
    return "ID ЖК. " + "; ".join(parts) + "."


TOOL = {
    "type": "function",
    "function": {
        "name": "get_flats",
        "description": (
            "Найти квартиры по бюджету, площади, ЖК и количеству комнат. "
            "Если пользователь указал ЖК, обязательно передай project_id. "
            "Студия — это rooms=0."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "min_price": {
                    "type": "number",
                    "description": "Минимальная цена квартиры, руб.",
                },
                "max_price": {
                    "type": "number",
                    "description": "Максимальная цена квартиры, руб.",
                },
                "min_area": {
                    "type": "number",
                    "description": "Минимальная площадь, м².",
                },
                "max_area": {
                    "type": "number",
                    "description": "Максимальная площадь, м².",
                },
                "project_id": {
                    "type": "integer",
                    "enum": ACTIVE_PROJECT_IDS,
                    "description": _complexes_description(),
                },
                "rooms": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Количество комнат: 0 — студия, 1 — однокомнатная, "
                        "2 — двухкомнатная и т.д. Передавай только если "
                        "пользователь явно указал."
                    ),
                },
                "top_n": {
                    "type": "integer",
                    "description": (
                        "Сколько лучших вариантов вернуть. "
                        "Например, 3 для 'топ-3', 5 для 'топ-5'. "
                        "Если пользователь не просил конкретное число — "
                        "не передавай этот параметр вообще, сервер сам "
                        "подставит разумное значение по умолчанию."
                    ),
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
}
