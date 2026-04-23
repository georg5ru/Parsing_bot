import asyncio
import re
from collections.abc import AsyncGenerator

from pydantic import HttpUrl

from app.parsing.interfaces.iByUsername import IByUsername, UserContentInfo
from app.parsing.YoutubeParsing.service.youtube_service import ServiceYouTubeScraper


class YoutubeParserByUsername(IByUsername):
    """
    Парсер YouTube, реализующий интерфейс IByUsername.
    Предоставляет унифицированный доступ к данным YouTube через сервисный слой.
    """

    def __init__(self):
        self._service = None

    async def __aenter__(self):
        """Инициализация сервиса через context manager"""
        self._service = ServiceYouTubeScraper()
        await self._service.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сервиса"""
        if self._service:
            await self._service.__aexit__(exc_type, exc_val, exc_tb)

    async def get_all_links(
            self,
            user_name: str,
            after_date: int = 0,
            key_words: set[str] = None
    ) -> AsyncGenerator[HttpUrl]:
        """
        Получает все ссылки на видео пользователя с фильтрацией.
        Args:
            user_name: Имя пользователя YouTube
            after_date: Unix timestamp начала периода
            key_words: Набор ключевых слов для фильтрации
        Yields:
            HttpUrl: Ссылки на видео
        """
        async for batch in self._service.get_all_links(user_name, after_date, key_words):
            yield batch

    async def get_all_info(
            self,
            user_name: str,
            after_date: int = 0,
            key_words: set[str] = None
    ) -> AsyncGenerator[UserContentInfo]:
        """
        Получает полную информацию о видео пользователя с фильтрацией.
        Args:
            user_name: Имя пользователя YouTube
            after_date: Unix timestamp начала периода
            key_words: Набор ключевых слов для фильтрации
        Yields:
            UserContentInfo: Информация о видео
        """
        async for batch in self._service.get_all_info(user_name, after_date, key_words):
            yield batch

    async def get_content_info(self, user_name: str, content_id: str) -> UserContentInfo:
        """
        Получает информацию о конкретном видео.
        Args:
            user_name: Имя пользователя YouTube (не используется)
            content_id: ID видео
        Returns:
            UserContentInfo: Информация о видео
        """
        return await self._service.get_content_info(user_name, content_id)

    @staticmethod
    def link_parser(link: str) -> tuple[str, str]:
        """
        Парсит ссылку YouTube и извлекает video_id.
        Поддерживаемые форматы:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        Args:
            link: Ссылка на видео YouTube
        Returns:
            tuple[str, str]: (video_id, video_id) - channel_id нужно получать через API
        Raises:
            ValueError: Если формат ссылки некорректен
        Note:
            Для получения channel_id используйте async метод info_from_link в сервисе.
        """
        # Паттерн для YouTube ссылок
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, link)

        if match:
            video_id = match.group(1)
            # Возвращаем video_id дважды, т.к. channel_id нужно получать через API
            return video_id, video_id

        raise ValueError(f"Invalid YouTube URL format: {link}")

    async def get_user_id_from_user_name(self, user_name: str) -> str:
        return await self._service.get_channel_id(user_name)


async def main():
    """
    Минималистичный тест всех методов интерфейса IByUsername.

    ⚠️ ВНИМАНИЕ: Тест выполняет реальные запросы к YouTube API.
    """
    import time
    from datetime import datetime, timezone

    # Тестовые данные
    test_username = 'MAConlygirl'  # Популярный канал для стабильных результатов
    now = int(time.time())
    one_month_ago = now - (30 * 24 * 60 * 60)  # 30 дней назад

    print("=" * 80)
    print("YOUTUBE PARSER - ТЕСТИРОВАНИЕ ИНТЕРФЕЙСА")
    print("=" * 80)
    print(f"Username: {test_username}")
    start_date = datetime.fromtimestamp(one_month_ago, tz=timezone.utc).strftime('%Y-%m-%d')
    end_date = datetime.fromtimestamp(now, tz=timezone.utc).strftime('%Y-%m-%d')
    print(f"Период: {start_date} - {end_date}")
    print("\n[1] Тест: Контекстный менеджер")
    print("-" * 80)
    try:
        async with YoutubeParserByUsername() as parser:
            print("✅ __aenter__: успешно")
            assert parser is not None, "Parser не инициализирован"
            assert parser._service is not None, "Service не инициализирован"
        print("✅ __aexit__: успешно")
    except Exception as e:
        print(f"❌ Ошибка контекстного менеджера: {e}")
        return

    # ========================================================================
    # ТЕСТ 2: get_all_info(username, after_date)
    # ========================================================================
    print("\n[2] Тест: get_all_info(username, after_date)")
    print("-" * 80)
    async with YoutubeParserByUsername() as parser:
        count = 0
        items = []
        async for item in parser.get_all_info(test_username, after_date=one_month_ago):
            assert item is not None, "Элемент генератора не должен быть None"
            assert isinstance(item, UserContentInfo), f"Ожидался UserContentInfo, получен {type(item)}"
            # Проверка периода (published должен быть >= one_month_ago)
            assert item.published >= one_month_ago, f"Видео старше периода: {item.published} < {one_month_ago}"
            items.append(item)
            count += 1
            if count >= 3:  # Ограничиваем для читаемости
                break

        print("✅ Генератор завершился корректно")
        print(f"✅ Получено элементов: {count}")
        print(f"✅ Все элементы не None: {all(item is not None for item in items)}")
        print(f"✅ Все элементы типа UserContentInfo: {all(isinstance(item, UserContentInfo) for item in items)}")

        # Вывод данных первого элемента
        if items:
            first = items[0]
            print("\n📊 Первый элемент:")
            print(f"   Link: {first.link}")
            print(f"   Views: {first.views:,}")
            print(f"   Published: {datetime.fromtimestamp(first.published, tz=timezone.utc)}")
            print(f"   Likes: {first.cnt_likes:,}")
            print(f"   Comments: {first.cnt_comments:,}")
            print(f"   Shares: {first.cnt_shares:,}")
            print(f"   Articles: {first.articles}")

    # ========================================================================
    # ТЕСТ 3: get_all_links(username, after_date)
    # ========================================================================
    print("\n[3] Тест: get_all_links(username, after_date)")
    print("-" * 80)
    async with YoutubeParserByUsername() as parser:
        count = 0
        links = []
        async for link in parser.get_all_links(test_username, after_date=one_month_ago):
            assert link is not None, "Ссылка не должна быть None"
            assert isinstance(link, HttpUrl), f"Ожидался HttpUrl, получен {type(link)}"
            links.append(str(link))
            count += 1
            if count >= 5:  # Ограничиваем для читаемости
                break

        print("✅ Генератор завершился корректно")
        print(f"✅ Получено ссылок: {count}")
        print(f"✅ Все ссылки не None: {all(link is not None for link in links)}")
        print("\n📊 Ссылки:")
        for i, link in enumerate(links, 1):
            print(f"   {i}. {link}")

    # ========================================================================
    # ТЕСТ 4: get_all_links(username, after_date, key_words)
    # ========================================================================
    print("\n[4] Тест: get_all_links(username, after_date, key_words)")
    print("-" * 80)
    async with YoutubeParserByUsername() as parser:
        keywords = {'random'}
        count = 0
        links = []

        # Проверяем, что генератор корректно завершается даже если совпадений нет
        async for link in parser.get_all_links(test_username, after_date=one_month_ago, key_words=keywords):
            assert link is not None, "Ссылка не должна быть None"
            assert isinstance(link, HttpUrl), f"Ожидался HttpUrl, получен {type(link)}"
            links.append(str(link))
            count += 1
            if count >= 5:  # Ограничиваем для читаемости
                break

        print("✅ Генератор завершился корректно (даже если совпадений нет)")
        print(f"✅ Получено ссылок с фильтрацией: {count}")
        print(f"✅ Ключевое слово: {keywords}")
        if links:
            print("\n📊 Отфильтрованные ссылки (содержат 'random'):")
            for i, link in enumerate(links, 1):
                print(f"   {i}. {link}")
        else:
            print("ℹ️  Совпадений по ключевому слову 'random' не найдено (это нормально)")
            print("   Генератор корректно завершился без ошибок")

    # ========================================================================
    # ТЕСТ 5: link_parser(link) - валидная ссылка
    # ========================================================================
    print("\n[5] Тест: link_parser(link) - валидная ссылка")
    print("-" * 80)
    test_links = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    ]
    for test_link in test_links:
        try:
            video_id_1, video_id_2 = YoutubeParserByUsername.link_parser(test_link)
            assert isinstance(video_id_1, str), f"Video ID должен быть str, получен {type(video_id_1)}"
            assert video_id_1 == video_id_2, "Для YouTube оба значения должны быть одинаковыми (video_id)"
            print(f"✅ {test_link} → Video ID: {video_id_1}")
        except ValueError as e:
            print(f"❌ Ошибка парсинга валидной ссылки: {e}")

    # ========================================================================
    # ТЕСТ 6: link_parser(link) - невалидная ссылка
    # ========================================================================
    print("\n[6] Тест: link_parser(link) - невалидная ссылка")
    print("-" * 80)
    invalid_link = "https://invalid-url.com/video/123"
    try:
        YoutubeParserByUsername.link_parser(invalid_link)
        print("❌ Ошибка: невалидная ссылка не вызвала ValueError")
    except ValueError as e:
        print("✅ Невалидная ссылка корректно вызвала ValueError")
        print(f"   Сообщение: {e}")

    # ========================================================================
    # ТЕСТ 7: get_content_info(username, content_id)
    # ========================================================================
    print("\n[7] Тест: get_content_info(username, content_id)")
    print("-" * 80)
    # Получаем реальный video_id из первого видео для теста
    async with YoutubeParserByUsername() as parser:
        try:
            # Сначала получаем одно видео, чтобы взять его video_id
            first_video = None
            async for video in parser.get_all_info(test_username, after_date=one_month_ago):
                first_video = video
                break

            if first_video:
                # Извлекаем video_id из ссылки (параметр v=)
                video_url = str(first_video.link)
                video_id = video_url.split('v=')[-1].split('&')[0] if 'v=' in video_url else video_url.split('/')[-1]

                content_info = await parser.get_content_info(test_username, video_id)
                assert content_info is not None, "Content info не должен быть None"
                assert isinstance(content_info,
                                  UserContentInfo), f"Ожидался UserContentInfoполучен {type(content_info)}"

                print("✅ get_content_info выполнен успешно")
                print("\n📊 Информация о видео:")
                print(f"   Link: {content_info.link}")
                print(f"   Views: {content_info.views:,}")
                print(f"   Published: {datetime.fromtimestamp(content_info.published, tz=timezone.utc)}")
                print(f"   Likes: {content_info.cnt_likes:,}")
                print(f"   Comments: {content_info.cnt_comments:,}")
                print(f"   Shares: {content_info.cnt_shares:,}")
                print(f"   Articles: {content_info.articles}")
                print(f"   Video ID: {video_id}")
            else:
                print("ℹ️  Не удалось получить видео для теста get_content_info")
        except Exception as e:
            print(f"❌ Ошибка при получении информации о видео: {e}")
            import traceback
            traceback.print_exc()

    # ========================================================================
    # ИТОГИ
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())
