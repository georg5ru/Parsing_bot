import datetime
from typing import AsyncGenerator, Optional, List

from pydantic import HttpUrl

from app.parsing.TikTokParsing.api.core import TikTokAPI
from app.services.date_service import convert_utc_to_moscow_time
from app.parsing.errors.baseErrors import APIError
from app.parsing.interfaces.iByUsername import UserContentInfo, UserChannelInfo
from app.parsing.services.articles_services import fetch_articles
from app.logger.logger import get_logger

# Инициализируем корпоративный логгер
logger = get_logger(__name__, log_level="INFO")


class ServiceTikTokScraper:
    """
    Сервис для работы с TikTok API.
    Лучшие практики:
    - Context manager для автоматического управления ресурсами
    - Обработка APIError из декоратора
    - Централизованное логирование
    - Type hints для всех методов
    """

    def __init__(self):
        self.api: Optional[TikTokAPI] = None

    @staticmethod
    def _is_tiktok_sec_uid(value: str) -> bool:
        return bool(value) and value.startswith("MS4") and len(value) > 50

    async def __aenter__(self):
        """Инициализация API клиента через context manager"""
        self.api = await TikTokAPI().__aenter__()
        logger.info("ServiceTikTokScraper initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие API клиента"""
        if self.api:
            await self.api.__aexit__(exc_type, exc_val, exc_tb)
            logger.info("ServiceTikTokScraper closed")

    async def get_views_tiktok(self, video_id: str) -> int:
        """
        Получает количество просмотров TikTok-видео.
        Args:
            video_id: ID видео TikTok
        Returns:
            int: Количество просмотров или -1 при ошибке
        """
        try:
            data = await self.api.get_info_tiktok(video_id)
            data_user = data.get("itemInfo", {}).get("itemStruct", {})
            play_count = data_user.get("stats", {}).get("playCount", -1)
            logger.info(f"Получены просмотры для видео {video_id}: {play_count}")
            return play_count
        except APIError as e:
            logger.error(
                f"API ошибка при получении просмотров для видео {video_id}: "
                f"[{e.platform}] {e.status_code} - {e.message}"
            )
            return -1
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при получении просмотров для видео {video_id}: {e}")
            return -1

    async def get_user_id(self, username: str) -> Optional[str]:
        """
        Получает secUid пользователя TikTok по его имени.
        Args:
            username: Уникальное имя пользователя (uniqueId)
        Returns:
            Optional[str]: secUid пользователя или None при ошибке
        """
        try:
            response = await self.api.get_user_id(username)
            user_id = response.get('userInfo', {}).get('user', {}).get('secUid')

            if not user_id:
                logger.warning(f"secUid не найден в ответе для пользователя {username}")
                return None

            logger.info(f"Получен secUid для пользователя {username}: {user_id[:20]}...")
            return user_id
        except APIError as e:
            logger.error(
                f"API ошибка при получении user_id для {username}: "
                f"[{e.platform}] {e.status_code} - {e.message}"
            )
            return None
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при получении user_id для {username}: {e}")
            return None

    async def get_tt_videos(
            self,
            user_id: str,
            start_time: datetime.datetime
    ) -> List[UserContentInfo]:
        """
        Возвращает список видео пользователя TikTok, опубликованных после start_time.
        Args:
            user_id: secUid пользователя
            start_time: Время начала (видео публикованные после этого времени)
        Returns:
            List[UserContentInfo]: Список информации о видео
        """
        videos_with_desc = await self.fetch_videos(user_id, start_time)
        videos = [video for video, _ in videos_with_desc]
        logger.info(f"Найдено {len(videos)} тиктоков для user_id {user_id[:20]}...")
        return videos

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

    async def fetch_videos(
            self,
            user_id: str,
            start_time: datetime.datetime
    ) -> List[tuple[UserContentInfo, str]]:
        """
        Получает видео с учетом пагинации и времени публикации.
        Args:
            user_id: secUid пользователя
            start_time: Время начала (видео публикованные после этого времени)
        Returns:
            List[tuple[UserContentInfo, str]]: Список кортежей (информация о видео, описание)
        """
        cursor = None
        videos = []

        while True:
            try:
                response = await self.get_next_page(user_id, cursor)
            except APIError as e:
                logger.error(
                    f"API ошибка при получении видео для user_id {user_id[:20]}: "
                    f"[{e.platform}] {e.status_code} - {e.message}"
                )
                break
            except Exception as e:
                logger.exception(f"Неожиданная ошибка при получении видео для user_id {user_id[:20]}: {e}")
                break

            data = response.get('data', {})
            items = data.get('itemList', [])

            if not items:
                logger.info(f"Дополнительные видео для user_id {user_id[:20]} не найдены.")
                break

            for video in items:
                # Проверяем, нужно ли остановить обработку
                if self.should_stop_processing(video, start_time):
                    logger.info(f"Достигли видео старше {start_time}, остановка.")
                    return videos

                # Обрабатываем видео, если оно подходит
                processed_video = self.process_video(video, start_time, user_id=user_id)
                if processed_video:
                    # Сохраняем description для фильтрации
                    description = video.get('desc', '')
                    videos.append((processed_video, description))

            cursor = data.get('cursor')
            if not cursor or not data.get('hasMore', False):
                logger.info(f"Достигнут конец списка видео для user_id {user_id[:20]}")
                break

        return videos

    async def get_next_page(self, user_id: str, cursor: Optional[str] = None) -> dict:
        """
        Выполняет API-запрос для получения следующей страницы данных.
        Args:
            user_id: secUid пользователя
            cursor: Курсор для пагинации (опционально)
        Returns:
            dict: JSON-ответ с данными видео
        Raises:
            APIError: При ошибках API (пробрасывается из api.get_search_tt)
        """
        return await self.api.get_search_tt(user_id, cursor)

    def should_stop_processing(self, video: dict, start_time: datetime.datetime) -> bool:
        """
        Проверяет, нужно ли прервать обработку видео.
        Args:
            video: Данные видео из API
            start_time: Время начала фильтрации
        Returns:
            bool: True если нужно остановить обработку
        """
        published = convert_utc_to_moscow_time(video.get('createTime', 0))
        # Прерываем для незакрепленных видео, если время публикации <= start_time
        return not video.get('isPinnedItem', False) and published <= start_time

    def process_video(
            self,
            video: dict,
            start_time: datetime.datetime,
            user_id: Optional[str] = None,
    ) -> Optional[UserContentInfo]:
        """
        Обрабатывает одно видео, возвращает UserContentInfo, если оно подходит.
        Args:
            video: Данные видео из API
            start_time: Время начала фильтрации
        Returns:
            Optional[UserContentInfo]: Информация о видео или None если не подходит
        """
        published = convert_utc_to_moscow_time(video.get('createTime', 0))
        # Пропускаем видео, если время публикации <= start_time (включая закрепленные)
        if published <= start_time:
            return None

        try:
            status = video.get('stats', {})
            views = round(status.get('playCount', 0))
            cnt_likes = status.get('diggCount', 0)
            cnt_comments = status.get('commentCount', 0)
            cnt_shares = status.get('shareCount', 0)
            link = f"https://www.tiktok.com/@{video['author']['uniqueId']}/video/{video['id']}"
            description = video.get('desc', '')
            articles = fetch_articles(description)

            # Преобразуем datetime в unixtime для UserContentInfo
            published_unix = int(published.timestamp())

            return self._build_content_info(
                articles=articles,
                link=link,
                views=views,
                published=published_unix,
                cnt_likes=cnt_likes,
                cnt_comments=cnt_comments,
                cnt_shares=cnt_shares,
                user_id=user_id,
            )
        except KeyError as e:
            logger.error(f"Отсутствует обязательное поле в данных видео: {e}")
            return None
        except Exception as e:
            logger.exception(f"Ошибка при обработке видео: {e}")
            return None

    @staticmethod
    def _filter_by_key_words(content_info: UserContentInfo, description: str,
                             keywords: Optional[set] = None) -> Optional[UserContentInfo]:
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

    async def info_from_link(self, link: str) -> tuple[str, str]:
        """
        Извлекает owner_id и video_id из ссылки на TikTok видео.
        Args:
            link: URL ссылка на видео TikTok
        Returns:
            tuple[str, str]: (owner_id, video_id)
        Raises:
            APIError: При ошибках API
            ValueError: При некорректном формате ссылки
        """
        try:
            video_id = link.split('/')[-1][0:19]
            response = await self.api.get_info_tiktok(video_id)
            owner_id = response['itemInfo']['itemStruct']['author']['id']
            logger.info(f"Извлечены данные из ссылки: owner_id={owner_id}, video_id={video_id}")
            return owner_id, video_id
        except IndexError as e:
            logger.error(f"Некорректный формат ссылки: {link}")
            raise ValueError(f"Некорректный формат ссылки: {link}") from e
        except KeyError as e:
            logger.error(f"Отсутствует обязательное поле в ответе API для видео {video_id}: {e}")
            raise

    async def get_content_info(self, username: str, content_id: str) -> UserContentInfo:
        """
        Получает полную информацию о конкретном видео.
        Args:
            username: Имя пользователя (для формирования ссылки)
            content_id: ID видео
        Returns:
            UserContentInfo: Информация о видео
        Raises:
            APIError: При ошибках API
        """
        response = await self.api.get_info_tiktok(content_id)

        # Извлекаем данные из ответа
        item_struct = response['itemInfo']['itemStruct']

        # createTime может быть int или str
        create_time = item_struct['createTime']
        if isinstance(create_time, str):
            create_time = int(create_time)

        published = convert_utc_to_moscow_time(create_time)
        published_unix = int(published.timestamp())

        stats = item_struct.get('stats', {})
        views = stats.get('playCount', 0)
        cnt_likes = stats.get('diggCount', 0)
        cnt_comments = stats.get('commentCount', 0)
        cnt_shares = stats.get('shareCount', 0)

        link = f"https://www.tiktok.com/@{username}/video/{content_id}"
        description = item_struct.get('desc', '')
        articles = fetch_articles(description)
        author_info = item_struct.get('author', {})
        user_id = author_info.get('secUid')
        if not user_id and username:
            user_id = await self.get_user_id(username)

        logger.info(f"Получена информация о видео {content_id}: views={views}, likes={cnt_likes}")

        return self._build_content_info(
            articles=articles,
            link=link,
            views=views,
            published=published_unix,
            cnt_likes=cnt_likes,
            cnt_comments=cnt_comments,
            cnt_shares=cnt_shares,
            user_id=user_id,
        )

    async def get_all_links(
            self,
            username: str,
            after_date: int = 0,
            keywords: Optional[set] = None
    ) -> AsyncGenerator[HttpUrl, None]:
        """
        Генератор ссылок на видео пользователя с фильтрацией
        Args:
            username: Имя пользователя TikTok
            after_date: Unix timestamp начала периода (0 = все видео)
            keywords: Набор ключевых слов для фильтрации (None = без фильтрации)
        Yields:
            HttpUrl: Ссылки на видео
        """
        if self._is_tiktok_sec_uid(username):
            user_id = username
        else:
            user_id = await self.get_user_id(username)
        if not user_id:
            logger.warning(f"Не удалось получить user_id для {username}")
            return

        start_time = convert_utc_to_moscow_time(after_date)
        videos_with_desc = await self.fetch_videos(user_id, start_time)

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
            keywords: Optional[set] = None
    ) -> AsyncGenerator[UserContentInfo, None]:
        """
        Генератор полной информации о видео пользователя с фильтрацией
        Args:
            username: Имя пользователя TikTok
            after_date: Unix timestamp начала периода (0 = все видео)
            keywords: Набор ключевых слов для фильтрации (None = без фильтрации)
        Yields:
            UserContentInfo: Информация о видео
        """
        if self._is_tiktok_sec_uid(username):
            user_id = username
        else:
            user_id = await self.get_user_id(username)
        if not user_id:
            logger.warning(f"Не удалось получить user_id для {username}")
            return

        start_time = convert_utc_to_moscow_time(after_date)
        videos_with_desc = await self.fetch_videos(user_id, start_time)

        logger.info(f"Обработка {len(videos_with_desc)} видео для {username}")

        for video, description in videos_with_desc:
            # Фильтрация по ключевым словам (логика как в VK)
            filtered_video = self._filter_by_key_words(video, description, keywords)
            if filtered_video:
                yield filtered_video

    async def get_user_info(self, username):
        response = await self.api.get_user_id(username)
        data = response['userInfo']['statsV2']
        videos = data.get('videoCount')
        likes = data.get('heart')
        followers = data.get('followerCount')
        user_id = await self.get_user_id(username)
        return UserChannelInfo(
            link=f"https://www.tiktok.com/@{username}",
            videos=videos or 0,
            cnt_likes=likes or 0,
            cnt_views=0,
            followers=followers or 0,
            user_id=user_id,
        )
