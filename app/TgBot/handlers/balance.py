from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import CallbackQuery

from app.config.settings import settings
from app.TgBot.services.user_service import add_coins

from app.TgBot.keyboards.coin_history_inline import (
    coin_history_keyboard,
    format_coin_history_page,
)

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

    if len(parts) == 2:
        tg_id = message.from_user.id
        amount_text = parts[1]

    elif len(parts) == 3:
        if not parts[1].isdigit():
            await message.answer("ID пользователя должен быть числом.")
            return

        tg_id = int(parts[1])
        amount_text = parts[2]

    else:
        await message.answer(
            "Используй:\n"
            "/add_coins 100 — себе\n"
            "/add_coins 1426158670 100 — пользователю"
        )
        return

    if not amount_text.isdigit():
        await message.answer("Количество коинов должно быть числом.")
        return

    amount = int(amount_text)

    if amount <= 0:
        await message.answer("Количество коинов должно быть больше 0.")
        return

    user = await add_coins(tg_id, amount)

    await message.answer(
        f"✅ Добавлено {amount} коинов.\n"
        f"Пользователь ID: {tg_id}\n"
        f"Новый баланс: {user.coins}"
    )


@router.message(F.text == "🧾 История коинов")
async def coin_history(message: Message):
    items = await get_coin_history(message.from_user.id, limit=100)

    await message.answer(
        format_coin_history_page(items, page=0),
        reply_markup=coin_history_keyboard(items, page=0),
    )


@router.callback_query(F.data.startswith("coins_page:"))
async def coin_history_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])

    items = await get_coin_history(callback.from_user.id, limit=100)

    await callback.message.edit_text(
        format_coin_history_page(items, page=page),
        reply_markup=coin_history_keyboard(items, page=page),
    )

    await callback.answer()


@router.callback_query(F.data == "coins_back_to_menu")
async def coins_back_to_menu(callback: CallbackQuery):
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )

    await callback.answer()