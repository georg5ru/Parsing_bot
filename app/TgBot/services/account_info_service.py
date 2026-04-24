from app.parsing.TikTokParsing.ParserByUsername import TiktokParserByUsername
from app.parsing.YoutubeParsing.ParserBuyUsername import YoutubeParserByUsername


async def get_account_info(platform: str, account: str):
    if platform == "TikTok":
        async with TiktokParserByUsername() as parser:
            return await parser.get_user_info(account)

    if platform == "YouTube":
        async with YoutubeParserByUsername() as parser:
            return await parser.get_channel_info(account)

    return None