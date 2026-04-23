import asyncio
from functools import wraps
from typing import Callable
import httpx

from app.logger.logger import get_logger
from app.parsing.errors.baseErrors import APIError

# Инициализируем логгер с использованием корпоративной системы логирования
logger = get_logger(__name__, log_level="INFO")


def improved_api_call(
        platform: str,
        identifier_key: str = "identifier",
        max_retries: int = 3,
        backoff_factor: float = 1.0,
):
    """
    Асинхронный декоратор для надёжного вызова внешних API с retry-логикой.

    Лучшие практики:
    - Централизованное логирование через корпоративную систему
    - Прозрачная обработка ошибок с кастомными исключениями
    - Экспоненциальная задержка (exponential backoff)
    - Чистый контракт: возвращает httpx.Response при успехе, бросает APIError при неудаче

    Args:
        platform: Название платформы (например, "TT" для TikTok, "IG" для Instagram)
        identifier_key: Ключ в kwargs для извлечения идентификатора (user_id, video_id и т.д.)
        max_retries: Максимальное число попыток (включая первую)
        backoff_factor: Базовая задержка между попытками (в секундах)

    Returns:
        httpx.Response: Успешный HTTP-ответ (status_code 200-299)

    Raises:
        APIError: При исчерпании попыток или критических ошибках
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> httpx.Response:
            # Извлекаем идентификатор для логов
            identifier = kwargs.get(identifier_key, None)

            # Если не нашли в kwargs, попробуем найти по индексу в args
            # Обычно для api_request сигнатура: (self, url, params)
            # Поэтому params будет args[2] (с учётом self=args[0])
            if identifier is None and identifier_key == "params" and len(args) >= 3:
                identifier = args[2]  # params - третий аргумент после self и url

            # Если identifier всё ещё None, попробуем другие распространённые позиции
            if identifier is None:
                # Для методов с сигнатурой (self, identifier_value)
                if len(args) >= 2:
                    identifier = args[1]
                else:
                    identifier = "unknown"

            # Если identifier_key указывает на словарь (например, params), 
            # попытаемся извлечь что-то полезное из него
            if isinstance(identifier, dict):
                # Приоритетные ключи для идентификации
                priority_keys = ['videoId', 'uniqueId', 'secUid', 'user_id', 'username', 'id']
                for key in priority_keys:
                    if key in identifier:
                        identifier = f"{key}={identifier[key]}"
                        break
                else:
                    # Если ничего не нашли, берём первый ключ-значение
                    if identifier:
                        first_key = next(iter(identifier))
                        identifier = f"{first_key}={identifier[first_key]}"
                    else:
                        identifier = "empty_params"

            for attempt in range(max_retries):
                try:
                    # Выполняем асинхронную функцию
                    response = await func(*args, **kwargs)
                    status_code = response.status_code

                    # Успех (2xx статус-коды)
                    if 200 <= status_code < 300:
                        logger.info(
                            f"[{platform}] Success for '{identifier}': "
                            f"status={status_code}, attempt={attempt + 1}"
                        )
                        return response

                    # Rate limit — 429
                    if status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 5))
                        logger.warning(
                            f"[{platform}] Rate limited for '{identifier}'. "
                            f"Retrying after {retry_after}s (attempt {attempt + 1}/{max_retries})"
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise APIError(
                                f"Rate limit exceeded after {max_retries} attempts",
                                status_code=429,
                                platform=platform
                            )

                    # Серверные ошибки или временные проблемы — retry
                    if status_code >= 500 or status_code in (408, 420):
                        wait = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"[{platform}] Server error {status_code} for '{identifier}'. "
                            f"Retrying in {wait:.1f}s (attempt {attempt + 1}/{max_retries})"
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(wait)
                            continue
                        else:
                            raise APIError(
                                f"Server error {status_code} after {max_retries} attempts",
                                status_code=status_code,
                                platform=platform
                            )

                    # Клиентские ошибки (4xx кроме 429) — не retry
                    if 400 <= status_code < 500:
                        error_detail = "Unknown error"
                        try:
                            error_detail = response.json().get("message", response.text[:200])
                        except Exception:
                            error_detail = response.text[:200] if response.text else "No details"

                        logger.error(
                            f"[{platform}] Client error {status_code} for '{identifier}': {error_detail}"
                        )
                        raise APIError(
                            f"Client error: {error_detail}",
                            status_code=status_code,
                            platform=platform
                        )

                    # Неожиданный статус-код
                    logger.error(
                        f"[{platform}] Unexpected status {status_code} for '{identifier}'"
                    )
                    raise APIError(
                        f"Unexpected status code: {status_code}",
                        status_code=status_code,
                        platform=platform
                    )

                except APIError:
                    # Пробрасываем наше кастомное исключение
                    raise

                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    wait = backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"[{platform}] Network error for '{identifier}': {type(e).__name__}. "
                        f"Retrying in {wait:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait)
                    else:
                        logger.error(
                            f"[{platform}] Network error for '{identifier}' after {max_retries} attempts: {e}"
                        )
                        raise APIError(
                            f"Network error: {str(e)}",
                            status_code=503,
                            platform=platform
                        )

                except httpx.HTTPStatusError as e:
                    # Например, при использовании response.raise_for_status()
                    status = e.response.status_code if e.response else 500
                    logger.error(
                        f"[{platform}] HTTP status error for '{identifier}': {e}"
                    )
                    raise APIError(
                        f"HTTP status error: {str(e)}",
                        status_code=status,
                        platform=platform
                    )

                except Exception as e:
                    logger.exception(
                        f"[{platform}] Unexpected exception for '{identifier}': {type(e).__name__}: {e}"
                    )
                    raise APIError(
                        f"Unexpected error: {str(e)}",
                        status_code=500,
                        platform=platform
                    )

            # Если все попытки исчерпаны (не должно досюда дойти при корректной логике)
            logger.error(
                f"[{platform}] Max retries ({max_retries}) exceeded for '{identifier}'"
            )
            raise APIError(
                "Max retries exceeded",
                status_code=500,
                platform=platform
            )

        return wrapper

    return decorator
