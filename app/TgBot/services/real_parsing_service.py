from datetime import datetime, timedelta

from app.parsing.TikTokParsing.ParserByUsername import TiktokParserByUsername
from app.parsing.YoutubeParsing.ParserBuyUsername import YoutubeParserByUsername


def get_after_timestamp(period: str) -> int:
    now = datetime.utcnow()

    period_map = {
        "1 месяц": 30,
        "3 месяца": 90,
        "6 месяцев": 180,
    }

    if period in period_map:
        return int((now - timedelta(days=period_map[period])).timestamp())

    if period.startswith("date:"):
        date_str = period.replace("date:", "").strip()
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        return int(dt.timestamp())

    return int((now - timedelta(days=30)).timestamp())


async def run_real_parsing(task):
    platform = task.platform
    username = task.account
    after_timestamp = get_after_timestamp(task.period)

    results = []

    if platform == "TikTok":
        async with TiktokParserByUsername() as parser:
            async for item in parser.get_all_info(username, after_date=after_timestamp):
                results.append(item)

    elif platform == "YouTube":
        async with YoutubeParserByUsername() as parser:
            async for item in parser.get_all_info(username, after_date=after_timestamp):
                results.append(item)

    return results