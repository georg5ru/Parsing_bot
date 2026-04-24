from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
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


class TIKTOKAPIConfig(BaseConfig):
    api_key: str = Field(alias="TIKTOK_API_KEY")


class YOUTUBEAPIConfig(BaseConfig):
    api_key: str = Field(alias="YOUTUBE_API_KEY")


class ProxyConfig(BaseConfig):
    proxies_str: str = Field(alias="PROXIES", default="")

    @property
    def proxies(self) -> list[str]:
        if not self.proxies_str:
            return []
        return [item.strip() for item in self.proxies_str.split(",") if item.strip()]


class TelegramProxyConfig(BaseConfig):
    proxy: str = Field(alias="TELEGRAM_PROXY", default="")


class Config:
    bot_token = BOT_TOKEN()
    admin_id = ADMIN_ID()
    database_url = DATABASE_URL()

    tiktok_api = TIKTOKAPIConfig()
    youtube_api = YOUTUBEAPIConfig()

    proxy = ProxyConfig()
    telegram_proxy = TelegramProxyConfig()


settings = Config()