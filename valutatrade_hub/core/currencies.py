from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс для валют"""
    def __init__(self, name: str, code: str):
        """Инициализирует валюту"""
        self._validate_name(name)
        self._validate_code(code)
        self.name = name
        self.code = code.upper()
    
    def _validate_name(self, name: str):
        """Проверяет валидность имени валюты"""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустой строкой\n")
    
    def _validate_code(self, code: str):
        """Проверяет валидность кода валюты"""
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Код валюты не может быть пустой строкой\n")
        code_upper = code.upper()
        if len(code_upper) < 2 or len(code_upper) > 5:
            raise ValueError("Код валюты должен содержать от 2 до 5 символов\n")
        if ' ' in code_upper:
            raise ValueError("Код валюты не может содержать пробелы\n")
    
    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление для UI/логов"""
        pass
    


class FiatCurrency(Currency):
    """Класс для фиатных валют"""
    def __init__(self, name: str, code: str, issuing_country: str):
        """Инициализирует фиатную валюту"""
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна не может быть пустой строкой\n")
        self.issuing_country = issuing_country
    
    def get_display_info(self) -> str:
        """Возвращает строковое представление фиатной валюты"""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})\n"


class CryptoCurrency(Currency):
    """Класс для криптовалют"""
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        """Инициализирует криптовалюту"""
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустой строкой\n")
        if not isinstance(market_cap, (int, float)) or market_cap < 0:
            raise ValueError("Капитализация должна быть неотрицательным числом\n")
        self.algorithm = algorithm
        self.market_cap = float(market_cap)
    
    def get_display_info(self) -> str:
        """Возвращает строковое представление криптовалюты"""
        mcap_formatted = (f"{self.market_cap:.2e}" 
                        if self.market_cap >= 1e6 
                        else f"{self.market_cap:,.2f}")
        return (f"[CRYPTO] {self.code} — {self.name} (Algo: "
                f"{self.algorithm}, MCAP: {mcap_formatted})")


_SUPPORTED_CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "JPY": FiatCurrency("Japanese Yen", "JPY", "Japan"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "CNY": FiatCurrency("Chinese Yuan", "CNY", "China"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of History", 6.8e10),
    "ADA": CryptoCurrency("Cardano", "ADA", "Ouroboros", 1.5e10),
    "DOT": CryptoCurrency("Polkadot", "DOT", "Nominated Proof of Stake", 8.9e9),
}

def get_currency(code: str) -> Currency:
    """Фабричный метод для получения валюты по коду"""
    if not isinstance(code, str):
        raise CurrencyNotFoundError(f"Код валюты должен быть строкой: {code}\n")
    code_upper = code.upper().strip()
    if not code_upper:
        raise CurrencyNotFoundError("Код валюты не может быть пустой строкой\n")
    if code_upper not in _SUPPORTED_CURRENCIES:
        raise CurrencyNotFoundError(f"Неизвестная валюта '{code_upper}'\n")
    return _SUPPORTED_CURRENCIES[code_upper]