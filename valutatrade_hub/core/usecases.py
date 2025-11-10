import datetime
import hashlib
import secrets
from typing import Any, Dict, Optional

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.decorators import log_buy, log_login, log_register, log_sell
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

from .models import Portfolio, User, Wallet
from .utils import (
    get_exchange_rates,
    is_rate_fresh,
    validate_amount,
)


class UserManager:
    """Класс менеджер для работы с пользователями"""
    def __init__(self):
        """Инициализирует менеджер пользователей"""
        self.database = DatabaseManager()
        self.current_user: Optional[User] = None

    @log_register(verbose=True)
    def register(self, username: str, password: str):
        """Регистрирует нового пользователя"""
        if not username or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым\n")
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов\n")
        
        users = self.database.load_users()
        for user_data in users:
            if user_data['username'] == username:
                raise ValueError(f"Имя пользователя '{username}' уже занято\n")
        
        user_id = 1
        if users:
            user_id = max(user['user_id'] for user in users) + 1
        
        salt = secrets.token_hex(8)
        hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        registration_date = datetime.datetime.now()
        
        user = User(user_id, username, hashed_password, salt, registration_date)
        users.append(user.get_user_data())  
        self.database.save_users(users)
        
        portfolios = self.database.load_portfolios()
        portfolios.append({
            "user_id": user.user_id, 
            "wallets": {}
        })
        self.database.save_portfolios(portfolios)
        
        return (f"Пользователь '{username}' зарегистрирован (id={user_id})."
               f" Войдите: login --username {username} --password ***\n")
    
    @log_login(verbose=True)
    def login(self, username: str, password: str):
        """Вход пользователя в систему"""
        users = self.database.load_users()
        user_data = None
        for u in users:
            if u['username'] == username:
                user_data = u
                break
        if not user_data:
            raise ValueError(f"Пользователь '{username}' не найден\n")
        
        registration_date = datetime.datetime.fromisoformat(
            user_data['registration_date'])
        
        temp_user = User(
            user_data['user_id'],
            user_data['username'],
            user_data['hashed_password'],
            user_data['salt'],
            registration_date
        )
        if not temp_user.verify_password(password):
            raise ValueError("Неверный пароль\n")
        
        self.current_user = temp_user
        return f"Вы вошли как '{username}'\n" 

    def get_current_user(self):
        """Возвращает текущего пользователя"""
        return self.current_user



