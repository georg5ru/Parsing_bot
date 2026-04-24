from urllib.parse import urlparse


def is_valid_account(value: str) -> bool:
    value = value.strip()

    if not value:
        return False

    if value.startswith("@") and len(value) > 1:
        return True

    if value.startswith("http://") or value.startswith("https://"):
        return True

    return False


def normalize_account(platform: str, value: str) -> str:
    value = value.strip()

    if value.startswith("@"):
        return value[1:].strip().lower()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        path = parsed.path.strip("/")
        parts = [part for part in path.split("/") if part]

        if platform == "TikTok":
            if parts and parts[0].startswith("@"):
                return parts[0][1:].strip().lower()

            if parts:
                return parts[-1].replace("@", "").strip().lower()

        if platform == "YouTube":
            ignored_tabs = {"videos", "shorts", "streams", "featured", "community", "playlists"}

            if parts and parts[-1].lower() in ignored_tabs:
                parts = parts[:-1]

            if not parts:
                return value.strip().lower()

            first = parts[0]

            if first.startswith("@"):
                return first[1:].strip().lower()

            if first in {"channel", "c", "user"} and len(parts) >= 2:
                return parts[1].strip().lower()

            return first.replace("@", "").strip().lower()

    return value.replace("@", "").strip().lower()