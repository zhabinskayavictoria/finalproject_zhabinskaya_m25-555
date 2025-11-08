import shlex

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import PortfolioManager, RateManager, UserManager


class CLIInterface:
    """Консольный интерфейс для управления валютным портфелем."""
    
    def __init__(self):
        """Инициализирует менеджеры пользователей, портфеля и курсов."""
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager(self.user_manager)
        self.rate_manager = RateManager()
        self.running = False

    def print_help(self):
        """Выводит справку по командам"""
        help_text = """
        Доступные команды:

        Регистрация и вход:
        register --username <name> --password <pass>  - Зарегистрировать пользователя
        login --username <name> --password <pass>     - Войти в систему

        Работа с портфелем:
        show-portfolio [--base <currency>]           - Показать портфель 
                                                    (базовая валюта по умолчанию: USD)
        deposit --amount <sum>                       - Пополнить USD кошелек
        buy --currency <code> --amount <sum>         - Купить валюту за USD
        sell --currency <code> --amount <sum>        - Продать валюту за USD

        Курсы валют:
        get-rate --from <code> --to <code>           - Получить курс между валютами

        Прочие команды:
        help                                        - Показать команды
        exit                                        - Выйти из приложения\n
        """
        print(help_text)

    def parse_arguments(self, command_line: str):
        """Парсит аргументы командной строки"""
        try:
            args = shlex.split(command_line)
            return args
        except ValueError as e:
            print(f"Ошибка парсинга команды: {e}\n")
            return None

    def _parse_simple_args(self, args, expected_args):
        """Парсер аргументов вида --key value"""
        parsed = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--'):
                key = args[i][2:]
                if i + 1 < len(args) and not args[i + 1].startswith('--'):
                    parsed[key] = args[i + 1]
                    i += 2
                else:
                    parsed[key] = None
                    i += 1
            else:
                i += 1
        missing = []
        for arg in expected_args:
            if arg not in parsed or parsed[arg] is None:
                missing.append(f"--{arg}")
        return parsed, missing

    def handle_register(self, args):
        """Обрабатывает команду register"""
        parsed, missing = self._parse_simple_args(args, ['username', 'password'])
        if missing:
            if '--username' in missing or '--password' in missing:
                print("Ошибка в команде: register --username <name> "
                    "--password <pass>\n")
            return
        try:
            result = self.user_manager.register(parsed['username'], parsed['password'])
            print(result)
        except Exception as e:
            print(f"Ошибка: {e}\n")

    def handle_login(self, args):
        """Обрабатывает команду login"""
        parsed, missing = self._parse_simple_args(args, ['username', 'password'])
        if missing:
            if '--username' in missing or '--password' in missing:
                print("Ошибка в команде: login --username <name> --password <pass>\n")
            return
        try:
            result = self.user_manager.login(parsed['username'], parsed['password'])
            print(result)
        except Exception as e:
            print(f"Ошибка: {e}\n")

    def handle_deposit(self, args):
        """Обрабатывает команду deposit"""
        parsed, missing = self._parse_simple_args(args, ['amount'])
        if missing:
            print("Ошибка в команде: deposit --amount <sum>\n")
            return
        try:
            amount = float(parsed['amount'])
            result = self.portfolio_manager.deposit_usd(amount)
            print(result)
        except ValueError:
            print("Ошибка: Сумма должна быть числом\n")
        except Exception as e:
            print(f"Ошибка: {e}\n")

    def handle_show_portfolio(self, args):
        """Обрабатывает команду show-portfolio"""
        parsed, _ = self._parse_simple_args(args, [])
        base_currency = parsed.get('base', 'USD')
        try:
            result = self.portfolio_manager.show_portfolio(base_currency)
            print(result)
        except Exception as e:
            print(f"Ошибка: {e}\n")

    def handle_buy(self, args):
        """Обрабатывает команду buy"""
        parsed, missing = self._parse_simple_args(args, ['currency', 'amount'])
        if missing:
            if '--currency' in missing or '--amount' in missing:
                print("Ошибка в команде: buy --currency <code> --amount <sum>\n")
            return

        try:
            amount = float(parsed['amount'])
        except ValueError:
            print("Ошибка: Сумма должна быть числом\n")
            return
        if amount <= 0:
            print("Ошибка: Сумма должна быть положительной\n")
            return
        
        try:
            amount = float(parsed['amount'])
            result = self.portfolio_manager.buy_currency(parsed['currency'], amount)
            print(result)
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Доступные валюты: USD, EUR, GBP, JPY, RUB, CNY, BTC, ETH, SOL, ADA, DOT")
            print("Используйте правильные коды валют в верхнем регистре\n")
        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
            print("Пополните баланс USD с помощью команды 'deposit --amount <сумма>'\n")
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже или проверьте подключение к сети\n")
        except Exception as e:
            print(f"Ошибка: {e}\n")

    def handle_sell(self, args):
        """Обрабатывает команду sell"""
        parsed, missing = self._parse_simple_args(args, ['currency', 'amount'])
        if missing:
            if '--currency' in missing or '--amount' in missing:
                print("Ошибка в команде: sell --currency <code> --amount <sum>\n")
            return

        try:
            amount = float(parsed['amount'])
        except ValueError:
            print("Ошибка: Сумма должна быть числом\n")
            return
        if amount <= 0:
            print("Ошибка: Сумма должна быть положительной\n")
            return
        
        try:
            result = self.portfolio_manager.sell_currency(parsed['currency'], amount)
            print(result)
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Доступные валюты: USD, EUR, GBP, JPY, RUB, CNY, BTC, ETH, SOL, ADA, DOT")
            print("Используйте правильные коды валют в верхнем регистре\n")
        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
            print("Убедитесь, что у вас достаточно средств для продажи\n")
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже или проверьте подключение к сети\n")
        except Exception as e:
            print(f"Ошибка: {e}\n")
            
    def handle_get_rate(self, args):
        """Обрабатывает команду get-rate"""
        parsed, missing = self._parse_simple_args(args, ['from', 'to'])
        if missing:
            if '--from' in missing or '--to' in missing:
                print("Ошибка в команде: get-rate --from <code> --to <code>\n")
            return
        try:
            result = self.rate_manager.get_rate(parsed['from'], parsed['to'])
            print(result)
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}\n")
            print("Доступные валюты: USD, EUR, GBP, JPY, RUB, CNY, BTC, ETH, SOL, ADA, DOT\n")
            print("Используйте правильные коды валют в верхнем регистре\n")
        except ApiRequestError as e:
            print(f"Ошибка: {e}\n")
            print("Повторите попытку позже или используйте команду 'update-rates' для обновления данных\n")
        except Exception as e:
            print(f"Ошибка: {e}\n")
            
    def process_command(self, command_line: str):
        """Обрабатывает введенную команду"""
        if not command_line.strip():
            return
        args = self.parse_arguments(command_line)
        if not args:
            return
        command = args[0].lower()
        command_args = args[1:]
        if command == 'help':
            self.print_help()
        elif command == 'exit':
            self.running = False
            print("До свидания!\n")
        elif command == 'register':
            self.handle_register(command_args)
        elif command == 'login':
            self.handle_login(command_args)
        elif command == 'deposit':
            self.handle_deposit(command_args)
        elif command == 'show-portfolio':
            self.handle_show_portfolio(command_args)
        elif command == 'buy':
            self.handle_buy(command_args)
        elif command == 'sell':
            self.handle_sell(command_args)
        elif command == 'get-rate':
            self.handle_get_rate(command_args)
        else:
            print(f"Неизвестная команда: {command}. Введите 'help'.\n")

    def run(self):
        """Запускает интерактивный режим CLI"""
        self.running = True
        print("Добро пожаловать в ValutaTrade Hub!")
        print("Введите 'help' для списка команд или 'exit' для выхода.\n")
        
        while self.running:
            try:
                command_line = input("> ").strip()
                self.process_command(command_line) 
            except KeyboardInterrupt:
                print("Выход из приложения.\n")
                self.running = False
            except EOFError:
                print("Выход из приложения.\n")
                self.running = False
            except Exception as e:
                print(f"Неожиданная ошибка: {e}\n")