class PortfolioManager:
    """Класс менеджер для работы с портфелями пользователей."""
    def __init__(self, user_manager: UserManager):
        """Инициализирует менеджер портфелей."""
        self.user_manager = user_manager
        self.database = DatabaseManager()
        self.settings = SettingsLoader()

    def _get_user_portfolio_data(self):
        """Получает данные портфеля текущего пользователя"""
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login\n")
        
        portfolios = self.database.load_portfolios()
        user_id = self.user_manager.current_user.user_id
        
        for portfolio in portfolios:
            if portfolio['user_id'] == user_id:
                return portfolio
            
        portfolio_obj = Portfolio(user_id)
        new_portfolio = {
            "user_id": portfolio_obj.user_id, 
            "wallets": {}
        }
        portfolios.append(new_portfolio)
        self.database.save_portfolios(portfolios)
        return new_portfolio

    def _save_portfolio_data(self, portfolio_data: Dict[str, Any]):
        """Сохраняет данные портфеля"""
        portfolios = self.database.load_portfolios()
        user_id = self.user_manager.current_user.user_id
        
        found = False
        for i, portfolio in enumerate(portfolios):
            if portfolio['user_id'] == user_id:
                portfolios[i] = portfolio_data
                found = True
                break
        if not found:
            portfolios.append(portfolio_data)
            
        self.database.save_portfolios(portfolios)

    def deposit_usd(self, amount: float):
        """Пополняет USD кошелек"""
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login\n")
        amount = validate_amount(amount)
        portfolio_data = self._get_user_portfolio_data()
        if 'USD' in portfolio_data['wallets']:
            usd_wallet = Wallet('USD', portfolio_data['wallets']['USD']['balance'])
            old_balance = usd_wallet.balance
            usd_wallet.deposit(amount) 
            new_balance = usd_wallet.balance
            portfolio_data['wallets']['USD']['balance'] = usd_wallet.balance
        else:
            usd_wallet = Wallet('USD', amount)
            old_balance = 0.0
            new_balance = usd_wallet.balance
            portfolio_data['wallets']['USD'] = {'balance': usd_wallet.balance}
        self._save_portfolio_data(portfolio_data)
        return (f"Пополнение выполнено: {amount:.2f} USD\n"
                f"Баланс USD: было {old_balance:.2f} → стало {new_balance:.2f}\n")

    def show_portfolio(self, base_currency: str = "USD"):
        """Показывает портфель пользователя"""
        portfolio_data = self._get_user_portfolio_data()
        base_currency = (base_currency or 
                        self.settings.get("DEFAULT_BASE_CURRENCY", "USD"))
        
        if not portfolio_data['wallets']:
            return "Ваш портфель пуст\n"
        
        wallets = {}
        for curr_code, wallet_data in portfolio_data['wallets'].items():
            wallets[curr_code] = Wallet(curr_code, wallet_data['balance'])
        portfolio = Portfolio(self.user_manager.current_user.user_id, wallets)
        exchange_rates = get_exchange_rates()
        
        rates_data = self.database.load_rates()
        warning_msg = ""
        if rates_data and 'last_refresh' in rates_data:
            last_refresh = rates_data.get('last_refresh')
            if last_refresh and not is_rate_fresh(last_refresh):
                ttl_minutes = self.settings.get("RATES_TTL_SECONDS", 300) // 60
                warning_msg = (f"\nВНИМАНИЕ: Данные курсов устарели "
                            f"(TTL: {ttl_minutes} мин). "
                            f"Используйте 'update-rates' для обновления.")
            
        try:
            total_value = portfolio.get_total_value(base_currency, exchange_rates)
        except ValueError as e:
            return f"Ошибка: {e}\n"
        
        username = self.user_manager.current_user.username
        output = [f"Портфель пользователя '{username}' (база: {base_currency}):"]
        
        for wallet in portfolio.wallets.values():
            currency = wallet.currency_code
            balance = wallet.balance
            
            try:
                currency_obj = get_currency(currency)
                currency_info = currency_obj.get_display_info().strip()
            except CurrencyNotFoundError:
                currency_info = f"Неизвестная валюта: {currency}"
        
            if currency in exchange_rates:
                if base_currency in exchange_rates:
                    rate_to_base = (
                        exchange_rates[currency] / exchange_rates[base_currency]
                    )
                    value_in_base = balance * rate_to_base
                    output.append(
                        f"- {currency_info}"
                        f"\n  Баланс: {balance:.4f} → "
                        f"{value_in_base:.2f} {base_currency}"
                    )
                else:
                    output.append(
                        f"- {currency_info}"
                        f"\n  Баланс: {balance:.4f} → курс для"
                        f" {base_currency} не найден"
                    )
            else:
                output.append(
                    f"- {currency_info}"
                    f"\n  Баланс: {balance:.4f} → курс не найден"
                )
        output.append("-" * 40)
        output.append(f"ИТОГО: {total_value:,.2f} {base_currency}\n")
        if warning_msg:
            output.append(warning_msg+"\n")
        return "\n".join(output)
        
    @log_buy(verbose=True)
    def buy_currency(self, currency_code: str, amount: float):
        """Покупает валюту"""
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login\n")
        
        try:
            currency = get_currency(currency_code)
            currency_code = currency.code  
        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(currency_code)
        
        portfolio_data = self._get_user_portfolio_data()
        exchange_rates = get_exchange_rates()
        
        rates_data = self.database.load_rates()
        if rates_data and 'last_refresh' in rates_data:
            last_refresh = rates_data.get('last_refresh')
            if last_refresh and not is_rate_fresh(last_refresh):
                ttl_minutes = self.settings.get("RATES_TTL_SECONDS", 300) // 60
                raise ApiRequestError(f"Данные курсов устарели (TTL: "
                                    f"{ttl_minutes} мин). "
                                    f"Используйте команду update-rates для обновления.")

        if currency_code not in exchange_rates:
            raise ApiRequestError(f"Не удалось получить курс для {currency_code}→USD")
                
        amount = validate_amount(amount)
        rate = exchange_rates[currency_code]
        cost_usd = amount * rate
        usd_wallet = None
        
        if 'USD' in portfolio_data['wallets']:
            usd_wallet = Wallet('USD', portfolio_data['wallets']['USD']['balance'])
            old_usd_balance = usd_wallet.balance
        else:
            old_usd_balance = 0.0
        
        if old_usd_balance < cost_usd:
            raise InsufficientFundsError(
                available=old_usd_balance,
                required=cost_usd,
                code='USD'
            )
        
        if currency_code in portfolio_data['wallets']:
            currency_wallet = Wallet(currency_code, 
                                    portfolio_data['wallets'][currency_code]['balance'])
            old_currency_balance = currency_wallet.balance
        else:
            currency_wallet = Wallet(currency_code, 0.0)
            old_currency_balance = 0.0
        
        if usd_wallet:
            usd_wallet.withdraw(cost_usd) 
            new_usd_balance = usd_wallet.balance
            portfolio_data['wallets']['USD']['balance'] = usd_wallet.balance
        else:
            usd_wallet = Wallet('USD', -cost_usd)
            new_usd_balance = usd_wallet.balance
            portfolio_data['wallets']['USD'] = {'balance': usd_wallet.balance}
        
        currency_wallet.deposit(amount)
        new_currency_balance = currency_wallet.balance
        portfolio_data['wallets'][currency_code] = {'balance': currency_wallet.balance}
        self._save_portfolio_data(portfolio_data)
        
        return (f"Покупка выполнена: {amount:.4f} {currency_code} "
                f"по курсу {rate:.2f} USD/{currency_code}\n"
                f"Изменения в портфеле:\n"
                f"- {currency_code}: было {old_currency_balance:.4f} →"
                f" стало {new_currency_balance:.4f}\n"
                f"- USD: было {old_usd_balance:.2f} → стало {new_usd_balance:.2f}\n"
                f"Оценочная стоимость покупки: {cost_usd:.2f} USD\n")
    
    @log_sell(verbose=True)
    def sell_currency(self, currency_code: str, amount: float):
        """Продает валюту"""
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login\n")
        
        try:
            currency = get_currency(currency_code)
            currency_code = currency.code  
        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(currency_code)
        
        portfolio_data = self._get_user_portfolio_data()
        
        if currency_code not in portfolio_data['wallets']:
            raise ValueError(f"У вас нет кошелька '{currency_code}'. "
                f"Добавьте валюту: она создаётся автоматически при первой покупке.\n")
        
        amount = validate_amount(amount)
        currency_wallet = Wallet(currency_code, 
                                portfolio_data['wallets'][currency_code]['balance'])
        old_currency_balance = currency_wallet.balance
        
        if old_currency_balance < amount:
            raise InsufficientFundsError(
                available=old_currency_balance,
                required=amount,
                code=currency_code
            )
        
        rates_data = self.database.load_rates()
        if rates_data and 'last_refresh' in rates_data:
            last_refresh = rates_data.get('last_refresh')
            if last_refresh and not is_rate_fresh(last_refresh):
                ttl_minutes = self.settings.get("RATES_TTL_SECONDS", 300) // 60
                raise ApiRequestError(f"Данные курсов устарели (TTL: {ttl_minutes}мин)."
                                    f"Используйте команду update-rates для обновления.")

        exchange_rates = get_exchange_rates()
        if currency_code not in exchange_rates:
            raise ApiRequestError(f"Не удалось получить курс для {currency_code}→USD")
        
        rate = exchange_rates[currency_code]
        revenue_usd = amount * rate
        if 'USD' in portfolio_data['wallets']:
            usd_wallet = Wallet('USD', portfolio_data['wallets']['USD']['balance'])
            old_usd_balance = usd_wallet.balance
        else:
            usd_wallet = Wallet('USD', 0.0)
            old_usd_balance = 0.0
        
        currency_wallet.withdraw(amount) 
        new_currency_balance = currency_wallet.balance
        usd_wallet.deposit(revenue_usd)
        new_usd_balance = usd_wallet.balance
        portfolio_data['wallets'][currency_code] = {'balance': currency_wallet.balance}
        portfolio_data['wallets']['USD'] = {'balance': usd_wallet.balance}
        self._save_portfolio_data(portfolio_data)
        
        return (f"Продажа выполнена: {amount:.4f} {currency_code}"
                f" по курсу {rate:.2f} USD/{currency_code}\n"
                f"Изменения в портфеле:\n"
                f"- {currency_code}: было {old_currency_balance:.4f} →"
                f" стало {new_currency_balance:.4f}\n"
                f"- USD: было {old_usd_balance:.2f} → стало {new_usd_balance:.2f}\n"
                f"Оценочная выручка: {revenue_usd:.2f} USD\n")


