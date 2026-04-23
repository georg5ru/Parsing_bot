from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class UserContentInfo(BaseModel):
    articles: set[str] = Field(..., description="Артиклы из описания")
    link: HttpUrl = Field(..., description="Ссылка на контент")
    views: int = Field(..., ge=0, description="Количество просмотров")
    published: int = Field(..., ge=0, description="Дата публикации (unixtime)")
    cnt_likes: int = Field(..., ge=0, description="Количество лайков")
    cnt_comments: int = Field(..., ge=0, description="Количество комментариев")
    cnt_shares: int = Field(..., ge=0, description="Количество репостов")
    user_id: Optional[str] = Field(
        default=None,
        description="Спец id для поиска пользователя (есть не во всех платформах)"
    )


class IByUsername(ABC):

    @abstractmethod
    async def __aenter__(self):
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...

    @abstractmethod
    async def get_all_links(
            self,
            user_name: str,
            after_date: int = 0,
            key_words: set[str] = None
    ) -> AsyncGenerator[HttpUrl]:
        """
        :param user_name: Уникальный идентификатор или имя пользователя в целевой платформе
        :param after_date: Unix-время, начиная с которого следует учитывать контент.
        :param key_words: Набор ключевых слов для фильтрации контента по тексту. Если None, фильтрация по ключевым словам не выполняется.
        :return: Асинхронный генератор, возвращающий ссылки на найденный контент.
        """
        ...

    @abstractmethod
    async def get_all_info(
            self,
            user_name: str,
            after_date: int = 0,
            key_words: set[str] = None
    ) -> AsyncGenerator[UserContentInfo]:
        """
        :param user_name: Уникальный идентификатор или имя пользователя в целевой платформе
        :param after_date: Unix-время, начиная с которого следует учитывать контент.
        :param key_words: Набор ключевых слов для фильтрации контента по тексту. Если None, фильтрация по ключевым словам не выполняется.
        :return: Асинхронный генератор объектов с информацией о контенте пользователя.
        """
        ...

    @abstractmethod
    async def get_content_info(
            self,
            user_name: str,
            content_id: str,
    ) -> UserContentInfo:
        """
        Асинхронно получает информацию о контенте для указанного пользователя.

        :param user_name: Имя или идентификатор пользователя в исходном сервисе.
        :param content_id: Идентификатор единицы контента (поста, видео, статьи и т.п.).
        :return: Получение информации по определенному контенту (ролику/посту)
        """
        ...

    @staticmethod
    @abstractmethod
    def link_parser(link: str) -> tuple[str, str]:
        """
        Парсит входящую ссылку и извлекает owner_id и content_id.

        :param link: ссылка но контент (ролик)
        :return: ``(owner_id, content_id,)``
        """
        ...

    @staticmethod
    async def get_user_id_from_user_name(user_name: str) -> str:
        """
        :param user_name: Имя или идентификатор пользователя в исходном сервисе.
        :return: Возвращает user_id, нужен для некторый плтаформ (так как обычный user_name не будут работать)
        """
        return user_name
