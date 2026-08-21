import json
import os
from typing import Any

import httpx
from openai import AsyncOpenAI

from agent.prompt import SYSTEM_PROMPT
from agent.tool import TOOL

PARSER_URL = os.getenv("PARSER_URL", "http://localhost:8000")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/free")

# Строго ограниченный системный промпт для второго, "объяснительного"
# запроса. Никакого function calling, никакого форматирования карточек —
# только короткий текст. Чем уже задача, тем меньше у модели соблазна
# "улучшить" результат по-своему (а именно это и произошло в проде:
# свободная модель построила собственную таблицу вместо summary и даже
# придумала деталь, которой не было в данных).
_EXPLANATION_SYSTEM_PROMPT = (
    "Ты пишешь короткий комментарий к подборке квартир. Не используй "
    "markdown, таблицы, списки, заголовки — только простой связный текст, "
    "1-2 предложения. Опирайся ТОЛЬКО на цифры из переданных данных "
    "(цена, площадь, этаж, price_per_sqm). Не упоминай названия полей "
    "(price, area, price_per_sqm и т.п.) — пиши обычным языком. Не "
    "придумывай никаких деталей, которых нет в данных (номер квартиры, "
    "вид из окна, инфраструктура и т.п.). Отвечай на русском."
)


class ParserAgent:
    def __init__(
            self,
            api_key: str,
            parser_url: str = PARSER_URL,
            base_url: str = LLM_BASE_URL,
            model: str = LLM_MODEL,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.parser_url = parser_url

    async def get_flats(self, **filters: Any) -> dict:
        filters = {key: value for key, value in filters.items() if value is not None}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.parser_url}/flats", params=filters)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    async def _explain(self, flats: list[dict], user_message: str) -> str:
        """Короткое объяснение "почему эти варианты хороши" — отдельным
        узким запросом, без права переформатировать сами данные."""
        payload = [
            {k: f[k] for k in ("project_name", "price", "area", "floor", "price_per_sqm") if k in f}
            for f in flats
        ]
        prompt = (
            f"Запрос пользователя: {user_message!r}\n\n"
            f"Данные о найденных квартирах (JSON): {json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _EXPLANATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            # Объяснение — приятное дополнение, а не критичная часть ответа.
            # Если LLM недоступна/ответила ошибкой — просто пропускаем его,
            # а не роняем всю выдачу квартир из-за этого.
            return ""

    def _render_flats_answer(self, tool_result: dict, explanation: str) -> str:
        """Собирает финальный текст КОДОМ, а не моделью — цена, площадь,
        этаж и ссылка (поле summary из server.py) гарантированно попадут
        в ответ пользователю независимо от того, насколько хорошо
        конкретная LLM следует инструкциям."""
        total_count = tool_result.get("total_count", 0)
        flats = tool_result.get("flats", [])

        if not flats:
            return f"По вашему запросу ничего не найдено (всего подходящих: {total_count})."

        lines = [f"Найдено подходящих квартир: {total_count}. Вот лучшие варианты:"]
        if explanation:
            lines.append("")
            lines.append(explanation)

        lines.append("")
        for i, flat in enumerate(flats, start=1):
            summary = flat.get("summary") or "(нет данных)"
            lines.append(f"{i}. {summary}")
            lines.append("")

        return "\n".join(lines).strip()

    async def run(self, user_message: str) -> str:
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[TOOL],
            temperature=0,
        )

        while True:
            message = response.choices[0].message
            tool_calls = message.tool_calls

            if not tool_calls:
                return message.content or ""

            # Добавляем ответ модели (с запросом на вызов инструмента) в историю.
            messages.append(message.model_dump(exclude_none=True))

            successful_flats_result: dict | None = None

            for call in tool_calls:
                if call.function.name != "get_flats":
                    tool_result = {
                        "success": False,
                        "error": f"Unknown tool: {call.function.name}",
                    }
                else:
                    try:
                        args = json.loads(call.function.arguments)
                    except json.JSONDecodeError as exc:
                        tool_result = {
                            "success": False,
                            "error": f"Bad tool arguments JSON: {exc}",
                        }
                    else:
                        tool_result = await self.get_flats(**args)
                        if tool_result.get("success"):
                            successful_flats_result = tool_result

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )

            if successful_flats_result is not None:
                explanation = await self._explain(
                    successful_flats_result.get("flats", []), user_message
                )
                return self._render_flats_answer(successful_flats_result, explanation)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[TOOL],
                temperature=0,
            )