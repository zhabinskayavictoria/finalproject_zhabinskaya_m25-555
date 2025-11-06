import datetime
import hashlib
import secrets
from typing import Any, Dict, Optional

from .models import Portfolio, User, Wallet
from .utils import (
    get_exchange_rates,
    load_json,
    save_json,
    validate_amount,
    validate_currency_code,
)


class UserManager:
    """Класс менеджер для работы с пользователями"""
    def __init__(self):
        """Инициализирует менеджер пользователей"""
        self.users_file = 'data/users.json'
        self.portfolios_file = 'data/portfolios.json'
        self.current_user: Optional[User] = None

    def register(self, username: str, password: str):
        """Регистрирует нового пользователя"""
        if not username or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым\n")
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов\n")
        
        users = load_json(self.users_file)
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
        save_json(users, self.users_file)
        
        portfolios = load_json(self.portfolios_file)
        portfolios.append({
            "user_id": user.user_id, 
            "wallets": {}
        })
        save_json(portfolios, self.portfolios_file)
        return (f"Пользователь '{username}' зарегистрирован (id={user_id})."
               f" Войдите: login --username {username} --password ***\n")

    def login(self, username: str, password: str):
        """Вход пользователя в систему"""
        users = load_json(self.users_file)
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
        self.portfolios_file = 'data/portfolios.json'

    def _get_user_portfolio_data(self):
        """Получает данные портфеля текущего пользователя"""
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login\n")
        portfolios = load_json(self.portfolios_file)
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
        save_json(portfolios, self.portfolios_file)
        return new_portfolio

    def _save_portfolio_data(self, portfolio_data: Dict[str, Any]):
        """Сохраняет данные портфеля"""
        portfolios = load_json(self.portfolios_file)
        user_id = self.user_manager.current_user.user_id
        for i, portfolio in enumerate(portfolios):
            if portfolio['user_id'] == user_id:
                portfolios[i] = portfolio_data
                break
        else:
            portfolios.append(portfolio_data)
        save_json(portfolios, self.portfolios_file)

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
        if not portfolio_data['wallets']:
            return "Ваш портфель пуст\n"
        
        wallets = {}
        for curr_code, wallet_data in portfolio_data['wallets'].items():
            wallets[curr_code] = Wallet(curr_code, wallet_data['balance'])
        portfolio = Portfolio(self.user_manager.current_user.user_id, wallets)
        exchange_rates = get_exchange_rates()
        try:
            total_value = portfolio.get_total_value(base_currency, exchange_rates)
        except ValueError as e:
            return f"Ошибка: {e}\n"
        username = self.user_manager.current_user.username
        output = [f"Портфель пользователя '{username}' (база: {base_currency}):"]
        for wallet in portfolio.wallets.values():
            currency = wallet.currency_code
            balance = wallet.balance
            
            if currency in exchange_rates:
                if base_currency in exchange_rates:
                    rate_to_base = (
                        exchange_rates[currency] / exchange_rates[base_currency]
                    )
                    value_in_base = balance * rate_to_base
                    output.append(
                        f"- {currency}: {balance:.4f} → "
                        f"{value_in_base:.2f} {base_currency}"
                        )
                else:
                    output.append(
                        f"- {currency}: {balance:.4f} → курс для"
                        f" {base_currency} не найден"
                        )
            else:
                output.append(f"- {currency}: {balance:.4f} → курс не найден")
        output.append("-" * 40)
        output.append(f"ИТОГО: {total_value:,.2f} {base_currency}\n")
        return "\n".join(output)

    def buy_currency(self, currency_code: str, amount: float):
        """Покупает валюту"""
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login\n")
        
        currency_code = validate_currency_code(currency_code)
        portfolio_data = self._get_user_portfolio_data()
        exchange_rates = get_exchange_rates()

        if currency_code not in exchange_rates:
            raise ValueError(f"Не удалось получить курс для {currency_code}→USD\n")
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
            raise ValueError(
                f"Недостаточно средств: требуется {cost_usd:.2f} USD, "
                f"доступно {old_usd_balance:.2f} USD\n"
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
        
    def sell_currency(self, currency_code: str, amount: float):
        """Продает валюту"""
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login\n")
        
        currency_code = validate_currency_code(currency_code)
        portfolio_data = self._get_user_portfolio_data()
        if currency_code not in portfolio_data['wallets']:
            raise ValueError(f"У вас нет кошелька '{currency_code}'. "
                f"Добавьте валюту: она создаётся автоматически при первой покупке.\n")
        
        amount = validate_amount(amount)
        currency_wallet = Wallet(currency_code, 
                                portfolio_data['wallets'][currency_code]['balance'])
        old_currency_balance = currency_wallet.balance
        if old_currency_balance < amount:
            raise ValueError(f"Недостаточно средств: доступно "
                            f"{old_currency_balance:.4f} {currency_code},"
                        f" требуется {amount:.4f} {currency_code}\n")
        
        exchange_rates = get_exchange_rates()
        if currency_code not in exchange_rates:
            raise ValueError(f"Не удалось получить курс для {currency_code}→USD\n")
        
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
        self.rates_file = 'data/rates.json'

    def get_rate(self, from_currency: str, to_currency: str):
        """Получает курс между двумя валютами"""
        from_currency = validate_currency_code(from_currency)
        to_currency = validate_currency_code(to_currency)
        rates_data = load_json(self.rates_file)
        if not rates_data or 'pairs' not in rates_data:
            return "Курсы валют недоступны. Повторите попытку позже.\n"
        
        pair = f"{from_currency}_{to_currency}"
        if pair in rates_data['pairs']:
            rate_data = rates_data['pairs'][pair]
            rate = rate_data['rate']
            updated_at = rate_data['updated_at']
            reverse_rate = 1 / rate if rate != 0 else 0
            return (f"Курс {from_currency}→{to_currency}: {rate:.6f}"
                    f" (обновлено: {updated_at})\n"
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
                return (f"Курс {from_currency}→{to_currency}: "
                        f"{cross_rate:.6f} (обновлено: {updated_at})\n"
                        f"Обратный курс {to_currency}→{from_currency}:"
                        f" {reverse_rate:.6f}\n")
        
        return (f"Курс {from_currency}→{to_currency} недоступен. "
                f"Повторите попытку позже.\n")