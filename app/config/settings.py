from pydantic import Field, PostgresDsn
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



class TIKTOKAPIConfig(BaseConfig):
    api_key: str = Field(alias="TIKTOK_API_KEY")


class YOUTUBEAPIConfig(BaseConfig):
    api_key: str = Field(alias="YOUTUBE_API_KEY")


class ProxyConfig(BaseConfig):
    proxies_str: str = Field(
        alias="PROXIES",
        default="",
        description="Прокси в формате:"
                    " https://user:pass@host:port,https://host:port"
    )

    @property
    def proxies(self) -> list[str]:
        if not self.proxies_str:
            return []
        return [item.strip() for item in self.proxies_str.split(",") if item.strip()]



class Config:
    tiktok_api = TIKTOKAPIConfig()
    proxy = ProxyConfig()
    youtube_api = YOUTUBEAPIConfig()


settings = Config()
