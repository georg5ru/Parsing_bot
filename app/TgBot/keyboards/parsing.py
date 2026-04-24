from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def platform_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="TikTok")],
            [KeyboardButton(text="YouTube")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def period_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 месяц")],
            [KeyboardButton(text="3 месяца")],
            [KeyboardButton(text="6 месяцев")],
            [KeyboardButton(text="До даты")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def parsing_result_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏳ Проверить статус")],
            [KeyboardButton(text="📥 Скачать таблицу")],
            [KeyboardButton(text="🔍 Новый парсинг")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )

def parsing_action_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ Общая информация")],
            [KeyboardButton(text="🎬 Парсить видео")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )