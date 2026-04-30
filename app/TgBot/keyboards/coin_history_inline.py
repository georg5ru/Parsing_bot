from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 5


def coin_history_keyboard(items, page: int = 0) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    buttons = []
    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"coins_page:{page - 1}",
            )
        )

    if end < len(items):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=f"coins_page:{page + 1}",
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(
            text="🏠 В меню",
            callback_data="coins_back_to_menu",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_coin_history_page(items, page: int = 0) -> str:
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]

    if not page_items:
        return "🧾 История коинов пока пустая."

    lines = [f"🧾 История коинов\nСтраница {page + 1}\n"]

    for item in page_items:
        sign = "+" if item.amount > 0 else ""

        lines.append(
            f"{sign}{item.amount} коинов\n"
            f"{item.description or item.operation_type}\n"
            f"{item.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    return "\n".join(lines)