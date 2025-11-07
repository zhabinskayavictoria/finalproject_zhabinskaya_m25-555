import datetime
import hashlib

from valutatrade_hub.core.exceptions import InsufficientFundsError


class User:
    """Класс пользователя системы."""
    def __init__(self, 
                user_id: int,
                username: str, 
                hashed_password: str, 
                salt: str, 
                registration_date: datetime.datetime):
        """Инициализирует пользователя."""
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    def get_user_info(self):
        """Возвращает информацию о пользователе без пароля"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat()
        }
        
    def get_user_data(self):
        """Возвращает все данные пользователя для сохранения."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }
        
    def change_password(self, new_password: str):
        """Изменяет пароль пользователю с проверками и хешированием"""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов\n")
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode('utf-8')
            ).hexdigest()

    def verify_password(self, password: str):
        """Проверяет правильность переданного пароля"""
        hashed = hashlib.sha256(
            (password + self._salt).encode('utf-8')
            ).hexdigest()
        return hashed == self._hashed_password

    @property
    def username(self):
        """Геттер. Возвращает имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str):
        """Сеттер. Устанавливает имя пользователя."""
        if not value or value.strip() == '':
            raise ValueError("Имя пользователя не может быть пустым\n")
        self._username = value

    @property
    def user_id(self):
        """Геттер. Возвращает ID пользователя."""
        return self._user_id

    @property
    def registration_date(self):
        """Геттер. Возвращает дату регистрации."""
        return self._registration_date

    @property
    def salt(self):
        """Геттер. Возвращает соль для хеширования."""
        return self._salt

    @property
    def hashed_password(self):
        """Геттер. Возвращает хешированный пароль."""
        return self._hashed_password


class Wallet:
    """Класс кошелька для хранения валюты."""
    def __init__(self, currency_code: str, balance: float = 0.0):
        """Инициализирует кошелек."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("currency_code не может быть пустым\n")
        self.currency_code = currency_code.upper()
        self._balance = 0.0
        self.balance = balance

    def deposit(self, amount: float):
        """Пополняет баланс."""
        if not isinstance(amount, (int, float)):
            raise TypeError("amount должен быть числом\n")
        if amount <= 0:
            raise ValueError("amount должен быть > 0\n")
        self._balance += float(amount)

    def withdraw(self, amount: float):
        """Снимает средства с баланса."""
        if not isinstance(amount, (int, float)):
            raise TypeError("amount должен быть числом\n")
        if amount <= 0:
            raise ValueError("amount должен быть > 0\n")
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance, 
                required=amount, 
                code=self.currency_code
            )
        self._balance -= float(amount)

    def get_balance_info(self):
        """Возвращает информацию о балансе."""
        return f"{self.currency_code}, balance: {self._balance:.6f}"

    @property
    def balance(self):
        """Геттер. Возвращает текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value):
        """Сеттер. Устанавливает баланс."""
        if not isinstance(value, (int, float)):
            raise TypeError("balance должен быть числом\n")
        if value < 0:
            raise ValueError("balance должен быть > 0\n")
        self._balance = float(value)


class Portfolio:
    """Класс портфеля кошельков пользователя."""
    def __init__(self, user_id: int, wallets: dict = None):
        """Инициализирует портфель."""
        if not isinstance(user_id, int):
            raise TypeError("user_id должен быть int\n")
        self._user_id = user_id
        self._wallets = dict(wallets) if wallets is not None else {}

    def add_currency(self, currency_code: str):
        """Добавляет новый кошелёк в портфель, если его ещё нет."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("currency_code не может быть пустым\n")
        code = currency_code.upper()
        if code in self._wallets:
            raise ValueError(f"Валюта {code} уже есть в портфеле\n")
        new_wallet = Wallet(code, balance=0.0)
        self._wallets[code] = new_wallet

    def get_wallet(self, currency_code: str):
        """Возвращает Wallet по коду валюты"""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("currency_code не может быть пустым\n")
        code = currency_code.upper()
        if code not in self._wallets:
            raise ValueError(f"Валюта {currency_code} не найдена в портфеле\n")
        wallet = self._wallets.get(code)
        return wallet

    def get_total_value(self, base_currency: str = "USD", exchange_rates: dict = None):
        """Считает общую стоимость портфеля в базовой валюте base_currency."""
        if exchange_rates is None:
            exchange_rates = {
                "USD": 1.0,
                "EUR": 1.10,
                "GBP": 1.30,
                "JPY": 0.009
            }
        base = (base_currency or "USD").upper()
        if base not in exchange_rates:
            raise ValueError(f"Неизвестная базовая валюта: {base_currency}\n")
        total = 0.0
        for wallet in self._wallets.values():
            code = wallet.currency_code.upper()
            if code not in exchange_rates:
                raise ValueError(f"Нет курса для валюты {code}\n")
            rate_to_base = exchange_rates[code] / exchange_rates[base]
            total += wallet.balance * rate_to_base
        return total

    @property
    def user_id(self):
        """Геттер. Возвращает ID пользователя."""
        return self._user_id

    @property
    def wallets(self):
        """Геттер. Возвращает копию словаря кошельков."""
        return self._wallets.copy()