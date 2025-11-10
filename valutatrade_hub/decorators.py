import functools
from typing import Any, Callable

from valutatrade_hub.logging_config import actions_logger


def log_action(action: str, verbose: bool = False):
    """Декоратор для логирования доменных операций"""
    def decorator(func: Callable) -> Callable:
        """Внутренний декоратор"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            """Обертка функции с логированием"""
            log_data = {
                'action': action,
                'user': 'unknown',  
                'currency_code': None,
                'amount': None,
                'rate': None,
                'base': 'USD',
                'result': 'OK',
                'extra_info': ''
            }
            
            if args and len(args) > 0:
                instance = args[0]
                if hasattr(instance, 'current_user') and instance.current_user:
                    log_data['user'] = instance.current_user.username
                elif hasattr(instance, 'user_manager'):
                    user_manager = instance.user_manager
                    if (hasattr(user_manager, 'current_user') and 
                        user_manager.current_user):
                        log_data['user'] = user_manager.current_user.username
            
            if action in ['BUY', 'SELL']:
                if len(args) >= 2 and isinstance(args[1], str):
                    log_data['currency_code'] = args[1]
                if len(args) >= 3 and isinstance(args[2], (int, float)):
                    log_data['amount'] = f"{args[2]:.4f}"
                from valutatrade_hub.core.utils import get_exchange_rates
                try:
                    exchange_rates = get_exchange_rates()
                    currency = log_data['currency_code']
                    if currency and currency in exchange_rates:
                        log_data['rate'] = f"{exchange_rates[currency]:.2f}"
                except Exception:
                    pass
            
            try:
                result = func(*args, **kwargs)
                extra = {
                    'action': log_data['action'],
                    'user': log_data['user'],  
                    'result': log_data['result']
                }
                
                if log_data['currency_code']:
                    extra_info = f" currency='{log_data['currency_code']}'"
                    if log_data['amount']:
                        extra_info += f" amount={log_data['amount']}"
                    if log_data['rate']:
                        extra_info += f" rate={log_data['rate']}"
                    if log_data['base']:
                        extra_info += f" base='{log_data['base']}'"
                    extra_info += log_data['extra_info']
                    extra['extra_info'] = extra_info
                else:
                    extra['extra_info'] = log_data['extra_info']
                
                actions_logger.info('', extra=extra)
                return result
                
            except Exception as e:
                log_data['result'] = 'ERROR'
                error_type = e.__class__.__name__
                error_message = str(e)
                
                extra = {
                    'action': log_data['action'],
                    'user': log_data['user'],  
                    'result': log_data['result'],
                    'extra_info': (f" error_type={error_type} "
                        f"error_message='{error_message}'")
                }
                
                if log_data['currency_code']:
                    extra['extra_info'] = f" currency='{log_data['currency_code']}'"
                    if log_data['amount']:
                        extra['extra_info'] += f" amount={log_data['amount']}"
                    if log_data['rate']:
                        extra['extra_info'] += f" rate={log_data['rate']}"
                    if log_data['base']:
                        extra['extra_info'] += f" base='{log_data['base']}'"
                    extra['extra_info'] += (f" error_type={error_type} "
                                            f"error_message='{error_message}'")
                
                actions_logger.info('', extra=extra)
                raise
                
        return wrapper
    return decorator

def log_buy(verbose: bool = False):
    return log_action('BUY', verbose=verbose)

def log_sell(verbose: bool = False):
    return log_action('SELL', verbose=verbose)

def log_register(verbose: bool = False):
    return log_action('REGISTER', verbose=verbose)

def log_login(verbose: bool = False):
    return log_action('LOGIN', verbose=verbose)