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

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[TOOL],
                temperature=0,
            )
