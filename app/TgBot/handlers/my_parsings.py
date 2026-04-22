from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.TgBot.keyboards.menu import back_keyboard, main_menu_keyboard
from app.TgBot.services.parsing_service import get_parsings

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


@router.message(F.text == "📊 Мои парсинги")
async def my_parsings(message: Message, state: FSMContext):
    await state.clear()

    items = await get_parsings(message.from_user.id)

    if not items:
        await message.answer(
            "У вас пока нет парсингов.",
            reply_markup=back_keyboard(),
        )
        return

    lines = ["📊 Ваши парсинги:\n"]

    for item in items:
        lines.append(
            f"• {item.platform} | {item.account}\n"
            f"  Период: {item.period}\n"
            f"  Статус: {format_status(item.status)}\n"
            f"  Дата: {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=back_keyboard(),
    )