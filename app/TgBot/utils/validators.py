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

        if platform == "TikTok":
            # /@username
            if path.startswith("@"):
                return path[1:].strip().lower()

            # fallback: берём последний сегмент
            parts = [part for part in path.split("/") if part]
            if parts:
                last_part = parts[-1]
                return last_part.replace("@", "").strip().lower()

        if platform == "YouTube":
            # /@channel
            if path.startswith("@"):
                return path[1:].strip().lower()

            parts = [part for part in path.split("/") if part]
            if parts:
                # youtube.com/@name -> first part = @name
                if parts[0].startswith("@"):
                    return parts[0][1:].strip().lower()

                # youtube.com/channel/xxx or youtube.com/c/xxx or youtube.com/user/xxx
                if len(parts) >= 2 and parts[0] in {"channel", "c", "user"}:
                    return parts[1].strip().lower()

                return parts[-1].replace("@", "").strip().lower()

    return value.replace("@", "").strip().lower()