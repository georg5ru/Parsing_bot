from datetime import datetime, timedelta

from sqlalchemy import desc, select
from app.db.models import ParsingTask, User
from app.db.session import AsyncSessionLocal

from app.db.models import ParsingTask, User
from app.db.session import AsyncSessionLocal
from app.TgBot.services.export_service import generate_csv, generate_excel
from app.TgBot.services.real_parsing_service import run_real_parsing
from app.TgBot.services.settings_service import get_or_create_settings
from app.TgBot.services.pricing_service import (
    get_max_videos_limit,
    get_video_parsing_cost,
)
from app.TgBot.services.user_service import deduct_coins, has_enough_coins


async def create_parsing(
    tg_id: int,
    platform: str,
    account: str,
    period: str,
    status: str = "pending",
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                tg_id=tg_id,
                username=None,
                first_name=None,
                coins=0,
            )
            session.add(user)
            await session.flush()

        task = ParsingTask(
            user_id=user.id,
            platform=platform,
            account=account,
            period=period,
            status=status,
            created_at=datetime.utcnow(),
        )

        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def process_parsing(task_id: int):
    async with AsyncSessionLocal() as session:
        task = await session.get(ParsingTask, task_id)

        if not task:
            return None

        task.status = "processing"
        await session.commit()

        try:
            data = await run_real_parsing(task)

            if not data:
                task.status = "failed"
                task.error_message = "Нет данных"
                await session.commit()
                await session.refresh(task)
                return task

            max_videos = await get_max_videos_limit()
            data = data[:max_videos]
            count = len(data)

            user_result = await session.execute(
                select(User).where(User.id == task.user_id)
            )
            user = user_result.scalar_one()

            video_cost = await get_video_parsing_cost(count)

            if not await has_enough_coins(user.tg_id, video_cost):
                task.status = "failed_insufficient_funds"
                task.error_message = (
                    f"Недостаточно коинов. Нужно ещё {video_cost} коинов "
                    f"за {count} видео."
                )
                await session.commit()
                await session.refresh(task)
                return task

            await deduct_coins(
                user.tg_id,
                video_cost,
                description=f"Видео: {task.platform} | {task.account} | {count} шт.",
            )

            data_sorted = sorted(data, key=lambda x: x.published)

            intervals = []
            for i in range(1, len(data_sorted)):
                diff = data_sorted[i].published - data_sorted[i - 1].published
                intervals.append(diff)

            avg_days = round(sum(intervals) / len(intervals) / 86400, 2) if intervals else None

            user_result = await session.execute(
                select(User).where(User.id == task.user_id)
            )
            user = user_result.scalar_one()

            user_settings = await get_or_create_settings(user.tg_id)

            if user_settings.export_format == "Excel":
                file_path = generate_excel(data, task.id)
            else:
                file_path = generate_csv(data, task.id)

            summary = (
                f"{count} видео, в среднем 1 видео каждые {avg_days} дня"
                if avg_days is not None
                else "Недостаточно данных"
            )

            task.status = "done"
            task.result_file_path = file_path
            task.summary_text = summary
            task.videos_count = count
            task.avg_interval_days = avg_days
            task.error_message = None

            await session.commit()
            await session.refresh(task)
            return task

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            await session.commit()
            await session.refresh(task)
            return task


async def get_parsings(tg_id: int):
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ParsingTask)
            .join(User, ParsingTask.user_id == User.id)
            .where(User.tg_id == tg_id)
            .order_by(desc(ParsingTask.created_at))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_last_parsing(tg_id: int):
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ParsingTask)
            .join(User, ParsingTask.user_id == User.id)
            .where(User.tg_id == tg_id)
            .order_by(desc(ParsingTask.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_parsing_by_id(task_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ParsingTask).where(ParsingTask.id == task_id)
        )
        return result.scalar_one_or_none()


async def update_parsing_status(
    task_id: int,
    new_status: str,
    error_message: str | None = None,
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ParsingTask).where(ParsingTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        task.status = new_status
        task.error_message = error_message

        await session.commit()
        await session.refresh(task)
        return task


async def save_parsing_result(
    task_id: int,
    result_file_path: str,
    summary_text: str,
    videos_count: int,
    avg_interval_days: float | None,
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ParsingTask).where(ParsingTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        task.result_file_path = result_file_path
        task.summary_text = summary_text
        task.videos_count = videos_count
        task.avg_interval_days = avg_interval_days
        task.status = "done"

        await session.commit()
        await session.refresh(task)
        return task


async def find_recent_cached_parsing(
    tg_id: int,
    platform: str,
    account: str,
    period: str,
    hours: int = 24,
):
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    async with AsyncSessionLocal() as session:
        stmt = (
            select(ParsingTask)
            .join(User, ParsingTask.user_id == User.id)
            .where(User.tg_id == tg_id)
            .where(ParsingTask.platform == platform)
            .where(ParsingTask.account == account)
            .where(ParsingTask.period == period)
            .where(ParsingTask.created_at >= cutoff)
            .order_by(desc(ParsingTask.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def find_active_duplicate_parsing(
    tg_id: int,
    platform: str,
    account: str,
    period: str,
):
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ParsingTask)
            .join(User, ParsingTask.user_id == User.id)
            .where(User.tg_id == tg_id)
            .where(ParsingTask.platform == platform)
            .where(ParsingTask.account == account)
            .where(ParsingTask.period == period)
            .where(ParsingTask.status.in_(["pending", "processing"]))
            .order_by(desc(ParsingTask.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_unfinished_parsings():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ParsingTask.id, User.tg_id)
            .join(User, ParsingTask.user_id == User.id)
            .where(ParsingTask.status.in_(["pending", "processing"]))
        )
        return result.all()


async def has_active_user_parsing(tg_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ParsingTask)
            .join(User, ParsingTask.user_id == User.id)
            .where(User.tg_id == tg_id)
            .where(ParsingTask.status.in_(["pending", "processing"]))
            .limit(1)
        )

        return result.scalar_one_or_none()