async def main():
    """
    Тестирование ServiceTikTokScraper.
    Демонстрирует использование всех основных методов сервиса с новой архитектурой:
    - Context manager для автоматического управления ресурсами
    - Обработка APIError
    - Работа с новым контрактом API (dict без status_code)
    """
    print("=" * 80)
    print("🚀 Тестирование ServiceTikTokScraper")
    print("=" * 80)

    # Тестовые данные
    test_username = "patrakeeva_a7"
    test_video_id = "7498684706716749078"

    async with ServiceTikTokScraper() as scraper:
        print("\n" + "=" * 80)
        print("📋 Тест 1: Получение secUid пользователя")
        print("=" * 80)

        try:
            user_id = await scraper.get_user_id(test_username)
            if user_id:
                print(f"✅ Успешно получен secUid для @{test_username}:")
                print(f"   secUid: {user_id[:40]}...")
            else:
                print(f"❌ Не удалось получить secUid для @{test_username}")
        except Exception as e:
            print(f"❌ Исключение при получении secUid: {type(e).__name__}: {e}")

        print("\n" + "=" * 80)
        print("📊 Тест 2: Получение количества просмотров видео")
        print("=" * 80)

        try:
            views = await scraper.get_views_tiktok(test_video_id)
            if views > 0:
                print(f"✅ Успешно получены просмотры для видео {test_video_id}:")
                print(f"   Просмотры: {views:,}")
            else:
                print("⚠️  Просмотры не получены (вернулось -1)")
        except Exception as e:
            print(f"❌ Исключение при получении просмотров: {type(e).__name__}: {e}")

        print("\n" + "=" * 80)
        print("📝 Тест 3: Получение полной информации о видео")
        print("=" * 80)

        try:
            content_info = await scraper.get_content_info(test_username, test_video_id)
            print("✅ Успешно получена информация о видео:")
            print(f"   Ссылка: {content_info.link}")
            print(f"   Просмотры: {content_info.views:,}")
            print(f"   Лайки: {content_info.cnt_likes:,}")
            print(f"   Комментарии: {content_info.cnt_comments:,}")
            print(f"   Репосты: {content_info.cnt_shares:,}")

            # Преобразуем unix timestamp в datetime для читабельности
            published_dt = datetime.datetime.fromtimestamp(content_info.published)
            print(f"   Дата публикации: {published_dt.strftime('%Y-%m-%d %H:%M:%S')}")

            if content_info.articles:
                articles_preview = ', '.join(list(content_info.articles)[:3])
                print(f"   Артиклы: {articles_preview}{'...' if len(content_info.articles) > 3 else ''}")
        except Exception as e:
            print(f"❌ Исключение при получении информации о видео: {type(e).__name__}: {e}")

        # Тест 4: только если получили user_id
        try:
            user_id = await scraper.get_user_id(test_username)
            if user_id:
                print("\n" + "=" * 80)
                print("🎬 Тест 4: Получение списка видео пользователя")
                print("=" * 80)

                # Получаем видео за последние 30 дней
                # Делаем datetime aware (Moscow timezone)
                from datetime import timezone, timedelta
                moscow_tz = timezone(timedelta(hours=3))
                start_time = datetime.datetime.now(tz=moscow_tz) - datetime.timedelta(days=30)
                videos = await scraper.get_tt_videos(user_id, start_time)

                print(f"✅ Найдено {len(videos)} видео за последние 30 дней:")
                for idx, video in enumerate(videos[:5], 1):  # Показываем первые 5
                    print(f"\n   {idx}. {video.link}")
                    print(f"      Просмотры: {video.views:,}")
                    print(f"      Лайки: {video.cnt_likes:,}")

                    # Преобразуем unix timestamp в datetime для читабельности
                    published_dt = datetime.datetime.fromtimestamp(video.published)
                    print(f"      Дата: {published_dt.strftime('%Y-%m-%d %H:%M:%S')}")

                if len(videos) > 5:
                    print(f"\n   ... и ещё {len(videos) - 5} видео")
        except Exception as e:
            print(f"❌ Исключение при получении списка видео: {type(e).__name__}: {e}")

        print("\n" + "=" * 80)
        print("🔗 Тест 5: Тестирование генератора ссылок (первые 3)")
        print("=" * 80)

        try:
            count = 0
            async for link in scraper.get_all_links(test_username, after_date=0):
                count += 1
                print(f"   {count}. {link}")
                if count >= 3:
                    break

            if count > 0:
                print(f"✅ Генератор работает корректно (показано {count} ссылок)")
            else:
                print("⚠️  Нет доступных видео")

        except Exception as e:
            print(f"❌ Исключение при работе генератора: {type(e).__name__}: {e}")

        print("\n" + "=" * 80)
        print("📦 Тест 6: Тестирование генератора полной информации (первые 2)")
        print("=" * 80)

        try:
            count = 0
            async for video_info in scraper.get_all_info(test_username, after_date=0):
                count += 1
                print(f"\n   {count}. Видео:")
                print(f"      Ссылка: {video_info.link}")
                print(f"      Просмотры: {video_info.views:,}")
                print(f"      Лайки: {video_info.cnt_likes:,}")

                # Преобразуем unix timestamp в datetime для читабельности
                published_dt = datetime.datetime.fromtimestamp(video_info.published)
                print(f"      Дата: {published_dt.strftime('%Y-%m-%d %H:%M:%S')}")

                if count >= 2:
                    break

            if count > 0:
                print("\n✅ Генератор полной информации работает корректно")
            else:
                print("⚠️  Нет доступных видео")

        except Exception as e:
            print(f"❌ Исключение при работе генератора: {type(e).__name__}: {e}")

        print("\n" + "=" * 80)
        print("🔍 Тест 7: Извлечение данных из ссылки")
        print("=" * 80)

        try:
            test_link = f"https://www.tiktok.com/@{test_username}/video/{test_video_id}"
            owner_id, video_id = await scraper.info_from_link(test_link)
            print("✅ Успешно извлечены данные из ссылки:")
            print(f"   Owner ID: {owner_id}")
            print(f"   Video ID: {video_id}")
        except Exception as e:
            print(f"❌ Исключение при извлечении данных: {type(e).__name__}: {e}")

    print("\n" + "=" * 80)
    print("✨ Тестирование завершено!")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio

    # Запускаем тесты
    asyncio.run(main())
