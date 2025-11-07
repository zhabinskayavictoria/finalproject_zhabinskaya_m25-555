import tomllib
from typing import Any


class SettingsLoader:
    """Singleton класс для загрузки конфигурации проекта"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._config = {}
            self._load_config()
            self._initialized = True
    
    def _load_config(self):
        """Загружает конфигурацию из pyproject.toml"""
        default_config = {
            "DATA_DIR": "data",
            "USERS_FILE": "data/users.json",
            "PORTFOLIOS_FILE": "data/portfolios.json", 
            "RATES_FILE": "data/rates.json",
            "EXCHANGE_RATES_FILE": "data/exchange_rates.json",
            "RATES_TTL_SECONDS": 300,
            "DEFAULT_BASE_CURRENCY": "USD",
            "LOG_DIR": "logs",
            "LOG_FILE": "valutatrade.log",
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "text",
            "LOG_MAX_SIZE_MB": 10,
            "LOG_BACKUP_COUNT": 3,
        }
    
        try:
            with open('pyproject.toml', 'rb') as f:
                config_data = tomllib.load(f)
            valutatrade_config = config_data.get('tool', {}).get('valutatrade', {})
            for key, value in valutatrade_config.items():
                default_config[key.upper()] = value
        except (FileNotFoundError, tomllib.TOMLDecodeError, KeyError):
            pass
        
        self._config = default_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение конфигурации по ключу"""
        return self._config.get(key, default)
    
    def reload(self):
        """Перезагружает конфигурацию"""
        self._load_config()