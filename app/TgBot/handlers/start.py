from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.TgBot.keyboards.menu import main_menu_keyboard
from app.TgBot.services.user_service import get_or_create_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    await message.answer(
        "Добро пожаловать в SMIP Parser Bot — Telegram-бот для анализа аккаунтов TikTok и YouTube. \n\n Бот позволяет: \n 1) получать общую информацию об аккаунте; \n 2) парсить видео аккаунта за выбранный период; \n 3) выгружать результаты в CSV/Excel; \n 4) хранить историю парсингов; \n 5) автоматически учитывать стоимость операций через внутреннюю валюту (коины).",
        reply_markup=main_menu_keyboard(),
    )