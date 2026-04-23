from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

MOSCOW_TZ = timezone(timedelta(hours=3))
msk_tz = ZoneInfo("Europe/Moscow")


def unix_to_datetime(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp)


def datetime_to_unix(dt: datetime) -> int:
    return int(dt.timestamp())


def str_date_to_datetime(dt: str) -> datetime:
    return datetime.strptime(dt, '%d.%m.%Y')


def str_date_to_date(dt: str) -> date:
    return datetime.strptime(dt, '%d.%m.%Y').date()


def str_date_to_unix(dt: str) -> int:
    return datetime_to_unix(str_date_to_datetime(dt))


def get_current_date() -> datetime:
    return datetime.now(msk_tz).replace(microsecond=0)


def get_month_from_date(date: datetime) -> str:
    months = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь"
    }
    return months.get(date.month)


def get_week_range_from_date(date: datetime) -> str:
    start_of_week = date - timedelta(days=date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return f"{start_of_week.strftime('%d.%m')} - {end_of_week.strftime('%d.%m')}"


def convert_utc_to_moscow_time(unix_timestamp: int) -> datetime:
    """Преобразует Unix-время в московское время (UTC+3)"""
    # Время по UTC
    utc_time = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    # Московское время (UTC+3)
    moscow_time = utc_time.astimezone(timezone(timedelta(hours=3)))
    return moscow_time


def convert_string_to_moscow_time(time_str: str) -> datetime:
    """Преобразует строку формата 'YYYY-MM-DD HH:MM:SS' в московское время (UTC+3)"""
    moscow_tz = timezone(timedelta(hours=3))
    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    return dt.replace(tzinfo=moscow_tz)


def convert_iso_utc_to_moscow(iso_time_str: str) -> datetime:
    """
    Преобразует ISO8601-строку в московское время.
    Пример: '2025-05-02T18:55:38Z' → datetime в UTC+3
    """
    try:
        utc_time = datetime.strptime(iso_time_str, '%Y-%m-%dT%H:%M:%SZ')
        utc_time = utc_time.replace(tzinfo=timezone.utc)
        # Переводим в московское время
        moscow_time = utc_time.astimezone(MOSCOW_TZ)
        return moscow_time
    except ValueError as e:
        raise ValueError(f"Неверный формат ISO-времени: '{iso_time_str}'") from e


def is_date_in_range(check_date: date, from_date: date, to_date: date) -> bool:
    """
    Проверяет, попадает ли check_date в диапазон [from_date, to_date] включительно.
    """
    return from_date <= check_date <= to_date


if __name__ == '__main__':
    now = get_current_date()
    print(get_week_range_from_date(now))
