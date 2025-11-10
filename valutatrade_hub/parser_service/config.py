import os
from dataclasses import dataclass, field
from typing import Dict, Tuple

from dotenv import load_dotenv

load_dotenv()

@dataclass
class ParserConfig:
    """Конфигурация для сервиса парсинга"""
    
    EXCHANGERATE_API_KEY: str = field(default_factory=lambda: 
        os.getenv("EXCHANGERATE_API_KEY", ""))
    
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: Tuple[str, ...] = field(default_factory=lambda: ("EUR", 
                                                                    "GBP", 
                                                                    "JPY", 
                                                                    "RUB", 
                                                                    "CNY", 
                                                                    ))
    CRYPTO_CURRENCIES: Tuple[str, ...] = field(default_factory=lambda: ("BTC", 
                                                                        "ETH", 
                                                                        "SOL", 
                                                                        "ADA", 
                                                                        "DOT"))
    
    CRYPTO_ID_MAP: Dict[str, str] = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum", 
        "SOL": "solana",
        "ADA": "cardano",
        "DOT": "polkadot",
    })
    
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"
    
    REQUEST_TIMEOUT: int = 10
    UPDATE_INTERVAL_MINUTES: int = 5
    
    def validate(self):
        """Проверяет корректность конфигурации"""
        if not self.EXCHANGERATE_API_KEY or self.EXCHANGERATE_API_KEY == "":
            raise ValueError("EXCHANGERATE_API_KEY не установлен.")
        if not all(isinstance(code, str) and 2 <= len(code) <= 5 for \
                code in self.FIAT_CURRENCIES):
            raise ValueError("Некорректные коды фиатных валют")
        if not all(isinstance(code, str) and 2 <= len(code) <= 5 for \
                code in self.CRYPTO_CURRENCIES):
            raise ValueError("Некорректные коды криптовалют")