import json
import os
from typing import Any, Dict, List

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """
    Singleton класс для управления JSON-хранилищем.
    Реализован через __new__ для простоты и читабельности.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.settings = SettingsLoader()
            self._initialized = True
    
    def load_users(self) -> List[Dict]:
        """Загружает список пользователей"""
        return self._load_json_file(self.settings.get("USERS_FILE"), [])
    
    def save_users(self, users: List[Dict]):
        """Сохраняет список пользователей"""
        self._save_json_file(self.settings.get("USERS_FILE"), users)
    
    def load_portfolios(self) -> List[Dict]:
        """Загружает список портфелей"""
        return self._load_json_file(self.settings.get("PORTFOLIOS_FILE"), [])
    
    def save_portfolios(self, portfolios: List[Dict]):
        """Сохраняет список портфелей"""
        self._save_json_file(self.settings.get("PORTFOLIOS_FILE"), portfolios)
    
    def load_rates(self) -> Dict:
        """Загружает курсы валют"""
        return self._load_json_file(self.settings.get("RATES_FILE"), {})
    
    def save_rates(self, rates: Dict):
        """Сохраняет курсы валют"""
        self._save_json_file(self.settings.get("RATES_FILE"), rates)
    
    def load_exchange_rates(self) -> Dict:
        """Загружает исторические курсы валют"""
        return self._load_json_file(self.settings.get("EXCHANGE_RATES_FILE"), {})
    
    def save_exchange_rates(self, exchange_rates: Dict):
        """Сохраняет исторические курсы валют"""
        self._save_json_file(self.settings.get("EXCHANGE_RATES_FILE"), exchange_rates)
    
    def _load_json_file(self, file_path: str, default: Any) -> Any:
        """
        Загружает данные из JSON файла.
        
        Args:
            file_path: Путь к файлу
            default: Значение по умолчанию если файл не существует
            
        Returns:
            Данные из файла или default
        """
        if not os.path.exists(file_path):
            return default
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
    
    def _save_json_file(self, file_path: str, data: Any):
        """
        Сохраняет данные в JSON файл.
        
        Args:
            file_path: Путь к файлу
            data: Данные для сохранения
        """
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)