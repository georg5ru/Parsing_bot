from sqlalchemy import select

from app.db.models import PricingSettings
from app.db.session import AsyncSessionLocal


async def get_pricing_settings():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PricingSettings).order_by(PricingSettings.id.asc()).limit(1)
        )
        settings = result.scalar_one_or_none()

        if settings:
            return settings

        settings = PricingSettings()
        session.add(settings)
        await session.commit()
        await session.refresh(settings)

        return settings


async def get_account_info_cost() -> int:
    settings = await get_pricing_settings()
    return settings.account_info_cost


async def get_start_parsing_cost() -> int:
    settings = await get_pricing_settings()
    return settings.parsing_start_cost


async def get_video_parsing_cost(videos_count: int) -> int:
    settings = await get_pricing_settings()
    return videos_count * settings.video_cost


async def get_max_videos_limit() -> int:
    settings = await get_pricing_settings()
    return settings.max_videos_per_parsing


async def update_pricing_setting(field: str, value: int):
    allowed_fields = {
        "account_info_cost",
        "parsing_start_cost",
        "video_cost",
        "max_videos_per_parsing",
    }

    if field not in allowed_fields:
        return None

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PricingSettings).order_by(PricingSettings.id.asc()).limit(1)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = PricingSettings()
            session.add(settings)
            await session.flush()

        setattr(settings, field, value)

        await session.commit()
        await session.refresh(settings)

        return settings