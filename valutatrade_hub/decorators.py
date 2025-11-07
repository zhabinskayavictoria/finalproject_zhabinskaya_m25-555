import functools
from typing import Any, Callable

from valutatrade_hub.logging_config import logger


def log_action(action: str, verbose: bool = False):
    """Декоратор для логирования доменных операций"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            log_extra = {
                'action': action,
                'user': 'unknown',  
                'currency': None,
                'amount': None,
                'rate': None,
                'base': 'USD',
                'result': 'OK'
            }
            
            if args and len(args) > 0:
                instance = args[0]
                
                if hasattr(instance, 'user_manager'):
                    user_manager = instance.user_manager
                    if hasattr(user_manager, 'current_user') and user_manager.current_user:
                        log_extra['user'] = user_manager.current_user.username
                elif hasattr(instance, 'current_user') and instance.current_user:
                    log_extra['user'] = instance.current_user.username
                
                if action in ['BUY', 'SELL']:
                    if len(args) >= 2 and isinstance(args[1], str):
                        log_extra['currency'] = args[1]
                    if len(args) >= 3 and isinstance(args[2], (int, float)):
                        log_extra['amount'] = f"{args[2]:.4f}"
            
            if action in ['BUY', 'SELL'] and log_extra['currency']:
                from valutatrade_hub.core.utils import get_exchange_rates
                try:
                    exchange_rates = get_exchange_rates()
                    currency = log_extra['currency']
                    if currency in exchange_rates:
                        log_extra['rate'] = f"{exchange_rates[currency]:.2f}"
                except Exception:
                    pass
            
            try:
                result = func(*args, **kwargs)
                
                if action in ['BUY', 'SELL']:
                    message = (f"{action} {log_extra['amount']} {log_extra['currency']} "
                            f"at rate {log_extra['rate']}")
                elif action in ['REGISTER', 'LOGIN']:
                    username = args[1] if len(args) >= 2 else 'unknown'
                    message = f"{action} user {username}"
                else:
                    message = f"{action} operation completed"
                
                if verbose and action in ['BUY', 'SELL'] and hasattr(instance, '_get_user_portfolio_data'):
                    try:
                        portfolio_data = instance._get_user_portfolio_data()
                        if log_extra['currency'] in portfolio_data['wallets']:
                            balance = portfolio_data['wallets'][log_extra['currency']]['balance']
                            message += f" | Balance: {balance:.4f} {log_extra['currency']}"
                    except Exception:
                        pass
                
                logger.info(message, extra=log_extra)
                return result
                
            except Exception as e:
                log_extra['result'] = 'ERROR'
                error_message = f"{e.__class__.__name__}: {str(e)}"
                logger.info(error_message, extra=log_extra)
                raise
                
        return wrapper
    return decorator


def log_buy(verbose: bool = False):
    """Специализированный декоратор для операций покупки"""
    return log_action('BUY', verbose=verbose)


def log_sell(verbose: bool = False):
    """Специализированный декоратор для операций продажи"""
    return log_action('SELL', verbose=verbose)


def log_register(verbose: bool = False):
    """Специализированный декоратор для регистрации"""
    return log_action('REGISTER', verbose=verbose)


def log_login(verbose: bool = False):
    """Специализированный декоратор для входа"""
    return log_action('LOGIN', verbose=verbose)