from typing import Any, Dict, Optional

from aiogoogle import Aiogoogle

from app.config.settings import settings
from app.logger.logger import get_logger

# Инициализируем логгер
logger = get_logger(__name__, log_level="INFO")


class YouTubeAPI:
    """
    Асинхронный YouTube API клиент для работы с YouTube Data API v3.
    Лучшие практики:
    - Context manager для автоматического управления соединениями
    - Централизованная конфигурация таймаутов
    - Чистый контракт: все методы возвращают Dict[str, Any] (JSON)
    - Ошибки обрабатываются на уровне вызывающего кода
    """

    def __init__(self):
        self.api_key = settings.youtube_api.api_key
        self.timeout = 30.0

        # Эти атрибуты будут инициализированы в __aenter__
        self._aiogoogle: Optional[Aiogoogle] = None
        self._youtube_api = None

    async def __aenter__(self):
        """Создаём HTTP-клиент и инициализируем YouTube API при входе в контекстный менеджер"""
        # Инициализация Aiogoogle (он создаст свою сессию внутри)
        self._aiogoogle = Aiogoogle(api_key=self.api_key)
        await self._aiogoogle.__aenter__()

        self._youtube_api = await self._aiogoogle.discover("youtube", "v3")

        logger.info("YouTube API client initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрываем HTTP-клиент при выходе из контекстного менеджера"""
        if self._aiogoogle:
            await self._aiogoogle.__aexit__(exc_type, exc_val, exc_tb)
            self._aiogoogle = None
            logger.info("YouTube API client closed")

    async def _make_request(self, request) -> Dict[str, Any]:
        """
        Выполняет запрос через Aiogoogle-клиент.
        Args:
            request: Объект запроса Aiogoogle
        Returns:
            Dict[str, Any]: JSON-ответ от YouTube API
        Raises:
            RuntimeError: Если клиент не инициализирован
            Exception: При ошибках API (будет обработано декоратором)
        """
        if self._aiogoogle is None or self._youtube_api is None:
            raise RuntimeError(
                "YouTubeAPI must be used as an async context manager: 'async with YouTubeAPI() as api:'"
            )

        # Aiogoogle сам выбросит исключение при ошибках - декоратор их обработает
        response = await self._aiogoogle.as_anon(request)
        return response

    async def get_channel_id(self, username: str) -> Dict[str, Any]:
        """
        Получает ID канала по имени пользователя.
        Args:
            username: Имя пользователя или часть названия канала
        Returns:
            Dict[str, Any]: JSON с результатами поиска
        Raises:
            RuntimeError: Если клиент не инициализирован
        """
        if self._youtube_api is None:
            raise RuntimeError("YouTubeAPI must be used as an async context manager")

        request = self._youtube_api.search.list(
            q=username, 
            part="snippet", 
            type="channel", 
            maxResults=10,  # Увеличиваем для лучшего охвата
            key=self.api_key
        )
        return await self._make_request(request)

    async def get_videos_from_channel(
        self, 
        channel_id: str, 
        next_page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает видео канала через uploads playlist.
        Args:
            channel_id: ID канала YouTube
            next_page_token: Токен для пагинации (опционально)
        Returns:
            Dict[str, Any]: JSON со списком видео и токеном пагинации
        Raises:
            RuntimeError: Если клиент не инициализирован
            ValueError: Если канал не найден или нет uploads playlist
        """
        if self._youtube_api is None:
            raise RuntimeError("YouTubeAPI must be used as an async context manager")

        # Шаг 1: Получить uploads playlist ID
        channels_request = self._youtube_api.channels.list(
            id=channel_id, 
            part="contentDetails",
            key=self.api_key
        )
        channel_resp = await self._make_request(channels_request)

        if not channel_resp.get("items"):
            raise ValueError(f"Channel {channel_id} not found")

        uploads_id = (
            channel_resp["items"][0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_id:
            raise ValueError(f"No uploads playlist found for channel {channel_id}")

        # Шаг 2: Получить видео из плейлиста
        playlist_params = {
            "playlistId": uploads_id,
            "part": "snippet",
            "maxResults": 50,
            "key": self.api_key
        }
        if next_page_token:
            playlist_params["pageToken"] = next_page_token

        playlist_request = self._youtube_api.playlistItems.list(**playlist_params)
        return await self._make_request(playlist_request)

    async def get_video_stats(self, video_id: str) -> Dict[str, Any]:
        """
        Получает статистику видео.
        Args:
            video_id: ID видео YouTube
        Returns:
            Dict[str, Any]: JSON со статистикой видео
        Raises:
            RuntimeError: Если клиент не инициализирован
        """
        if self._youtube_api is None:
            raise RuntimeError("YouTubeAPI must be used as an async context manager")

        request = self._youtube_api.videos.list(
            part="statistics", 
            id=video_id,
            key=self.api_key
        )
        return await self._make_request(request)

    async def get_video_details(self, video_id: str, parts: str = "snippet,statistics") -> Dict[str, Any]:
        """
        Получает детальную информацию о видео.
        Args:
            video_id: ID видео YouTube
            parts: Части данных для получения (snippet, statistics, contentDetails и т.д.)
        Returns:
            Dict[str, Any]: JSON с информацией о видео
        Raises:
            RuntimeError: Если клиент не инициализирован
        """
        if self._youtube_api is None:
            raise RuntimeError("YouTubeAPI must be used as an async context manager")

        request = self._youtube_api.videos.list(
            part=parts, 
            id=video_id,
            key=self.api_key
        )
        return await self._make_request(request)

    async def get_channel_details(self, channel_id: str, parts: str = "snippet") -> Dict[str, Any]:
        """
        Получает детальную информацию о канале.
        Args:
            channel_id: ID канала YouTube
            parts: Части данных для получения (snippet, statistics, contentDetails и т.д.)
        Returns:
            Dict[str, Any]: JSON с информацией о канале
        Raises:
            RuntimeError: Если клиент не инициализирован
        """
        if self._youtube_api is None:
            raise RuntimeError("YouTubeAPI must be used as an async context manager")

        request = self._youtube_api.channels.list(
            part=parts,
            id=channel_id,
            key=self.api_key
        )
        return await self._make_request(request)
