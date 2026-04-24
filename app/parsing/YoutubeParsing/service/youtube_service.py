import datetime
import re
from typing import Optional, AsyncGenerator

from pydantic import HttpUrl

from app.parsing.YoutubeParsing.api.core import YouTubeAPI
from app.services.date_service import convert_utc_to_moscow_time, convert_iso_utc_to_moscow
from app.parsing.errors.baseErrors import APIError
from app.parsing.interfaces.iByUsername import UserContentInfo, UserChannelInfo
from app.parsing.services.articles_services import fetch_articles
from app.logger.logger import get_logger

# Инициализируем логгер
logger = get_logger(__name__, log_level="INFO")

moscow_tz = datetime.timezone(datetime.timedelta(hours=3))


class ServiceYouTubeScraper:
    """
    Сервис для работы с YouTube Data API.
    Лучшие практики:
    - Context manager для автоматического управления ресурсами
    - Обработка APIError из декоратора
    - Централизованное логирование
    - Type hints для всех методов
    """

    def __init__(self):
        self.api: Optional[YouTubeAPI] = None

    @staticmethod
    def _supports_user_id_field() -> bool:
        if hasattr(UserContentInfo, "model_fields"):
            return "user_id" in UserContentInfo.model_fields
        return "user_id" in getattr(UserContentInfo, "__fields__", {})

    def _build_content_info(
            self,
            *,
            articles: set[str],
            link: str,
            views: int,
            published: int,
            cnt_likes: int,
            cnt_comments: int,
            cnt_shares: int,
            user_id: Optional[str] = None,
    ) -> UserContentInfo:
        data = {
            "articles": articles,
            "link": link,
            "views": views,
            "published": published,
            "cnt_likes": cnt_likes,
            "cnt_comments": cnt_comments,
            "cnt_shares": cnt_shares,
        }
        if user_id and self._supports_user_id_field():
            data["user_id"] = user_id
        return UserContentInfo(**data)

    @staticmethod
    def _is_youtube_channel_id(value: str) -> bool:
        if not value:
            return False
        if not value.startswith("UC"):
            return False
        return len(value) == 24

    async def __aenter__(self):
        """Инициализация API клиента через context manager"""
        self.api = await YouTubeAPI().__aenter__()
        logger.info("ServiceYouTubeScraper initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие API клиента"""
        if self.api:
            await self.api.__aexit__(exc_type, exc_val, exc_tb)
            logger.info("ServiceYouTubeScraper closed")

    async def get_channel_id(self, username: str) -> Optional[str]:
        clean_username = username.strip().lstrip("@").split("/")[0]
        """
                Получает ID канала по имени пользователя.

                Использует многоуровневую проверку:
                1. Поиск по handle (@username)
                2. Точное совпадение channelTitle
                3. Проверка customUrl (если доступен)
                4. Частичное совпадение channelTitle (fallback)

                Args:
                    username: Имя пользователя YouTube (с @ или без)

                Returns:
                    Optional[str]: ID канала или None если не найден
                """
        

        try:
            # 1. Если уже пришёл channel_id
            if self._is_youtube_channel_id(clean_username):
                return clean_username

            # 2. Точный поиск по handle через channels.list(forHandle=...)
            try:
                response = await self.api.get_channel_by_handle(clean_username)
                items = response.get("items", [])

                if items:
                    channel_id = items[0].get("id")
                    if channel_id:
                        logger.info(
                            f"Найден канал по handle для {username}: {channel_id}"
                        )
                        return channel_id
            except Exception as e:
                logger.warning(
                    f"Не удалось получить канал по handle для {username}: {e}"
                )

            # 3. Fallback: старый поиск
            search_queries = [f"@{clean_username}", clean_username]
            username_lower = clean_username.lower()

            for search_query in search_queries:
                response = await self.api.get_channel_id(search_query)
                items = response.get("items", [])

                if not items:
                    continue

                for item in items:
                    channel_id = item.get("id", {}).get("channelId")
                    snippet = item.get("snippet", {})
                    channel_title = snippet.get("channelTitle", "").lower()

                    if not channel_id:
                        continue

                    try:
                        channel_info = await self.api.get_channel_details(
                            channel_id,
                            parts="snippet",
                        )
                        if channel_info.get("items"):
                            custom_url = (
                                channel_info["items"][0]
                                .get("snippet", {})
                                .get("customUrl", "")
                                .lstrip("@")
                                .lower()
                            )

                            if custom_url == username_lower:
                                logger.info(
                                    f"Найден канал по customUrl для {username}: {channel_id}"
                                )
                                return channel_id
                    except Exception:
                        pass

                    if channel_title == username_lower:
                        return channel_id

            logger.warning(f"Канал не найден для пользователя {username}")
            return None

        except APIError as e:
            logger.error(
                f"API ошибка при получении channel_id для {username}: "
                f"[{e.platform}] {e.status_code} - {e.message}"
            )
            return None

        except Exception as e:
            logger.exception(
                f"Неожиданная ошибка при получении channel_id для {username}: {e}"
            )
            return None

    async def fetch_videos(
            self,
            channel_id: str,
            start_time: datetime.datetime
    ) -> list[tuple[UserContentInfo, str]]:
        """
        Получает все видео канала после start_time с пагинацией.
        Args:
            channel_id: ID канала YouTube
            start_time: Время начала фильтрации
        Returns:
            list[tuple[UserContentInfo, str]]: Список кортежей (информация о видео, описание)
        """
        videos = []
        next_page_token = None

        try:
            while True:
                try:
                    response = await self.api.get_videos_from_channel(channel_id, next_page_token)
                except APIError as e:
                    logger.error(
                        f"API ошибка при получении видео для канала {channel_id}: "
                        f"[{e.platform}] {e.status_code} - {e.message}"
                    )
                    break
                except ValueError as e:
                    # Канал не найден или нет uploads playlist
                    logger.error(f"Ошибка получения видео для канала {channel_id}: {e}")
                    break
                except Exception as e:
                    logger.exception(f"Неожиданная ошибка при получении видео для канала {channel_id}: {e}")
                    break

                items = response.get('items', [])

                if not items:
                    logger.info(f"Дополнительные видео для канала {channel_id} не найдены")
                    break

                for video in items:
                    if self.should_stop_processing(video, start_time):
                        logger.info(f"Остановлена обработка: видео старше {start_time}")
                        return videos

                    processed = await self.process_video(video, channel_id=channel_id)
                    if processed:
                        # Сохраняем description для фильтрации
                        snippet = video.get('snippet', {})
                        description = snippet.get('description', '') or snippet.get('title', '')
                        videos.append((processed, description))

                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    logger.info(f"Достигнут конец списка видео для канала {channel_id}")
                    break

            return videos

        except Exception as e:
            logger.exception(f"Критическая ошибка при фильтрации видео для канала {channel_id}: {e}")
            return []

    def should_stop_processing(self, video: dict, start_time: datetime.datetime) -> bool:
        """
        Определяет, стоит ли завершить обработку видео.
        Args:
            video: Данные видео из API
            start_time: Время начала фильтрации
        Returns:
            bool: True если нужно остановить обработку
        """
        published_str = video.get('snippet', {}).get('publishedAt')
        published = convert_iso_utc_to_moscow(published_str)
        return published < start_time

    async def process_video(
            self,
            video: dict,
            channel_id: Optional[str] = None,
    ) -> Optional[UserContentInfo]:
        """
        Обрабатывает одно видео, возвращает UserContentInfo.
        Args:
            video: Данные видео из API
        Returns:
            Optional[UserContentInfo]: Информация о видео или None если не подходит
        """
        try:
            snippet = video.get('snippet', {})
            published = convert_iso_utc_to_moscow(snippet.get('publishedAt'))
            video_id = snippet.get('resourceId', {}).get('videoId')
            title = snippet.get('title', '')

            if not video_id:
                logger.warning("Пропущено видео без videoId")
                return None

            # Получаем статистику видео
            stats = await self.get_video_stats(video_id)

            def safe_int(value: str | None, default: int = 0) -> int:
                """Безопасное преобразование в int"""
                if value is None:
                    return default
                try:
                    return max(0, int(value))
                except (ValueError, TypeError):
                    return default

            views = safe_int(stats.get('viewCount'))
            cnt_likes = safe_int(stats.get('likeCount'))
            cnt_comments = safe_int(stats.get('commentCount'))
            cnt_shares = safe_int(stats.get('favoriteCount'))

            articles = fetch_articles(title)
            link = f"https://www.youtube.com/shorts/{video_id}"

            # Преобразуем datetime в unixtime
            published_unix = int(published.timestamp())

            return self._build_content_info(
                articles=articles,
                views=views,
                cnt_likes=cnt_likes,
                cnt_comments=cnt_comments,
                cnt_shares=cnt_shares,
                link=link,
                published=published_unix,
                user_id=channel_id,
            )

        except KeyError as e:
            logger.error(f"Отсутствует обязательное поле в данных видео: {e}")
            return None
        except Exception as e:
            logger.exception(f"Ошибка при обработке видео: {e}")
            return None

    async def get_video_stats(self, video_id: str) -> dict:
        """
        Получает статистику видео.
        Args:
            video_id: ID видео YouTube
        Returns:
            dict: Статистика видео (viewCount, likeCount и т.д.)
        """
        try:
            response = await self.api.get_video_stats(video_id)
            if "items" in response and response["items"]:
                return response["items"][0]["statistics"]
            else:
                logger.warning(f"Статистика для видео {video_id} недоступна")
                return {
                    'viewCount': '0',
                    'likeCount': '0',
                    'commentCount': '0',
                    'favoriteCount': '0'
                }
        except APIError as e:
            logger.error(
                f"API ошибка при получении статистики для видео {video_id}: "
                f"[{e.platform}] {e.status_code} - {e.message}"
            )
            return {
                'viewCount': '0',
                'likeCount': '0',
                'commentCount': '0',
                'favoriteCount': '0'
            }
        except Exception as e:
            logger.exception(f"Ошибка при получении статистики для видео {video_id}: {e}")
            return {
                'viewCount': '0',
                'likeCount': '0',
                'commentCount': '0',
                'favoriteCount': '0'
            }

    async def info_from_link(self, link: str) -> tuple[str, str]:
        """
        Извлекает video_id и channel_id из ссылки на YouTube видео.
        Args:
            link: URL ссылка на видео YouTube
        Returns:
            tuple[str, str]: (video_id, channel_id)
        Raises:
            ValueError: При некорректном формате ссылки или если не удалось получить channel_id
        """
        # Паттерн для YouTube ссылок
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, link)

        if not match:
            raise ValueError(f"Некорректная YouTube-ссылка: {link}")

        video_id = match.group(1)

        # Получаем channel_id через API
        try:
            response = await self.api.get_video_details(video_id, parts="snippet")
            if response.get("items"):
                snippet = response["items"][0].get("snippet", {})
                channel_id = snippet.get("channelId")
                if channel_id:
                    logger.info(f"Извлечены данные из ссылки: video_id={video_id}, channel_id={channel_id}")
                    return video_id, channel_id

            raise ValueError(f"Видео {video_id} не найдено")

        except APIError as e:
            logger.error(
                f"API ошибка при получении channel_id для видео {video_id}: "
                f"[{e.platform}] {e.status_code} - {e.message}"
            )
            raise ValueError(f"Не удалось получить channel_id для видео {video_id}") from e
        except Exception as e:
            logger.exception(f"Ошибка при получении channel_id для видео {video_id}: {e}")
            raise

    async def get_content_info(
            self,
            user_name: str,
            content_id: str,
    ) -> UserContentInfo:
        """
        Получает полную информацию о конкретном видео.
        Args:
            user_name: Имя пользователя (не используется, для совместимости с интерфейсом)
            content_id: ID видео YouTube
        Returns:
            UserContentInfo: Информация о видео
        Raises:
            APIError: При ошибках API
        """
        try:
            response = await self.api.get_video_details(content_id, parts="snippet,statistics")

            if not response.get("items"):
                logger.error(f"Видео {content_id} не найдено")
                # Возвращаем минимально валидный объект
                return self._build_content_info(
                    articles=set(),
                    link=f"https://www.youtube.com/shorts/{content_id}",
                    views=0,
                    published=0,
                    cnt_likes=0,
                    cnt_comments=0,
                    cnt_shares=0,
                )

            video = response["items"][0]
            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})

            link = f"https://www.youtube.com/shorts/{content_id}"
            published_at_str = snippet.get("publishedAt")
            published = convert_iso_utc_to_moscow(published_at_str)
            published_unix = int(published.timestamp())
            channel_id = snippet.get("channelId")

            title = snippet.get('title', '')

            def safe_int(value: str | None, default: int = 0) -> int:
                """Безопасное преобразование в int"""
                if value is None:
                    return default
                try:
                    return max(0, int(value))
                except (ValueError, TypeError):
                    return default

            views = safe_int(statistics.get("viewCount"))
            cnt_likes = safe_int(statistics.get("likeCount"))
            cnt_comments = safe_int(statistics.get("commentCount"))
            cnt_shares = safe_int(statistics.get("favoriteCount"))
            articles = fetch_articles(title)

            logger.info(f"Получена информация о видео {content_id}: views={views}, likes={cnt_likes}")

            return self._build_content_info(
                articles=articles,
                link=link,
                views=views,
                published=published_unix,
                cnt_likes=cnt_likes,
                cnt_comments=cnt_comments,
                cnt_shares=cnt_shares,
                user_id=channel_id,
            )

        except APIError as e:
            logger.error(
                f"API ошибка при получении информации о видео {content_id}: "
                f"[{e.platform}] {e.status_code} - {e.message}"
            )
            raise
        except Exception as e:
            logger.exception(f"Ошибка при получении информации о видео {content_id}: {e}")
            raise

    @staticmethod
    def _filter_by_key_words(content_info: UserContentInfo, description: str,
                             keywords: Optional[set[str]] = None) -> Optional[UserContentInfo]:
        """
        Фильтрует контент по ключевым словам (логика как в VK).
        Двухэтапная проверка:
        1. Проверка пересечения articles с keywords (точное совпадение)
        2. Поиск keywords в description (подстрока)
        Args:
            content_info: Информация о контенте
            description: Текст описания видео
            keywords: Набор ключевых слов для фильтрации (None = без фильтрации)
        Returns:
            Optional[UserContentInfo]: Информация о контенте или None если не прошло фильтрацию
        """
        if not keywords:
            return content_info

        # Этап 1: Проверка пересечения articles с keywords (точное совпадение)
        if content_info.articles.intersection(keywords):
            return content_info

        # Этап 2: Поиск keywords в description (подстрока)
        description_lower = description.lower()
        cnt_new_key_words = 0
        for word in keywords:
            if word.lower() in description_lower:
                content_info.articles.add(word)
                cnt_new_key_words += 1

        # Если нашли хотя бы одно ключевое слово, возвращаем контент
        if cnt_new_key_words:
            return content_info

        # Если ничего не нашли, возвращаем None (не прошло фильтрацию)
        return None

    async def get_all_links(
            self,
            username: str,
            after_date: int = 0,
            keywords: Optional[set[str]] = None
    ) -> AsyncGenerator[HttpUrl, None]:
        """
        Генератор ссылок на видео пользователя с фильтрацией.
        Args:
            username: Имя пользователя YouTube
            after_date: Unix timestamp начала периода (0 = все видео)
            keywords: Набор ключевых слов для фильтрации (None = без фильтрации)
        Yields:
            HttpUrl: Ссылки на видео
        """
        if self._is_youtube_channel_id(username):
            channel_id = username
        else:
            channel_id = await self.get_channel_id(username)
        if not channel_id:
            logger.warning(f"Не удалось получить channel_id для {username}")
            return

        start_time = convert_utc_to_moscow_time(after_date)
        videos_with_desc = await self.fetch_videos(channel_id, start_time)

        logger.info(f"Обработка {len(videos_with_desc)} видео для {username}")

        for video, description in videos_with_desc:
            # Фильтрация по ключевым словам (логика как в VK)
            filtered_video = self._filter_by_key_words(video, description, keywords)
            if filtered_video:
                yield HttpUrl(filtered_video.link)

    async def get_all_info(
            self,
            username: str,
            after_date: int = 0,
            keywords: Optional[set[str]] = None
    ) -> AsyncGenerator[UserContentInfo, None]:
        """
        Генератор полной информации о видео пользователя с фильтрацией.
        Args:
            username: Имя пользователя YouTube
            after_date: Unix timestamp начала периода (0 = все видео)
            keywords: Набор ключевых слов для фильтрации (None = без фильтрации)
        Yields:
            UserContentInfo: Информация о видео
        """
        if self._is_youtube_channel_id(username):
            channel_id = username
        else:
            channel_id = await self.get_channel_id(username)
        if not channel_id:
            logger.warning(f"Не удалось получить channel_id для {username}")
            return

        start_time = convert_utc_to_moscow_time(after_date)
        videos_with_desc = await self.fetch_videos(channel_id, start_time)

        logger.info(f"Обработка {len(videos_with_desc)} видео для {username}")

        for video, description in videos_with_desc:
            # Фильтрация по ключевым словам (логика как в VK)
            filtered_video = self._filter_by_key_words(video, description, keywords)
            if filtered_video:
                yield filtered_video

    async def get_channel_info(self, username):
        username = username.replace('@', '')
        user_id = await self.get_channel_id(username, parts='snippet,statistics')
        response = await self.api.get_channel_details(user_id)
        views = response.get("statistics", {}).get("viewCount")
        followers = response.get("statistics", {}).get("subscriberCount")
        video = response.get("statistics", {}).get("videoCount")
        return UserChannelInfo(
            link=f'https://www.youtube.com/@{username}',
            cnt_views=int(views),
            followers=followers,
            videos=video,
            user_id=user_id
        )


