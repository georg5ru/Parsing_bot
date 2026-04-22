from datetime import datetime

mock_parsings: dict[int, list[dict]] = {}


def create_stub_parsing(user_id: int, platform: str, account: str, period: str) -> dict:
    parsing = {
        "id": len(mock_parsings.get(user_id, [])) + 1,
        "platform": platform,
        "account": account,
        "period": period,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    user_items = mock_parsings.get(user_id, [])
    user_items.insert(0, parsing)
    mock_parsings[user_id] = user_items

    return parsing


def get_user_parsings(user_id: int) -> list[dict]:
    return mock_parsings.get(user_id, [])