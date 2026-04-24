from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.TgBot.keyboards.menu import main_menu_keyboard
from app.TgBot.keyboards.settings import (
    format_keyboard,
    period_settings_keyboard,
    settings_keyboard,
)
from app.TgBot.services.settings_service import (
    get_or_create_settings,
    update_default_period,
    update_export_format,
)
from app.TgBot.services.user_service import get_or_create_user
from app.TgBot.states.settings_states import SettingsStates

router = Router()


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    await state.clear()

    await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    settings = await get_or_create_settings(message.from_user.id)

    await state.set_state(SettingsStates.choosing_option)
    await message.answer(
        f"Ваши настройки:\n\n"
        f"Формат выгрузки: {settings.export_format}\n"
        f"Период по умолчанию: {settings.default_period}",
        reply_markup=settings_keyboard(),
    )


@router.message(SettingsStates.choosing_option, F.text == "📁 Формат выгрузки")
async def choose_format(message: Message, state: FSMContext):
    await state.set_state(SettingsStates.choosing_format)
    await message.answer(
        "Выберите формат выгрузки:",
        reply_markup=format_keyboard(),
    )


@router.message(SettingsStates.choosing_option, F.text == "📅 Дефолтный период")
async def choose_period(message: Message, state: FSMContext):
    await state.set_state(SettingsStates.choosing_period)
    await message.answer(
        "Выберите период по умолчанию:",
        reply_markup=period_settings_keyboard(),
    )


@router.message(SettingsStates.choosing_format, F.text.in_({"CSV", "Excel"}))
async def set_format(message: Message, state: FSMContext):
    await update_export_format(message.from_user.id, message.text)
    settings = await get_or_create_settings(message.from_user.id)

    await state.set_state(SettingsStates.choosing_option)
    await message.answer(
        f"Формат обновлён: {settings.export_format}",
        reply_markup=settings_keyboard(),
    )


@router.message(SettingsStates.choosing_period, F.text.in_({"1 месяц", "3 месяца", "6 месяцев"}))
async def set_period(message: Message, state: FSMContext):
    await update_default_period(message.from_user.id, message.text)
    settings = await get_or_create_settings(message.from_user.id)

    await state.set_state(SettingsStates.choosing_option)
    await message.answer(
        f"Период обновлён: {settings.default_period}",
        reply_markup=settings_keyboard(),
    )


@router.message(
    SettingsStates.choosing_option,
    F.text == "⬅️ Назад",
)
@router.message(
    SettingsStates.choosing_format,
    F.text == "⬅️ Назад",
)
@router.message(
    SettingsStates.choosing_period,
    F.text == "⬅️ Назад",
)
async def back_from_settings(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )