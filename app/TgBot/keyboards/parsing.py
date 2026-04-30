from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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

def cached_result_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔁 Запустить заново")],
            [KeyboardButton(text="📥 Скачать прошлую таблицу")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )

def account_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def parsing_done_inline_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📥 Скачать таблицу",
                    callback_data=f"download_parsing:{task_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Общая информация",
                    callback_data=f"account_info_from_task:{task_id}",
                )
            ],
        ]
    )

def parsing_wait_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏳ Проверить статус")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def parsing_done_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Скачать таблицу")],
            [KeyboardButton(text="🔎 Новый парсинг")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def parsing_no_data_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔎 Новый парсинг")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )