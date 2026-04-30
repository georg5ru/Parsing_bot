from datetime import datetime, time

from sqlalchemy import func, select

from app.db.models import CoinTransaction, ParsingTask, User
from app.db.session import AsyncSessionLocal


async def get_admin_stats():
    async with AsyncSessionLocal() as session:
        today_start = datetime.combine(datetime.utcnow().date(), time.min)

        total_users = await session.scalar(select(func.count(User.id)))

        new_today = await session.scalar(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )

        total_parsings = await session.scalar(select(func.count(ParsingTask.id)))

        done_parsings = await session.scalar(
            select(func.count(ParsingTask.id)).where(ParsingTask.status == "done")
        )

        failed_parsings = await session.scalar(
            select(func.count(ParsingTask.id)).where(ParsingTask.status == "failed")
        )

        insufficient = await session.scalar(
            select(func.count(ParsingTask.id)).where(
                ParsingTask.status == "failed_insufficient_funds"
            )
        )

        added_coins = await session.scalar(
            select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
                CoinTransaction.amount > 0
            )
        )

        spent_coins = await session.scalar(
            select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
                CoinTransaction.amount < 0
            )
        )

        return {
            "total_users": total_users or 0,
            "new_today": new_today or 0,
            "total_parsings": total_parsings or 0,
            "done_parsings": done_parsings or 0,
            "failed_parsings": failed_parsings or 0,
            "insufficient": insufficient or 0,
            "added_coins": added_coins or 0,
            "spent_coins": abs(spent_coins or 0),
        }


async def get_all_user_tg_ids():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.tg_id))
        return list(result.scalars().all())


async def get_users_page(limit: int = 10):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())