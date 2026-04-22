import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    database_url: str


bot_token = os.getenv("BOT_TOKEN")
admin_id = os.getenv("ADMIN_ID")
database_url = os.getenv("DATABASE_URL")

if not bot_token:
    raise ValueError("BOT_TOKEN не найден в .env")

if not admin_id:
    raise ValueError("ADMIN_ID не найден в .env")

if not database_url:
    raise ValueError("DATABASE_URL не найден в .env")

settings = Settings(
    bot_token=bot_token,
    admin_id=int(admin_id),
    database_url=database_url,
)