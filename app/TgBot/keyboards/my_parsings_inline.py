from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def my_parsings_inline_keyboard(items) -> InlineKeyboardMarkup:
    buttons = []

    for item in items[:10]:
        buttons.append([
            InlineKeyboardButton(
                text=f"{item.platform} | {item.account} | {item.period}",
                callback_data=f"parsing_detail:{item.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="parsings_back_to_menu",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parsing_detail_inline_keyboard(task) -> InlineKeyboardMarkup:
    buttons = []

    if task.result_file_path and task.status == "done":
        buttons.append([
            InlineKeyboardButton(
                text="📥 Скачать таблицу",
                callback_data=f"download_parsing:{task.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ К списку",
            callback_data="back_to_parsings_list",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="🏠 В меню",
            callback_data="parsings_back_to_menu",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)