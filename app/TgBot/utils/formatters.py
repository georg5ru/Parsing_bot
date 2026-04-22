def format_summary(task):
    if task.videos_count is None:
        return "Недостаточно данных"

    return (
        f"{task.videos_count} видео\n"
        f"Средний интервал: {task.avg_interval_days or 'недостаточно данных'} дней"
    )