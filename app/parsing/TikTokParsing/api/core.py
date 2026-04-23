import httpx
from httpx import AsyncClient, Limits
from typing import Dict, Any

from app.parsing.services.rapid.rate_limit_pass_decorator import improved_api_call
from app.parsing.errors.baseErrors import APIError
from app.config.settings import settings
from app.logger.logger import get_logger
import asyncio

# Инициализируем логгер
logger = get_logger(__name__, log_level="INFO")


class TikTokAPI:
    """
    API клиент для работы с TikTok через RapidAPI.
    Лучшие практики:
    - Context manager для автоматического управления соединениями
    - Connection pooling для эффективного использования ресурсов
    - Централизованная конфигурация таймаутов и лимитов
    - Чистый контракт: все методы возвращают Dict[str, Any] (JSON)
    """

    def __init__(self):
        self.api_key = settings.tiktok_api.api_key
        self.headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"}
        self._limits = Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        )
        self._timeout = 30.0
        # Получаем первый прокси из списка, если есть
        proxy_list = settings.proxy.proxies
        self._proxy = proxy_list[0] if proxy_list else None
        self._client = None

    async def __aenter__(self):
        """Создаём HTTP-клиент при входе в контекстный менеджер"""
        self._client = AsyncClient(
            limits=self._limits,
            timeout=self._timeout,
            proxy=self._proxy,  # None или строка вида "https://user:pass@host:port"
        )
        proxy_status = f"с прокси {self._proxy}" if self._proxy else "без прокси"
        logger.info(f"TikTok API client initialized {proxy_status}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрываем HTTP-клиент при выходе из контекстного менеджера"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("TikTok API client closed")

    @improved_api_call(platform="TT", identifier_key="params", max_retries=3)
    async def api_request(self, url: str, params: dict) -> httpx.Response:
        """
        Базовый метод для выполнения API-запросов.
        Args:
            url: Полный URL эндпоинта
            params: Параметры запроса
        Returns:
            httpx.Response: HTTP-ответ (обрабатывается декоратором)
        """
        if not self._client:
            raise RuntimeError(
                "TikTokAPI client not initialized. Use 'async with TikTokAPI() as api:'"
            )

        response = await self._client.get(url, headers=self.headers, params=params)
        return response

    async def get_info_tiktok(self, video_id: str) -> Dict[str, Any]:
        """
        Возвращает информацию о посте/видео TikTok.
        Args:
            video_id: ID видео TikTok
        Returns:
            Dict[str, Any]: JSON с данными о видео
        Raises:
            APIError: При ошибках API (пробрасывается из api_request)
        """
        url = "https://tiktok-api23.p.rapidapi.com/api/post/detail"
        params = {"videoId": video_id}

        response = await self.api_request(url, params)
        return response.json()

    async def get_user_id(self, username: str) -> Dict[str, Any]:
        """
        Получает информацию о пользователе TikTok по имени.
        Args:
            username: Уникальное имя пользователя (uniqueId)
        Returns:
            Dict[str, Any]: JSON с данными пользователя (включая secUid)
        Raises:
            APIError: При ошибках API (пробрасывается из api_request)
        """
        url = "https://tiktok-api23.p.rapidapi.com/api/user/info"
        params = {"uniqueId": username}

        response = await self.api_request(url, params)
        return response.json()

    async def get_search_tt(self, user_id: str, cursor: str | None = None) -> Dict[str, Any]:
        """
        Возвращает список видео пользователя TikTok.
        Args:
            user_id: secUid пользователя
            cursor: Курсор для пагинации (опционально)
        Returns:
            Dict[str, Any]: JSON со списком видео и метаданными пагинации
        Raises:
            APIError: При ошибках API
        """
        url = "https://tiktok-api23.p.rapidapi.com/api/user/posts"
        params = {"secUid": user_id, "count": "35", "cursor": cursor or "0"}

        response = await self.api_request(url, params)
        return response.json()