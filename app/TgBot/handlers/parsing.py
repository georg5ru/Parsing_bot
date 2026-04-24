import asyncio
from datetime import datetime
from aiogram import Bot

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from app.TgBot.services.task_runner import process_and_notify

from app.TgBot.keyboards.menu import main_menu_keyboard
from app.TgBot.keyboards.parsing import (
    parsing_result_keyboard,
    period_keyboard,
    platform_keyboard,
)
from app.TgBot.services.parsing_service import (
    create_parsing,
    find_active_duplicate_parsing,
    find_recent_cached_parsing,
    get_last_parsing,
    process_parsing,
)
from app.TgBot.services.pricing_service import get_start_parsing_cost
from app.TgBot.services.user_service import (
    deduct_coins,
    get_or_create_user,
    has_enough_coins,
)
from app.TgBot.states.parsing_states import ParsingStates
from app.TgBot.utils.validators import is_valid_account, normalize_account

router = Router()


def format_status(status: str) -> str:
    return {
        "pending": "⏳ В очереди",
        "processing": "⚙️ В обработке",
        "done": "✅ Завершён",
        "failed": "❌ Ошибка",
        "failed_insufficient_funds": "💳 Недостаточно коинов",
    }.get(status, status)


@router.message(F.text == "📑 Парсинг аккаунта")
async def parsing_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(force_new=False)
    await state.set_state(ParsingStates.choosing_platform)

    await message.answer("Выберите платформу:", reply_markup=platform_keyboard())


@router.message(F.text == "🔍 Новый парсинг")
async def parsing_force_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(force_new=True)
    await state.set_state(ParsingStates.choosing_platform)

    await message.answer("Выберите платформу:", reply_markup=platform_keyboard())


@router.message(ParsingStates.choosing_platform, F.text == "⬅️ Назад")
async def back_from_platform(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())


@router.message(ParsingStates.entering_account, F.text == "⬅️ Назад")
async def back_from_account(message: Message, state: FSMContext):
    await state.set_state(ParsingStates.choosing_platform)
    await message.answer("Выберите платформу:", reply_markup=platform_keyboard())


@router.message(ParsingStates.choosing_period, F.text == "⬅️ Назад")
async def back_from_period(message: Message, state: FSMContext):
    await state.set_state(ParsingStates.entering_account)
    await message.answer("Введите @username или ссылку на аккаунт:")


@router.message(ParsingStates.entering_custom_date, F.text == "⬅️ Назад")
async def back_from_custom_date(message: Message, state: FSMContext):
    await state.set_state(ParsingStates.choosing_period)
    await message.answer("Выберите период:", reply_markup=period_keyboard())


@router.message(ParsingStates.choosing_platform)
async def parsing_choose_platform(message: Message, state: FSMContext):
    if message.text not in {"TikTok", "YouTube"}:
        await message.answer("Пожалуйста, выберите платформу.")
        return

    await state.update_data(platform=message.text)
    await state.set_state(ParsingStates.entering_account)

    await message.answer("Введите @username или ссылку на аккаунт:")


@router.message(ParsingStates.entering_account)
async def parsing_enter_account(message: Message, state: FSMContext):
    account = message.text.strip()

    if not is_valid_account(account):
        await message.answer("Некорректный формат аккаунта.")
        return

    data = await state.get_data()
    platform = data["platform"]

    normalized = normalize_account(platform, account)

    await state.update_data(account=normalized)
    await state.set_state(ParsingStates.choosing_period)

    await message.answer(
        f"Аккаунт: {normalized}\n\nВыберите период:",
        reply_markup=period_keyboard(),
    )


@router.message(ParsingStates.choosing_period)
async def parsing_choose_period(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    period_text = data.get("custom_period") or message.text

    if message.text == "До даты":
        await state.set_state(ParsingStates.entering_custom_date)
        await message.answer(
            "Введите дату в формате ДД.ММ.ГГГГ\nНапример: 01.04.2026"
        )
        return

    allowed_periods = {"1 месяц", "3 месяца", "6 месяцев"}

    if period_text not in allowed_periods and not period_text.startswith("date:"):
        await message.answer("Выберите период кнопкой.")
        return

    await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    data = await state.get_data()
    platform = data["platform"]
    account = data["account"]
    period = data.get("custom_period") or message.text
    force_new = data.get("force_new", False)

    active = await find_active_duplicate_parsing(
        message.from_user.id, platform, account, period
    )

    if active:
        await state.clear()
        await message.answer(
            "Такой парсинг уже запущен.",
            reply_markup=parsing_result_keyboard(),
        )
        return

    if not force_new:
        cached = await find_recent_cached_parsing(
            message.from_user.id, platform, account, period
        )

        if cached:
            await state.clear()
            await message.answer(
                "Данные уже есть. Коины не списаны.",
                reply_markup=parsing_result_keyboard(),
            )
            return

    cost = get_start_parsing_cost()

    if not await has_enough_coins(message.from_user.id, cost):
        await create_parsing(
            message.from_user.id,
            platform,
            account,
            period,
            status="failed_insufficient_funds",
        )

        await state.clear()
        await message.answer("Недостаточно коинов.", reply_markup=main_menu_keyboard())
        return

    await deduct_coins(
        message.from_user.id,
        cost,
        description=f"Старт парсинга: {platform} | {account}",
    )

    task = await create_parsing(
        message.from_user.id,
        platform,
        account,
        period,
        status="pending",
    )

    asyncio.create_task(
        process_and_notify(bot, task.id, message.from_user.id)
    )

    await state.clear()

    await message.answer(
        "⏳ Парсинг запущен. Это может занять несколько минут.\n\n"
        f"Платформа: {task.platform}\n"
        f"Аккаунт: {task.account}\n"
        f"Период: {task.period.replace('date:', 'с ')}\n"
        f"Статус: {format_status(task.status)}\n"
        f"Списано коинов: {cost}",
        reply_markup=parsing_result_keyboard(),
    )


@router.message(ParsingStates.entering_custom_date)
async def parsing_enter_custom_date(message: Message, state: FSMContext):
    date_text = message.text.strip()

    try:
        datetime.strptime(date_text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пример: 01.04.2026")
        return

    await state.update_data(custom_period=f"date:{date_text}")
    await state.set_state(ParsingStates.choosing_period)

    await parsing_choose_period(message, state)


@router.message(F.text == "⏳ Проверить статус")
async def check_status(message: Message, state: FSMContext):
    await state.clear()

    task = await get_last_parsing(message.from_user.id)

    if not task:
        await message.answer("Нет парсингов.", reply_markup=main_menu_keyboard())
        return

    text = (
        f"{task.platform} | {task.account}\n"
        f"{format_status(task.status)}"
    )

    if task.summary_text:
        text += f"\n\n📊 {task.summary_text}"

    if task.error_message:
        text += f"\n\nОшибка: {task.error_message}"

    await message.answer(text, reply_markup=parsing_result_keyboard())


@router.message(F.text == "📥 Скачать таблицу")
async def download_table(message: Message, state: FSMContext):
    await state.clear()

    task = await get_last_parsing(message.from_user.id)

    if not task or not task.result_file_path:
        await message.answer("Файл недоступен.", reply_markup=parsing_result_keyboard())
        return

    file = FSInputFile(task.result_file_path)
    await message.answer_document(file)


@router.message(F.text == "⬅️ Назад")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())