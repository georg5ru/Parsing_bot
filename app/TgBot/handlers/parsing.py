from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

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
)
from app.TgBot.services.pricing_service import get_mvp_parsing_cost
from app.TgBot.services.user_service import deduct_coins, get_or_create_user, has_enough_coins
from app.TgBot.states.parsing_states import ParsingStates
from app.TgBot.utils.validators import is_valid_account, normalize_account

router = Router()


def format_status(status: str) -> str:
    mapping = {
        "pending": "⏳ В очереди",
        "processing": "⚙️ В обработке",
        "done": "✅ Завершён",
        "failed": "❌ Ошибка",
        "failed_insufficient_funds": "💳 Недостаточно коинов",
    }
    return mapping.get(status, status)


@router.message(F.text == "📑 Парсинг аккаунта")
@router.message(F.text == "🔍 Новый парсинг")
async def parsing_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ParsingStates.choosing_platform)

    await message.answer(
        "Выберите платформу:",
        reply_markup=platform_keyboard(),
    )


@router.message(ParsingStates.choosing_platform, F.text == "⬅️ Назад")
async def back_from_platform(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(ParsingStates.entering_account, F.text == "⬅️ Назад")
async def back_from_account(message: Message, state: FSMContext):
    await state.set_state(ParsingStates.choosing_platform)
    await message.answer(
        "Выберите платформу:",
        reply_markup=platform_keyboard(),
    )


@router.message(ParsingStates.choosing_period, F.text == "⬅️ Назад")
async def back_from_period(message: Message, state: FSMContext):
    await state.set_state(ParsingStates.entering_account)
    await message.answer("Введите @username или ссылку на аккаунт:")


@router.message(ParsingStates.choosing_platform)
async def parsing_choose_platform(message: Message, state: FSMContext):
    if message.text not in {"TikTok", "YouTube"}:
        await message.answer("Пожалуйста, выберите платформу: TikTok или YouTube.")
        return

    await state.update_data(platform=message.text)
    await state.set_state(ParsingStates.entering_account)
    await message.answer("Введите @username или ссылку на аккаунт:")


@router.message(ParsingStates.entering_account)
async def parsing_enter_account(message: Message, state: FSMContext):
    account = message.text.strip()

    if not is_valid_account(account):
        await message.answer("Некорректный формат аккаунта. Отправьте @username или ссылку.")
        return

    data = await state.get_data()
    platform = data["platform"]

    normalized_account = normalize_account(platform, account)

    await state.update_data(account=normalized_account)
    await state.set_state(ParsingStates.choosing_period)

    await message.answer(
        f"Аккаунт сохранён: {normalized_account}\n\nВыберите период:",
        reply_markup=period_keyboard(),
    )


@router.message(ParsingStates.choosing_period)
async def parsing_choose_period(message: Message, state: FSMContext):
    allowed_periods = {"1 месяц", "3 месяца", "6 месяцев", "До даты"}

    if message.text not in allowed_periods:
        await message.answer("Пожалуйста, выберите период кнопкой.")
        return

    await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    data = await state.get_data()
    platform = data["platform"]
    account = data["account"]
    period = message.text

    active_task = await find_active_duplicate_parsing(
        tg_id=message.from_user.id,
        platform=platform,
        account=account,
        period=period,
    )

    if active_task:
        await state.clear()

        await message.answer(
            "Такой парсинг уже запущен. Проверьте статус.\n\n"
            f"Платформа: {active_task.platform}\n"
            f"Аккаунт: {active_task.account}\n"
            f"Период: {active_task.period}\n"
            f"Статус: {format_status(active_task.status)}\n"
            f"Дата: {active_task.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Повторная задача не создана, коины не списаны.",
            reply_markup=parsing_result_keyboard(),
        )
        return

    cached_task = await find_recent_cached_parsing(
        tg_id=message.from_user.id,
        platform=platform,
        account=account,
        period=period,
        hours=24,
    )

    if cached_task:
        await state.clear()

        await message.answer(
            "Данные уже есть. Показать?\n\n"
            f"Платформа: {cached_task.platform}\n"
            f"Аккаунт: {cached_task.account}\n"
            f"Период: {cached_task.period}\n"
            f"Статус: {format_status(cached_task.status)}\n"
            f"Дата: {cached_task.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Коины повторно не списываются.",
            reply_markup=parsing_result_keyboard(),
        )
        return

    parsing_cost = get_mvp_parsing_cost()

    enough_coins = await has_enough_coins(message.from_user.id, parsing_cost)

    if not enough_coins:
        task = await create_parsing(
            tg_id=message.from_user.id,
            platform=platform,
            account=account,
            period=period,
            status="failed_insufficient_funds",
        )

        await state.clear()

        await message.answer(
            "Недостаточно коинов для запуска парсинга.\n\n"
            f"Платформа: {task.platform}\n"
            f"Аккаунт: {task.account}\n"
            f"Период: {task.period}\n"
            f"Статус: {format_status(task.status)}\n"
            f"Нужно коинов: {parsing_cost}",
            reply_markup=main_menu_keyboard(),
        )
        return

    await deduct_coins(message.from_user.id, parsing_cost)

    task = await create_parsing(
        tg_id=message.from_user.id,
        platform=platform,
        account=account,
        period=period,
        status="pending",
    )

    await state.clear()

    await message.answer(
        "⏳ Парсинг запущен. Это может занять несколько минут.\n\n"
        f"Платформа: {task.platform}\n"
        f"Аккаунт: {task.account}\n"
        f"Период: {task.period}\n"
        f"Статус: {format_status(task.status)}\n"
        f"Списано коинов: {parsing_cost}",
        reply_markup=parsing_result_keyboard(),
    )


@router.message(F.text == "⏳ Проверить статус")
async def check_last_parsing_status(message: Message, state: FSMContext):
    await state.clear()

    task = await get_last_parsing(message.from_user.id)

    if not task:
        await message.answer(
            "У вас пока нет активных парсингов.",
            reply_markup=main_menu_keyboard(),
        )
        return



    text = (
        "Статус последнего парсинга:\n\n"
        f"Платформа: {task.platform}\n"
        f"Аккаунт: {task.account}\n"
        f"Период: {task.period}\n"
        f"Статус: {format_status(task.status)}"
    )

    if task.error_message:
        text += f"\nОшибка: {task.error_message}"

    await message.answer(
        text,
        reply_markup=parsing_result_keyboard(),
    )