if __name__ == "__main__":
    import asyncio


    async def test_youtube_service():
        """Тестирование основных функций YouTube сервиса"""

        # Тестовый пользователь (без @, YouTube API не поддерживает поиск с @)
        test_username = "MrBeast"  # Популярный канал

        # Время 1 месяц назад
        import time
        one_month_ago = int(time.time()) - (30 * 24 * 60 * 60)  # 30 дней назад

        print("=" * 80)
        print("▶️  ТЕСТИРОВАНИЕ YOUTUBE SERVICE")
        print("📅 Период: последние 30 дней")
        print("=" * 80)

        async with ServiceYouTubeScraper() as scraper:
            print("\n✅ Сервис инициализирован успешно\n")

            # Тест 1: Получение channel_id
            print(f"📊 Тест 1: Получение channel_id для '{test_username}'")
            print("-" * 80)
            try:
                channel_id = await scraper.get_channel_id(test_username)
                if channel_id:
                    print(f"✅ Channel ID: {channel_id}")
                else:
                    print("❌ Channel ID не найден")
            except Exception as e:
                print(f"❌ Ошибка: {e}")

            # Тест 2: Получение видео (если channel_id найден)
            if channel_id:
                print("\n\n📊 Тест 2: Получение видео канала за последний месяц (первые 3)")
                print("-" * 80)
                try:
                    start_time = convert_utc_to_moscow_time(one_month_ago)
                    videos = await scraper.fetch_videos(channel_id, start_time)
                    print(f"✅ Получено видео: {len(videos)}")

                    if videos:
                        for i, video in enumerate(videos[:3], 1):
                            print(f"\n   {i}. Видео:")
                            print(f"      Ссылка: {video.link}")
                            print(f"      Просмотры: {video.views:,}")
                            print(f"      Лайки: {video.cnt_likes:,}")
                            print(f"      Комментарии: {video.cnt_comments:,}")
                            print(f"      Артикли: {list(video.articles)[:3]}...")
                except Exception as e:
                    print(f"❌ Ошибка: {e}")

            # Тест 3: Генератор ссылок
            print("\n\n📊 Тест 3: Генератор ссылок за последний месяц (первые 3 видео)")
            print("-" * 80)
            try:
                count = 0
                async for link in scraper.get_all_links(test_username, after_date=one_month_ago):
                    count += 1
                    print(f"   {count}. {link}")
                    if count >= 3:
                        break
                print(f"✅ Обработано ссылок: {count}")
            except Exception as e:
                print(f"❌ Ошибка: {e}")

            # Тест 4: Генератор полной информации
            print("\n\n📊 Тест 4: Генератор полной информации за последний месяц (первые 2 видео)")
            print("-" * 80)
            try:
                count = 0
                async for video_info in scraper.get_all_info(test_username, after_date=one_month_ago):
                    count += 1
                    print(f"\n   {count}. Видео:")
                    print(f"      Ссылка: {video_info.link}")
                    print(f"      Просмотры: {video_info.views:,}")
                    print(f"      Лайки: {video_info.cnt_likes:,}")
                    if count >= 2:
                        break
                print(f"\n✅ Обработано видео: {count}")
            except Exception as e:
                print(f"❌ Ошибка: {e}")

            # Тест 5: Парсинг ссылки
            print("\n\n📊 Тест 5: Парсинг ссылки и получение информации")
            print("-" * 80)
            test_link = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            try:
                video_id, channel_id_from_link = await scraper.info_from_link(test_link)
                print(f"✅ Video ID: {video_id}")
                print(f"✅ Channel ID: {channel_id_from_link}")
            except Exception as e:
                print(f"❌ Ошибка: {e}")

        print("\n" + "=" * 80)
        print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("=" * 80)


    # Запуск тестов
    asyncio.run(test_youtube_service())
