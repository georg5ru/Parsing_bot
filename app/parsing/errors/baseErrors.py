class SocialMediaError(Exception):
    """Базовая ошибка для всех действий, связанных с социальными сетями."""
    pass


class ParsingError(SocialMediaError):
    """Ошибка, связанная с парсингом данных из социальной сети."""
    pass


class NetworkError(SocialMediaError):
    """Ошибка, связанная с сетевыми запросами к социальной сети."""
    pass


class AuthError(SocialMediaError):
    """Ошибка, связанная с аутентификацией в социальной сети."""
    pass


class RateLimitError(SocialMediaError):
    """Ошибка, связанная с превышением рейт-лимита."""
    pass


class APIError(Exception):
    """Базовое исключение для ошибок API."""
    def __init__(self, message: str, status_code: int = 500, platform: str = "Unknown"):
        self.message = message
        self.status_code = status_code
        self.platform = platform
        super().__init__(self.message)

