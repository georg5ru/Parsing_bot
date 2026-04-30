from aiogram import Bot

from app.TgBot.keyboards.menu import main_menu_keyboard
from app.TgBot.keyboards.parsing import parsing_done_inline_keyboard
from app.TgBot.services.parsing_service import (
    get_unfinished_parsings,
    process_parsing,
)
from app.TgBot.keyboards.parsing import (
    parsing_wait_keyboard,
    parsing_done_keyboard,
    parsing_no_data_keyboard,
)


def format_status(status: str) -> str:
    return {
        "pending": "⏳ В очереди",
        "processing": "⚙️ В обработке",
        "done": "✅ Завершён",
        "failed": "❌ Ошибка",
        "failed_insufficient_funds": "💳 Недостаточно коинов",
    }.get(status, status)


async def process_and_notify(bot: Bot, task_id: int, tg_id: int):
    task = await process_parsing(task_id)

    if not task:
        return

    # успешный парсинг
    if task.status == "done":
        # если данных нет
        if "Недостаточно данных" in (task.summary_text or ""):
            await bot.send_message(
                tg_id,
                "✅ Парсинг завершён\n\n"
                f"Платформа: {task.platform}\n"
                f"Аккаунт: {task.account}\n"
                f"Период: {task.period.replace('date:', 'с ')}\n"
                f"Статус: {format_status(task.status)}\n\n"
                f"📊 {task.summary_text}",
                reply_markup=parsing_no_data_keyboard(),
            )
            return

        # обычный успешный
        await bot.send_message(
            tg_id,
            "✅ Парсинг завершён\n\n"
            f"Платформа: {task.platform}\n"
            f"Аккаунт: {task.account}\n"
            f"Период: {task.period.replace('date:', 'с ')}\n"
            f"Статус: {format_status(task.status)}\n\n"
            f"📊 {task.summary_text}",
            reply_markup=parsing_done_inline_keyboard(task.id),
        )
        return

    # ошибка
    if task.status == "failed":
        if task.error_message == "Нет данных":
            await bot.send_message(
                tg_id,
                "✅ Парсинг завершён\n\n"
                f"Платформа: {task.platform}\n"
                f"Аккаунт: {task.account}\n"
                f"Период: {task.period.replace('date:', 'с ')}\n"
                f"Статус: ✅ Завершён\n\n"
                f"📊 Недостаточно данных",
                reply_markup=parsing_no_data_keyboard(),
            )
            return

        await bot.send_message(
            tg_id,
            f"❌ Ошибка парсинга:\n{task.error_message}",
            reply_markup=main_menu_keyboard(),
        )
        return

    # недостаточно денег
    if task.status == "failed_insufficient_funds":
        await bot.send_message(
            tg_id,
            "💳 Недостаточно коинов\n\n"
            f"Платформа: {task.platform}\n"
            f"Аккаунт: {task.account}\n"
            f"Период: {task.period.replace('date:', 'с ')}\n\n"
            f"{task.error_message or 'Пополните баланс и попробуйте снова.'}",
            reply_markup=main_menu_keyboard(),
        )
        return


async def resume_unfinished_tasks(bot: Bot):
    unfinished = await get_unfinished_parsings()

    for task_id, tg_id in unfinished:
        await bot.send_message(
            tg_id,
            "♻️ Бот был перезапущен. Продолжаю незавершённый парсинг.",
            reply_markup=parsing_wait_keyboard(),
        )

        import asyncio
        asyncio.create_task(process_and_notify(bot, task_id, tg_id))