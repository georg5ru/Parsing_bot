from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError

from app.db.models import CoinTransaction, User
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
            await session.flush()
        else:
            user.coins += amount

        transaction = CoinTransaction(
            user_id=user.id,
            amount=amount,
            operation_type="add",
            description="Пополнение через админку",
        )
        session.add(transaction)

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

            transaction = CoinTransaction(
                user_id=user.id,
                amount=amount,
                operation_type="add",
                description="Пополнение через админку",
            )
            session.add(transaction)

            await session.commit()
            await session.refresh(user)

            return user


async def has_enough_coins(tg_id: int, required_amount: int) -> bool:
    balance = await get_balance(tg_id)
    return balance >= required_amount


async def deduct_coins(
    tg_id: int,
    amount: int,
    description: str = "Списание за парсинг",
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if not user or user.coins < amount:
            return None

        user.coins -= amount

        transaction = CoinTransaction(
            user_id=user.id,
            amount=-amount,
            operation_type="deduct",
            description=description,
        )
        session.add(transaction)

        await session.commit()
        await session.refresh(user)

        return user


async def get_coin_history(tg_id: int, limit: int = 10):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CoinTransaction)
            .join(User, CoinTransaction.user_id == User.id)
            .where(User.tg_id == tg_id)
            .order_by(desc(CoinTransaction.created_at))
            .limit(limit)
        )

        return list(result.scalars().all())