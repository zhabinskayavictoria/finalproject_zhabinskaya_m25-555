from datetime import datetime, timedelta

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


def validate_currency_code(currency_code: str) -> str:
    """Валидирует и нормализует код валюты"""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты должен быть непустой строкой\n")
    code = currency_code.upper().strip()
    try:
        get_currency(code)
    except CurrencyNotFoundError:
        raise CurrencyNotFoundError(code)
    return code

def validate_amount(amount) -> float:
    """Валидирует сумму"""
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        raise TypeError("Сумма должна быть числом\n")
    if amount_float <= 0:
        raise ValueError("Сумма должна быть положительной\n")
    return amount_float

def is_rate_fresh(updated_at: str):
    """Проверяет свежесть курса валюты"""
    settings = SettingsLoader()
    
    try:
        update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        ttl_seconds = settings.get("RATES_TTL_SECONDS", 300)
        expiry_time = update_time + timedelta(seconds=ttl_seconds)
        return datetime.now().astimezone() < expiry_time
    except (ValueError, TypeError):
        return False
    
def get_exchange_rates():
    """Получает текущие курсы валют"""
    database = DatabaseManager()
    rates_data = database.load_rates()
    if not rates_data or 'pairs' not in rates_data:
        return {
            "USD": 1.0,
            "EUR": 1.10,
            "GBP": 1.30,
            "JPY": 0.009,
            "BTC": 59337.21,
            "ETH": 3720.00,
            "RUB": 0.01016,
            "SOL": 145.12
        }
    rates = {}
    for pair, data in rates_data['pairs'].items():
        from_curr = pair.split('_')[0]
        rates[from_curr] = data['rate']
    rates["USD"] = 1.0
    return rates
