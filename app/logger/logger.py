"""
Настройка системы логирования для проекта Parser_media
"""
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для консольного вывода"""

    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[41m',  # Red background
        'RESET': '\033[0m'  # Reset
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class LoggerSetup:
    """Класс для настройки логирования"""

    @staticmethod
    def setup_logger(
            name: str,
            level: int = logging.INFO,
            log_file: Optional[str] = None,
            console_output: bool = True,
            max_bytes: int = 10 * 1024 * 1024,  # 10MB
            backup_count: int = 5
    ) -> logging.Logger:
        """
        Настраивает и возвращает logger
        Args:
            name: Имя логгера
            level: Уровень логирования
            log_file: Путь к файлу логов
            console_output: Выводить ли логи в консоль
            max_bytes: Максимальный размер файла лога
            backup_count: Количество резервных копий
        """
        logger = logging.getLogger(name)

        # Избегаем дублирования обработчиков
        if logger.handlers:
            return logger

        logger.setLevel(level)

        # Формат для логов
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # Файловый обработчик с ротацией
        if log_file:
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(level)
            logger.addHandler(file_handler)

        # Консольный обработчик
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(level)
            logger.addHandler(console_handler)

        return logger

    @staticmethod
    def setup_error_logger(log_dir: str = "logs") -> logging.Logger:
        """Настраивает отдельный логгер для ошибок"""
        error_log_path = Path(log_dir) / f"errors_{datetime.now().strftime('%Y%m%d')}.log"

        return LoggerSetup.setup_logger(
            name="error_logger",
            level=logging.ERROR,
            log_file=str(error_log_path),
            console_output=False
        )

    @staticmethod
    def setup_api_logger(log_dir: str = "logs") -> logging.Logger:
        """Настраивает логгер для API запросов"""
        api_log_path = Path(log_dir) / f"api_{datetime.now().strftime('%Y%m%d')}.log"

        return LoggerSetup.setup_logger(
            name="api_logger",
            level=logging.DEBUG,
            log_file=str(api_log_path),
            console_output=False
        )


def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Получить настроенный логгер
    Args:
        name: Имя логгера (обычно __name__)
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Создаем директорию для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Путь к основному файлу логов
    log_file = log_dir / f"parser_media_{datetime.now().strftime('%Y%m%d')}.log"

    return LoggerSetup.setup_logger(
        name=name,
        level=level,
        log_file=str(log_file),
        console_output=True
    )


# Глобальные логгеры для проекта
main_logger = get_logger("parser_media")
error_logger = LoggerSetup.setup_error_logger()
api_logger = LoggerSetup.setup_api_logger()


def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """
    Логирование исключения с контекстом
    Args:
        logger: Логгер для записи
        exception: Исключение
        context: Дополнительный контекст
    """
    error_msg = f"{context}: {type(exception).__name__}: {str(exception)}" if context \
        else f"{type(exception).__name__}: {str(exception)}"
    logger.error(error_msg, exc_info=True)
    # Дублируем в error_logger
    error_logger.error(error_msg, exc_info=True)
