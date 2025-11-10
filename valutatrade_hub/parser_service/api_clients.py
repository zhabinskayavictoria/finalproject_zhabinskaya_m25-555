from abc import ABC, abstractmethod
from typing import Dict

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Абстрактный базовый класс для API клиентов"""
    
    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы валют и возвращает словарь {валютная_пара: курс}"""
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент для работы с CoinGecko API"""
    
    def __init__(self, config: ParserConfig):
        """Инициализирует клиент CoinGecko"""
        self.config = config
    
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы криптовалют от CoinGecko"""
        try:
            crypto_ids = list(self.config.CRYPTO_ID_MAP.values())
            if not crypto_ids:
                return {}
                
            ids_param = ",".join(crypto_ids)
            url = f"{self.config.COINGECKO_URL}?ids={ids_param}&vs_currencies=usd"
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            for crypto_code, crypto_id in self.config.CRYPTO_ID_MAP.items():
                if crypto_id in data and "usd" in data[crypto_id]:
                    pair_key = f"{crypto_code}_USD"
                    rates[pair_key] = float(data[crypto_id]["usd"])
            return rates
            
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko API error: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            raise ApiRequestError(f"CoinGecko data parsing error: {str(e)}")


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для работы с ExchangeRate-API"""
    
    def __init__(self, config: ParserConfig):
        """Инициализирует клиент ExchangeRate-API"""
        self.config = config
    
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы фиатных валют от ExchangeRate-API"""
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("ExchangeRate-API key not configured")
        try:
            url = (f"{self.config.EXCHANGERATE_API_URL}/"
                f"{self.config.EXCHANGERATE_API_KEY}/latest/USD")
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if data.get("result") != "success":
                error_type = data.get('error-type', 'Unknown error')
                raise ApiRequestError(f"ExchangeRate-API returned: {error_type}")
            
            rates_data = data.get("conversion_rates", {})
            rates = {}
            for currency in self.config.FIAT_CURRENCIES:
                if currency in rates_data and currency != "USD":
                    pair_key = f"{currency}_USD"
                    rates[pair_key] = 1.0 / float(rates_data[currency])
            return rates

        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.ConnectionError):
                raise ApiRequestError(f"Network connection error: {str(e)}")
            elif isinstance(e, requests.exceptions.Timeout):
                raise ApiRequestError(f"Request timeout: {str(e)}")
            elif isinstance(e, requests.exceptions.HTTPError):
                if response.status_code == 429:
                    raise ApiRequestError("Rate limit exceeded (429 Too Many Requests)")
                elif response.status_code == 401:
                    raise ApiRequestError("Invalid API key (401 Unauthorized)")
                else:
                    raise ApiRequestError(f"HTTP error {response.status_code}:{str(e)}")
            else:
                raise ApiRequestError(f"Request error: {str(e)}")