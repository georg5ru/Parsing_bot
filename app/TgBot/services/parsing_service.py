from datetime import datetime, timedelta

from sqlalchemy import desc, select

from app.db.models import ParsingTask, User
from app.db.session import AsyncSessionLocal


async def create_parsing(tg_id: int, platform: str, account: str, period: str, status: str = "pending"):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(tg_id=tg_id, coins=0)
            session.add(user)
            await session.flush()

        task = ParsingTask(
            user_id=user.id,
            platform=platform,
            account=account,
            period=period,
            status=status,
        )

        session.add(task)
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


async def update_parsing_status(task_id: int, new_status: str, error_message: str | None = None):
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


async def get_parsing_by_id(task_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ParsingTask).where(ParsingTask.id == task_id)
        )
        return result.scalar_one_or_none()


async def save_parsing_result(
    task_id: int,
    result_file_path: str,
    summary_text: str,
    videos_count: int,
    avg_interval_days: float,
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


async def get_parsing_by_id(task_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ParsingTask).where(ParsingTask.id == task_id)
        )
        return result.scalar_one_or_none()