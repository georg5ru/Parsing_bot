from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


PAGE_SIZE = 5


def my_parsings_inline_keyboard(items, page: int = 0) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]

    buttons = []

    for item in page_items:
        buttons.append([
            InlineKeyboardButton(
                text=f"{item.platform} | {item.account} | {item.period}",
                callback_data=f"parsing_detail:{item.id}:{page}",
            )
        ])

    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"parsings_page:{page - 1}",
            )
        )

    if end < len(items):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=f"parsings_page:{page + 1}",
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(
            text="🏠 В меню",
            callback_data="parsings_back_to_menu",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parsing_detail_inline_keyboard(task, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []

    if task.status == "done" and task.result_file_path and task.videos_count and task.videos_count > 0:
        buttons.append([
            InlineKeyboardButton(
                text="📥 Скачать таблицу",
                callback_data=f"download_parsing:{task.id}",
            )
        ])

    if task.status in {"failed", "failed_insufficient_funds"} or not task.videos_count:
        buttons.append([
            InlineKeyboardButton(
                text="🔁 Повторить парсинг",
                callback_data=f"repeat_parsing:{task.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ К списку",
            callback_data=f"parsings_page:{page}",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="🏠 В меню",
            callback_data="parsings_back_to_menu",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)