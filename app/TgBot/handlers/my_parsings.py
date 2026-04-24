from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.TgBot.keyboards.menu import back_keyboard, main_menu_keyboard
from app.TgBot.keyboards.my_parsings_inline import (
    my_parsings_inline_keyboard,
    parsing_detail_inline_keyboard,
)
from app.TgBot.services.parsing_service import get_parsing_by_id, get_parsings

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


def format_task_detail(task) -> str:
    text = (
        f"📄 Парсинг #{task.id}\n\n"
        f"Платформа: {task.platform}\n"
        f"Аккаунт: {task.account}\n"
        f"Период: {task.period}\n"
        f"Статус: {format_status(task.status)}\n"
        f"Дата: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    if task.summary_text:
        text += f"\n\n📊 {task.summary_text}"

    if task.error_message:
        text += f"\n\nОшибка: {task.error_message}"

    return text


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

    await message.answer(
        "📊 Выберите парсинг:",
        reply_markup=my_parsings_inline_keyboard(items),
    )


@router.callback_query(F.data.startswith("parsing_detail:"))
async def parsing_detail(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    task_id = int(callback.data.split(":")[1])
    task = await get_parsing_by_id(task_id)

    if not task:
        await callback.message.edit_text("Парсинг не найден.")
        await callback.answer()
        return

    await callback.message.edit_text(
        format_task_detail(task),
        reply_markup=parsing_detail_inline_keyboard(task),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_parsings_list")
async def back_to_parsings_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    items = await get_parsings(callback.from_user.id)

    if not items:
        await callback.message.edit_text("У вас пока нет парсингов.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "📊 Выберите парсинг:",
        reply_markup=my_parsings_inline_keyboard(items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("download_parsing:"))
async def download_parsing(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    task_id = int(callback.data.split(":")[1])
    task = await get_parsing_by_id(task_id)

    if not task or not task.result_file_path:
        await callback.answer("Файл недоступен.", show_alert=True)
        return

    file = FSInputFile(task.result_file_path)
    await callback.message.answer_document(
        file,
        caption=f"Таблица для парсинга #{task.id}",
    )
    await callback.answer()


@router.callback_query(F.data == "parsings_back_to_menu")
async def parsings_back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()