import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config.settings import settings
from app.db.init_db import init_db
from app.TgBot.handlers.balance import router as balance_router
from app.TgBot.handlers.my_parsings import router as my_parsings_router
from app.TgBot.handlers.parsing import router as parsing_router
from app.TgBot.handlers.settings import router as settings_router
from app.TgBot.handlers.start import router as start_router


async def main():
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(parsing_router)
    dp.include_router(balance_router)
    dp.include_router(my_parsings_router)
    dp.include_router(settings_router)

    await dp.start_polling(bot)


def run_bot():
    asyncio.run(main())