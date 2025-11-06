import json
import os


def load_json(file_path: str):
    """Загружает данные из JSON файла"""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_json(data: list, file_path: str):
    """Сохраняет данные в JSON файл"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def validate_currency_code(currency_code: str) -> str:
    """Валидирует и нормализует код валюты"""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты должен быть непустой строкой\n")
    return currency_code.upper()

def validate_amount(amount) -> float:
    """Валидирует сумму"""
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        raise TypeError("Сумма должна быть числом\n")
    
    if amount_float <= 0:
        raise ValueError("Сумма должна быть положительной\n")
    
    return amount_float

def get_exchange_rates():
    """Получает текущие курсы валют"""
    rates_data = load_json('data/rates.json')
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