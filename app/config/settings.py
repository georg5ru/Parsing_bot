from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Базовый класс для конфигурации приложения"""
    environment: str = Field(alias="ENV", default="tests")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class BOT_TOKEN(BaseConfig):
    bot_token: str = Field(alias="BOT_TOKEN")

class ADMIN_ID(BaseConfig):
    admin_id: int = Field(alias="ADMIN_ID")

class DATABASE_URL(BaseConfig):
    database_url: str = Field(alias="DATABASE_URL")

class Config:
    bot_token = BOT_TOKEN()
    admin_id = ADMIN_ID()
    database_url = DATABASE_URL()

settings = Config()