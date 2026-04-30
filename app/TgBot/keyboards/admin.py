from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Админ статистика")],
            [KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="💰 Цены")],
            [KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def admin_prices_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ Цена общей информации")],
            [KeyboardButton(text="🚀 Цена старта парсинга")],
            [KeyboardButton(text="🎬 Цена за видео")],
            [KeyboardButton(text="📦 Лимит видео")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )