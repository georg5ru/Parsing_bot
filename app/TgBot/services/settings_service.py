from sqlalchemy import select

from app.db.models import User, UserSettings
from app.db.session import AsyncSessionLocal


async def get_or_create_settings(tg_id: int):
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = user_result.scalar_one()

        settings_result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        settings = settings_result.scalar_one_or_none()

        if settings:
            return settings

        settings = UserSettings(user_id=user.id)
        session.add(settings)

        await session.commit()
        await session.refresh(settings)

        return settings


async def update_export_format(tg_id: int, export_format: str):
    async with AsyncSessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.tg_id == tg_id)
        )).scalar_one()

        settings = (await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )).scalar_one()

        settings.export_format = export_format

        await session.commit()


async def update_default_period(tg_id: int, period: str):
    async with AsyncSessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.tg_id == tg_id)
        )).scalar_one()

        settings = (await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )).scalar_one()

        settings.default_period = period

        await session.commit()  