class RateManager:
    """Класс менеджер для работы с курсами валют."""
    def __init__(self):
        """Инициализирует менеджер курсов."""
        self.database = DatabaseManager()
        self.settings = SettingsLoader()

    def get_rate(self, from_currency: str, to_currency: str):
        """Получает курс между двумя валютами"""
        try:
            from_currency_obj = get_currency(from_currency)
            to_currency_obj = get_currency(to_currency)
            from_currency = from_currency_obj.code
            to_currency = to_currency_obj.code
        except CurrencyNotFoundError as e:
            raise e
        
        rates_data = self.database.load_rates()
        if not rates_data or 'pairs' not in rates_data:
            raise ApiRequestError("Курсы валют недоступны")
        

        last_refresh = rates_data.get('last_refresh')
        warning_msg = ""
        if last_refresh and not is_rate_fresh(last_refresh):
            ttl_minutes = self.settings.get("RATES_TTL_SECONDS", 300) // 60
            warning_msg = (f"\nВНИМАНИЕ: Данные курсов устарели "
                        f"(TTL: {ttl_minutes}мин)."
                        f"Используйте 'update-rates' для обновления.")
                
        pair = f"{from_currency}_{to_currency}"
        if pair in rates_data['pairs']:
            rate_data = rates_data['pairs'][pair]
            rate = rate_data['rate']
            updated_at = rate_data['updated_at']
            reverse_rate = 1 / rate if rate != 0 else 0
            return (f"{warning_msg}\n"
                    f"Курс {from_currency}→{to_currency}: {rate:.6f}"
                    f" (обновлено: {updated_at})\n"
                    f"Обратный курс {to_currency}→{from_currency}: "
                    f"{reverse_rate:.6f}\n")
        
        reverse_pair = f"{to_currency}_{from_currency}"
        if reverse_pair in rates_data['pairs']:
            rate_data = rates_data['pairs'][reverse_pair]
            reverse_rate = rate_data['rate']
            rate = 1 / reverse_rate if reverse_rate != 0 else 0
            updated_at = rate_data['updated_at']
            return (f"{warning_msg}\n"
                    f"Курс {from_currency}→{to_currency}: {rate:.6f}"
                    f" (обновлено: {updated_at})"
                    f"Обратный курс {to_currency}→{from_currency}: "
                    f"{reverse_rate:.6f}\n")
        
        usd_pair1 = f"{from_currency}_USD"
        usd_pair2 = f"{to_currency}_USD"
        if usd_pair1 in rates_data['pairs'] and usd_pair2 in rates_data['pairs']:
            rate1 = rates_data['pairs'][usd_pair1]['rate']
            rate2 = rates_data['pairs'][usd_pair2]['rate']
            if rate2 != 0:
                cross_rate = rate1 / rate2
                updated_at = rates_data['pairs'][usd_pair1]['updated_at']
                reverse_rate = 1 / cross_rate if cross_rate != 0 else 0
                return (f"{warning_msg}\n"
                        f"Курс {from_currency}→{to_currency}: "
                        f"{cross_rate:.6f} (обновлено: {updated_at})\n"
                        f"Обратный курс {to_currency}→{from_currency}:"
                        f" {reverse_rate:.6f}\n")
        
        raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен")