class WrongResponseCode(Exception):
    """Wrong answer API."""

    pass


class NotForSending(Exception):
    """Not for telegram forwarding."""

    pass


class InvalidResponseCode(Exception):
    """Invalid response code."""

    pass


class EmptyResponseFromAPI(NotForSending):
    """Blank API response."""

    pass


class TelegramError(NotForSending):
    """Error sending message to telegram."""

    pass
