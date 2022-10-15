class NotSendException(Exception):
    """Исключение не для пересылки в Telegram."""
    pass


class EmptyResponseError(NotSendException):
    """Пустой запрос"""
    pass


class HTTPStatusError(Exception):
    """Пришел статус отличный от 200."""
    pass
