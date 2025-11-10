import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from valutatrade_hub.parser_service.config import ParserConfig


class RatesStorage:
    """Класс для работы с хранилищем курсов валют"""
    
    def __init__(self, config: ParserConfig):
        """Инициализирует хранилище курсов валют"""
        self.config = config
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создает необходимые директории, если они не существуют"""
        os.makedirs(os.path.dirname(self.config.RATES_FILE_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(self.config.HISTORY_FILE_PATH), exist_ok=True)
    
    def save_current_rates(self, rates_data: Dict[str, Any]) -> None:
        """Сохраняет текущие курсы в rates.json (атомарно)"""
        try:
            temp_path = f"{self.config.RATES_FILE_PATH}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(rates_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.config.RATES_FILE_PATH)
        except (IOError, OSError) as e:
            raise IOError(f"Failed to save rates: {str(e)}")
    
    def save_historical_record(self, record: Dict[str, Any]) -> None:
        """Сохраняет запись в exchange_rates.json"""
        try:
            records = self.load_historical_records()
            records.append(record)
            temp_path = f"{self.config.HISTORY_FILE_PATH}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.config.HISTORY_FILE_PATH)
        except (IOError, OSError) as e:
            raise IOError(f"Failed to save historical record: {str(e)}")
    
    def load_historical_records(self) -> List[Dict[str, Any]]:
        """Загружает записи из exchange_rates.json"""
        if not os.path.exists(self.config.HISTORY_FILE_PATH):
            return []
        try:
            with open(self.config.HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def load_current_rates(self) -> Dict[str, Any]:
        """Загружает текущие курсы из rates.json"""
        if not os.path.exists(self.config.RATES_FILE_PATH):
            return {}
        try:
            with open(self.config.RATES_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def create_historical_record(self, pair: str, rate: float, source: str, 
                            meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """Создает запись для сохранения"""
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        from_currency, to_currency = pair.split('_')
        timestamp_part = timestamp.replace(':', '-').replace('.', '-')
        record_id = f"{from_currency}_{to_currency}_{timestamp_part}"
        
        return {
            "id": record_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "timestamp": timestamp,
            "source": source,
            "meta": meta or {}
        }