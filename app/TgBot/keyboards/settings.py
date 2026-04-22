from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📁 Формат выгрузки")],
            [KeyboardButton(text="📅 Дефолтный период")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def format_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="CSV")],
            [KeyboardButton(text="Excel")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def period_settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 месяц")],
            [KeyboardButton(text="3 месяца")],
            [KeyboardButton(text="6 месяцев")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )