import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


class CustomFormatter(logging.Formatter):
    """Кастомный форматтер для логирования с дополнительными полями"""
    
    def format(self, record):
        record.action = getattr(record, 'action', 'UNKNOWN')
        record.user = getattr(record, 'user', 'unknown')
        record.currency = getattr(record, 'currency', '')
        record.amount = getattr(record, 'amount', '')
        record.rate = getattr(record, 'rate', '')
        record.base = getattr(record, 'base', 'USD')
        record.result = getattr(record, 'result', 'OK')
        
        return super().format(record)


def setup_logging():
    """Настройка логирования для приложения"""
    settings = SettingsLoader()
    
    log_dir = settings.get("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = settings.get("LOG_FILE", "valutatrade.log")
    log_path = os.path.join(log_dir, log_file)
    
    formatter = CustomFormatter(
        '%(levelname)s %(asctime)s %(action)s user=%(user)s '
        'currency=%(currency)s amount=%(amount)s rate=%(rate)s '
        'base=%(base)s result=%(result)s - %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    max_size_mb = settings.get("LOG_MAX_SIZE_MB", 10)
    backup_count = settings.get("LOG_BACKUP_COUNT", 3)
    
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger('valutatrade_hub')
    log_level = settings.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    
    return logger

logger = setup_logging()