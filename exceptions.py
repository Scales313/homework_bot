class WrongResponseCode(Exception):
    pass

class NotForSending(Exception):
    pass

class InvalidResponseCode(Exception):
    pass

class EmptyResponseFromAPI(NotForSending):
    pass


class TelegramError(NotForSending):
    pass
