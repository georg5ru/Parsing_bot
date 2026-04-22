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
        "Добро пожаловать в Smip_Bot 👋\n\nВыберите действие:",
        reply_markup=main_menu_keyboard(),
    )