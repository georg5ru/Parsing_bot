from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import User
from app.db.session import AsyncSessionLocal


async def get_or_create_user(tg_id: int, username: str | None, first_name: str | None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if user:
            updated = False

            if user.username != username:
                user.username = username
                updated = True

            if user.first_name != first_name:
                user.first_name = first_name
                updated = True

            if updated:
                await session.commit()
                await session.refresh(user)

            return user

        user = User(
            tg_id=tg_id,
            username=username,
            first_name=first_name,
            coins=0,
        )

        session.add(user)

        try:
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()

            result = await session.execute(
                select(User).where(User.tg_id == tg_id)
            )
            user = result.scalar_one()

            updated = False

            if user.username != username:
                user.username = username
                updated = True

            if user.first_name != first_name:
                user.first_name = first_name
                updated = True

            if updated:
                await session.commit()
                await session.refresh(user)

            return user


async def get_balance(tg_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()
        return user.coins if user else 0


async def add_coins(tg_id: int, amount: int):
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
                coins=amount,
            )
            session.add(user)
        else:
            user.coins += amount

        try:
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()

            result = await session.execute(
                select(User).where(User.tg_id == tg_id)
            )
            user = result.scalar_one()
            user.coins += amount
            await session.commit()
            await session.refresh(user)
            return user


async def has_enough_coins(tg_id: int, required_amount: int) -> bool:
    balance = await get_balance(tg_id)
    return balance >= required_amount


async def deduct_coins(tg_id: int, amount: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if not user or user.coins < amount:
            return None

        user.coins -= amount
        await session.commit()
        await session.refresh(user)
        return user