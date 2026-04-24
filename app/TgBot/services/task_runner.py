from aiogram import Bot

from app.TgBot.keyboards.parsing import parsing_result_keyboard
from app.TgBot.services.parsing_service import (
    get_unfinished_parsings,
    process_parsing,
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

    if task.status == "done":
        await bot.send_message(
            tg_id,
            "✅ Парсинг завершён\n\n"
            f"Платформа: {task.platform}\n"
            f"Аккаунт: {task.account}\n"
            f"Период: {task.period.replace('date:', 'с ')}\n"
            f"Статус: {format_status(task.status)}\n\n"
            f"📊 {task.summary_text}",
            reply_markup=parsing_result_keyboard(),
        )
        return

    if task.status == "failed":
        await bot.send_message(
            tg_id,
            f"❌ Ошибка парсинга:\n{task.error_message}",
            reply_markup=parsing_result_keyboard(),
        )


async def resume_unfinished_tasks(bot: Bot):
    unfinished = await get_unfinished_parsings()

    for task_id, tg_id in unfinished:
        await bot.send_message(
            tg_id,
            "♻️ Бот был перезапущен. Продолжаю незавершённый парсинг.",
            reply_markup=parsing_result_keyboard(),
        )

        import asyncio
        asyncio.create_task(process_and_notify(bot, task_id, tg_id))