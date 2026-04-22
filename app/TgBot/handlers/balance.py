from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config.settings import settings
from app.TgBot.services.user_service import add_coins, get_balance, get_or_create_user

router = Router()


@router.message(F.text == "💳 Баланс")
async def show_balance(message: Message, state: FSMContext):
    await state.clear()

    await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    balance = await get_balance(message.from_user.id)
    await message.answer(f"Ваш баланс: {balance} коинов")


@router.message(F.text.startswith("/add_coins"))
async def add_coins_handler(message: Message):
    if message.from_user.id != settings.admin_id:
        await message.answer("Нет доступа")
        return

    parts = message.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Используй: /add_coins 100")
        return

    amount = int(parts[1])

    await add_coins(message.from_user.id, amount)
    new_balance = await get_balance(message.from_user.id)

    await message.answer(
        f"Добавлено {amount} коинов.\n"
        f"Новый баланс: {new_balance}"
    )