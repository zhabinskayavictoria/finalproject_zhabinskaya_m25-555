class ValutaTradeError(Exception):
    """Базовое исключение для ValutaTrade"""
    pass

class InsufficientFundsError(ValutaTradeError):
    """Исключение для случая недостатка средств"""
    def __init__(self, available: float, required: float, code: str):
        message = (f"Недостаточно средств: доступно {available:.4f} {code}, "
                f"требуется {required:.4f} {code}\n")
        super().__init__(message)
        self.available = available
        self.required = required
        self.code = code
        
class CurrencyNotFoundError(ValutaTradeError):
    """Исключение для случая, когда валюта не найдена"""
    def __init__(self, code: str):
        message = f"Неизвестная валюта '{code}'\n"
        super().__init__(message)
        self.code = code

class ApiRequestError(ValutaTradeError):
    """Исключение для ошибок API запросов"""
    def __init__(self, reason: str = ""):
        message = f"Ошибка при обращении к внешнему API: {reason}\n"
        super().__init__(message)
        self.reason = reason

class UserNotFoundError(ValutaTradeError):
    """Исключение для случая, когда пользователь не найден"""
    pass

class AuthenticationError(ValutaTradeError):
    """Исключение для ошибок аутентификации"""
    pass