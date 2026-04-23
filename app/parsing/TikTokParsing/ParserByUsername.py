import asyncio
import re
from collections.abc import AsyncGenerator

from pydantic import HttpUrl

from app.parsing.interfaces.iByUsername import IByUsername, UserContentInfo
from app.parsing.TikTokParsing.service.TikTokService import ServiceTikTokScraper


class TiktokParserByUsername(IByUsername):
    """
    Парсер TikTok, реализующий интерфейс IByUsername.
    Предоставляет унифицированный доступ к данным TikTok через сервисный слой.
    """

    def __init__(self):
        self._service = None

    async def __aenter__(self):
        """Инициализация сервиса через context manager"""
        self._service = ServiceTikTokScraper()
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
            user_name: Имя пользователя TikTok
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
            user_name: Имя пользователя TikTok
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
            user_name: Имя пользователя TikTok
            content_id: ID видео
        Returns:
            UserContentInfo: Информация о видео
        """
        return await self._service.get_content_info(user_name, content_id)

    @staticmethod
    def link_parser(link: str) -> tuple[str, str]:
        """
        Парсит ссылку TikTok и извлекает username и video_id.
        Поддерживаемые форматы:
        - https://www.tiktok.com/@username/video/1234567890
        - https://vm.tiktok.com/ZMxxx/
        Args:
            link: Ссылка на видео TikTok
        Returns:
            tuple[str, str]: (username, video_id)
        Raises:
            ValueError: Если формат ссылки некорректен
        """
        # Паттерн для обычных ссылок: https://www.tiktok.com/@username/video/123456
        pattern_full = r'tiktok\.com/@([^/]+)/video/(\d+)'
        match = re.search(pattern_full, link)

        if match:
            username = match.group(1)
            video_id = match.group(2)
            return username, video_id

        # Паттерн для коротких ссылок требует разрешения через API
        # В этом случае используем синхронную обертку
        if 'vm.tiktok.com' in link or 'vt.tiktok.com' in link:
            raise ValueError(
                f"Short TikTok URLs not supported in static parser. "
                f"Use async method or resolve URL first: {link}"
            )

        raise ValueError(f"Invalid TikTok URL format: {link}")

    async def get_user_id_from_user_name(self, user_name: str) -> str:
        return await self._service.get_user_id(user_name)


async def main():
    """
    Минималистичный тест всех методов интерфейса IByUsername.

    ⚠️ ВНИМАНИЕ: Тест выполняет реальные запросы к TikTok API.
    """
    import time
    from datetime import datetime, timezone

    # Тестовые данные
    test_username = 'mrbeast'  # Популярный аккаунт для стабильных результатов
    now = int(time.time())
    one_month_ago = now - (30 * 24 * 60 * 60)  # 30 дней назад

    print("=" * 80)
    print("TIKTOK PARSER - ТЕСТИРОВАНИЕ ИНТЕРФЕЙСА")
    print("=" * 80)
    print(f"Username: {test_username}")
    start_date = datetime.fromtimestamp(one_month_ago, tz=timezone.utc).strftime('%Y-%m-%d')
    end_date = datetime.fromtimestamp(now, tz=timezone.utc).strftime('%Y-%m-%d')
    print(f"Период: {start_date} - {end_date}")
    print("=" * 80)

    # ========================================================================
    # ТЕСТ 1: Контекстный менеджер (__aenter__ / __aexit__)
    # ========================================================================
    print("\n[1] Тест: Контекстный менеджер")
    print("-" * 80)
    try:
        async with TiktokParserByUsername() as parser:
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
    async with TiktokParserByUsername() as parser:
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
    async with TiktokParserByUsername() as parser:
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
    async with TiktokParserByUsername() as parser:
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
    valid_link = "https://www.tiktok.com/@mrbeast/video/7234567890123456789"
    try:
        username, video_id = TiktokParserByUsername.link_parser(valid_link)
        assert isinstance(username, str), f"Username должен быть str, получен {type(username)}"
        assert isinstance(video_id, str), f"Video ID должен быть str, получен {type(video_id)}"
        print("✅ Валидная ссылка обработана")
        print(f"   Username: {username}")
        print(f"   Video ID: {video_id}")
    except ValueError as e:
        print(f"❌ Ошибка парсинга валидной ссылки: {e}")

    # ========================================================================
    # ТЕСТ 6: link_parser(link) - невалидная ссылка
    # ========================================================================
    print("\n[6] Тест: link_parser(link) - невалидная ссылка")
    print("-" * 80)
    invalid_link = "https://invalid-url.com/video/123"
    try:
        TiktokParserByUsername.link_parser(invalid_link)
        print("❌ Ошибка: невалидная ссылка не вызвала ValueError")
    except ValueError as e:
        print("✅ Невалидная ссылка корректно вызвала ValueError")
        print(f"   Сообщение: {e}")

    # ========================================================================
    # ТЕСТ 7: get_content_info(username, content_id)
    # ========================================================================
    print("\n[7] Тест: get_content_info(username, content_id)")
    print("-" * 80)
    test_video_id = "7587484219908115743"
    async with TiktokParserByUsername() as parser:
        try:
            content_info = await parser.get_content_info(test_username, test_video_id)
            assert content_info is not None, "Content info не должен быть None"
            expected_type = UserContentInfo
            assert isinstance(content_info, expected_type), (
                f"Ожидался UserContentInfo, получен {type(content_info)}"
            )

            print("✅ get_content_info выполнен успешно")
            print("\n📊 Информация о видео:")
            print(f"   Link: {content_info.link}")
            print(f"   Views: {content_info.views:,}")
            print(f"   Published: {datetime.fromtimestamp(content_info.published, tz=timezone.utc)}")
            print(f"   Likes: {content_info.cnt_likes:,}")
            print(f"   Comments: {content_info.cnt_comments:,}")
            print(f"   Shares: {content_info.cnt_shares:,}")
            print(f"   Articles: {content_info.articles}")
            print(f"   Video ID в ссылке: {str(content_info.link).split('/')[-1]}")
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
