import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from agent.agent import ParserAgent

load_dotenv()

TG_BOT = os.environ["TG_BOT"]

LLM_API_KEY = os.environ["LLM_API_KEY"]

bot = Bot(TG_BOT)
dp = Dispatcher()

agent = ParserAgent(
    api_key=LLM_API_KEY,
    parser_url=os.getenv(
        "PARSER_URL",
        "http://localhost:8000",
    ),
)


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Напиши параметры квартиры, "
        "например: «2-комнатная до 10 млн, от 50 м²»."
    )


@dp.message()
async def handle_message(message: Message):
    await message.answer("Ищу квартиры...")

    try:
        answer = await agent.run(message.text)

        await message.answer(answer)

    except Exception as exc:
        await message.answer(
            f"Не удалось выполнить запрос: {exc}"
        )


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())