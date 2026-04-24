from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config.settings import settings
from app.TgBot.services.user_service import add_coins, get_balance, get_or_create_user
from app.TgBot.keyboards.menu import balance_keyboard, main_menu_keyboard
from app.TgBot.services.user_service import (
    add_coins,
    get_balance,
    get_coin_history,
    get_or_create_user,
)

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

    await message.answer(
        f"Ваш баланс: {balance} коинов",
        reply_markup=balance_keyboard(),
    )

@router.message(F.text.startswith("/add_coins"))
async def add_coins_handler(message: Message):
    if message.from_user.id != settings.admin_id.admin_id:
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


@router.message(F.text == "🧾 История коинов")
async def coin_history(message: Message):
    items = await get_coin_history(message.from_user.id)

    if not items:
        await message.answer(
            "История коинов пока пустая.",
            reply_markup=balance_keyboard(),
        )
        return

    lines = ["🧾 История коинов:\n"]

    for item in items:
        sign = "+" if item.amount > 0 else ""

        lines.append(
            f"{sign}{item.amount} коинов\n"
            f"{item.description or item.operation_type}\n"
            f"{item.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=balance_keyboard(),
    )