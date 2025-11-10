import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging():
    """Настройка логирования для приложения"""
    settings = SettingsLoader()
    
    log_dir = settings.get("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    actions_log_file = settings.get("ACTIONS_LOG_FILE", "actions.log")
    actions_log_path = os.path.join(log_dir, actions_log_file)
    
    parser_log_file = settings.get("PARSER_LOG_FILE", "parser.log")
    parser_log_path = os.path.join(log_dir, parser_log_file)
    
    actions_formatter = logging.Formatter(
        '%(levelname)s %(asctime)s %(action)s '
        'user=%(user)s%(extra_info)s result=%(result)s', 
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    parser_formatter = logging.Formatter(
        '%(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    actions_logger = logging.getLogger('valutatrade_hub.actions')
    log_level = settings.get("LOG_LEVEL", "INFO").upper()
    actions_logger.setLevel(getattr(logging, log_level, logging.INFO))
    actions_logger.handlers.clear()
    
    max_size_mb = settings.get("LOG_MAX_SIZE_MB", 10)
    backup_count = settings.get("LOG_BACKUP_COUNT", 3)
    
    actions_file_handler = RotatingFileHandler(
        actions_log_path,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    actions_file_handler.setFormatter(actions_formatter)
    actions_logger.addHandler(actions_file_handler)
    
    actions_console_handler = logging.StreamHandler()
    actions_console_handler.setFormatter(actions_formatter)
    actions_logger.addHandler(actions_console_handler)
    actions_logger.propagate = False
    
    parser_logger = logging.getLogger('valutatrade_hub.parser_service')
    parser_logger.setLevel(getattr(logging, log_level, logging.INFO))
    parser_logger.handlers.clear()
    
    parser_file_handler = RotatingFileHandler(
        parser_log_path,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    parser_file_handler.setFormatter(parser_formatter)
    parser_logger.addHandler(parser_file_handler)
    
    parser_console_handler = logging.StreamHandler()
    parser_console_handler.setFormatter(parser_formatter)
    parser_logger.addHandler(parser_console_handler)
    parser_logger.propagate = False
    
    main_logger = logging.getLogger('valutatrade_hub')
    main_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    return actions_logger, parser_logger

actions_logger, parser_logger = setup_logging()
logger = logging.getLogger('valutatrade_hub')