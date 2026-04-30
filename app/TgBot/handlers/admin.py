from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config.settings import settings
from app.TgBot.keyboards.admin import admin_keyboard, admin_prices_keyboard
from app.TgBot.keyboards.menu import main_menu_keyboard
from app.TgBot.services.admin_service import (
    get_admin_stats,
    get_all_user_tg_ids,
    get_users_page,
)
from app.TgBot.services.pricing_service import (
    get_pricing_settings,
    update_pricing_setting,
)

from app.TgBot.states.admin_states import AdminStates

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id.admin_id


@router.message(F.text == "/admin")
async def admin_start(message: Message, state: FSMContext):
    await state.clear()

    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    await message.answer(
        "Админ-панель:",
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "📊 Админ статистика")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    stats = await get_admin_stats()

    await message.answer(
        "📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🆕 Новых сегодня: {stats['new_today']}\n\n"
        f"📂 Всего парсингов: {stats['total_parsings']}\n"
        f"✅ Успешных: {stats['done_parsings']}\n"
        f"❌ Ошибок: {stats['failed_parsings']}\n"
        f"💳 Недостаточно коинов: {stats['insufficient']}\n\n"
        f"💸 Выдано коинов: {stats['added_coins']}\n"
        f"🪙 Списано коинов: {stats['spent_coins']}",
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "📢 Рассылка")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(AdminStates.waiting_broadcast_text)
    await message.answer(
        "Введите текст рассылки:",
        reply_markup=admin_keyboard(),
    )


@router.message(AdminStates.waiting_broadcast_text)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()

    if text == "⬅️ Назад":
        await state.clear()
        await message.answer("Админ-панель:", reply_markup=admin_keyboard())
        return

    users = await get_all_user_tg_ids()

    success = 0
    failed = 0

    for tg_id in users:
        try:
            await bot.send_message(
                tg_id,
                f"📢 Уведомление\n\n{text}",
            )
            success += 1
        except Exception:
            failed += 1

    await state.clear()

    await message.answer(
        f"Рассылка завершена.\n\n"
        f"✅ Отправлено: {success}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "👥 Пользователи")
async def admin_users(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = await get_users_page(limit=10)

    if not users:
        await message.answer("Пользователей пока нет.", reply_markup=admin_keyboard())
        return

    lines = ["👥 Последние пользователи:\n"]

    for user in users:
        lines.append(
            f"ID: {user.tg_id}\n"
            f"Username: @{user.username if user.username else 'нет'}\n"
            f"Имя: {user.first_name or 'нет'}\n"
            f"Коины: {user.coins}\n"
            f"Дата: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=admin_keyboard(),
    )


@router.message(F.text == "⬅️ Назад")
async def admin_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())


@router.message(F.text == "💰 Цены")
async def admin_prices(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()

    prices = await get_pricing_settings()

    await message.answer(
        "💰 Текущие цены\n\n"
        f"ℹ️ Общая информация: {prices.account_info_cost} коин(ов)\n"
        f"🚀 Старт парсинга: {prices.parsing_start_cost} коин(ов)\n"
        f"🎬 За видео: {prices.video_cost} коин(ов)\n"
        f"📦 Лимит видео: {prices.max_videos_per_parsing}",
        reply_markup=admin_prices_keyboard(),
    )


@router.message(
    F.text.in_({
        "ℹ️ Цена общей информации",
        "🚀 Цена старта парсинга",
        "🎬 Цена за видео",
        "📦 Лимит видео",
    })
)
async def admin_choose_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    mapping = {
        "ℹ️ Цена общей информации": "account_info_cost",
        "🚀 Цена старта парсинга": "parsing_start_cost",
        "🎬 Цена за видео": "video_cost",
        "📦 Лимит видео": "max_videos_per_parsing",
    }

    await state.update_data(price_field=mapping[message.text])
    await state.set_state(AdminStates.waiting_price_value)

    await message.answer(
        "Введите новое значение числом:",
        reply_markup=admin_prices_keyboard(),
    )


@router.message(AdminStates.waiting_price_value)
async def admin_set_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text == "⬅️ Назад":
        await state.clear()
        await admin_prices(message, state)
        return

    if not message.text.isdigit():
        await message.answer("Введите целое число.")
        return

    value = int(message.text)

    if value < 0:
        await message.answer("Значение не может быть меньше 0.")
        return

    data = await state.get_data()
    field = data.get("price_field")

    updated = await update_pricing_setting(field, value)

    await state.clear()

    if not updated:
        await message.answer("Не удалось обновить цену.", reply_markup=admin_keyboard())
        return

    await message.answer(
        "✅ Настройка обновлена.",
        reply_markup=admin_keyboard(),
    )

    await admin_prices(message, state)