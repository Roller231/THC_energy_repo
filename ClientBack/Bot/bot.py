import asyncio
import logging
import sys

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from environs import Env
# from DataBase import Base, engineЙ
from Handlers import CommanHandler

env = Env()
env.read_env()
bot_token = env('BOT_TOKEN')

dp = Dispatcher(storage=MemoryStorage())
dp.include_router(CommanHandler.router)


# Base.metadata.create_all(engine)

async def main() -> None:
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())