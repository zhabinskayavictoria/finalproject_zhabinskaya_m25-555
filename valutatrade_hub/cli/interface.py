import json
import os
import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import PortfolioManager, RateManager, UserManager
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


class CLIInterface:
    """Консольный интерфейс для управления валютным портфелем."""
    
    def __init__(self):
        """Инициализирует менеджеры пользователей, портфеля и курсов."""
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager(self.user_manager)
        self.rate_manager = RateManager()
        self.rates_updater = RatesUpdater()
        self.rates_storage = RatesStorage(ParserConfig())
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
        deposit --amount <sum>                       - Пополнить USD кошелек
        buy --currency <code> --amount <sum>         - Купить валюту за USD
        sell --currency <code> --amount <sum>        - Продать валюту за USD

        Курсы валют:
        get-rate --from <code> --to <code>          - Получить курс между валютами
        update-rates [--source <source>]            - Обновить курсы валют
        show-rates [--currency <code>] [--top <N>]  - Показать актуальные курсы

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
        except ValueError as e:
            print(f"Ошибка: {e}\n")
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
            print('Доступные валюты: USD, EUR, GBP, JPY, '
                'RUB, CNY, BTC, ETH, SOL, ADA, DOT')
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
            print('Доступные валюты: USD, EUR, GBP, '
                'JPY, RUB, CNY, BTC, ETH, SOL, ADA, DOT')
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
            print('Доступные валюты: USD, EUR, GBP, JPY,'
                ' RUB, CNY, BTC, ETH, SOL, ADA, DOT\n')
            print("Используйте правильные коды валют в верхнем регистре\n")
        except ApiRequestError as e:
            print(f"Ошибка: {e}\n")
            print("Повторите попытку позже или используйте команду 'update-rates'\n")
        except Exception as e:
            print(f"Ошибка: {e}\n")
            
    def handle_update_rates(self, args):
        """Обрабатывает команду update-rates"""
        parsed, _ = self._parse_simple_args(args, [])
        source = parsed.get('source')
        sources = None
        if source:
            if source.lower() in ['coingecko', 'exchangerate']:
                sources = [source.lower()]
            else:
                print(f"Ошибка: Неизвестный источник '{source}'.")
                print("Используйте 'coingecko' или 'exchangerate'\n")
                return
        try:
            print("Starting rates update...")
            stats = self.rates_updater.run_update(sources)
            if stats["sources_updated"]:
                print(f"Update successful. Total rates updated: {stats['total_rates']}")
                print(f"Last refresh: {stats.get('last_refresh', 'N/A')}")
            else:
                print("Обновление не удалось. Ни один источник не вернул данные.")
            if stats["sources_failed"]:
                print("Update completed with errors.")
                print("Check logs/parser.log for details.")
        except Exception as e:
            print(f"Ошибка при обновлении курсов: {e}\n")

    def handle_show_rates(self, args):
        """Обрабатывает команду show-rates"""
        parsed, _ = self._parse_simple_args(args, [])
        currency_filter = parsed.get('currency')
        top_count = parsed.get('top')
        
        try:
            rates_file = "data/rates.json"
            if not os.path.exists(rates_file):
                print("Локальный кеш курсов пуст.")
                print("Выполните 'update-rates', чтобы загрузить данные.\n")
                return
            with open(rates_file, 'r', encoding='utf-8') as f:
                rates_data = json.load(f)
            if not rates_data or 'pairs' not in rates_data or not rates_data['pairs']:
                print("Локальный кеш курсов пуст.")
                print("Выполните 'update-rates', чтобы загрузить данные.\n")
                return
            pairs = rates_data['pairs']
            last_refresh = rates_data.get('last_refresh', 'Неизвестно')
            
            warning_msg = ""
            if last_refresh != 'unknow':
                from valutatrade_hub.core.utils import is_rate_fresh
                from valutatrade_hub.infra.settings import SettingsLoader
                settings = SettingsLoader()
                
                if not is_rate_fresh(last_refresh):
                    ttl_minutes = settings.get("RATES_TTL_SECONDS", 300) // 60
                    warning_msg = (f"\nВНИМАНИЕ: Данные курсов устарели "
                                f"(TTL: {ttl_minutes} мин). "
                                f"Используйте 'update-rates' для обновления.")
                    
            try:
                if 'T' in last_refresh:
                    date_part, time_part = last_refresh.split('T')
                    time_part = time_part.split('.')[0]  
                    formatted_refresh = f"{date_part} {time_part}"
                else:
                    formatted_refresh = last_refresh
            except Exception:
                formatted_refresh = last_refresh
            
            table = PrettyTable()
            table.field_names = ["Valute pair", "Rate", "Source"]
            table.align["Valute pair"] = "l"
            table.align["Rate"] = "r"
            table.align["Source"] = "l"
            filtered_items = []
            for pair, data in pairs.items():
                if currency_filter:
                    currency_upper = currency_filter.upper()
                    if (pair.startswith(currency_upper + "_") or 
                        pair.endswith("_" + currency_upper)):
                        filtered_items.append((pair, data))
                else:
                    filtered_items.append((pair, data))
            
            if top_count:
                try:
                    top_n = int(top_count)
                    if top_n <= 0:
                        print("Ошибка: --top должен быть положительным числом\n")
                        return
                    filtered_items.sort(key=lambda x: x[1]['rate'], reverse=True)
                    filtered_items = filtered_items[:top_n]
                except ValueError:
                    print("Ошибка: параметр --top должен быть числом\n")
                    return
            else:
                filtered_items.sort(key=lambda x: x[0])
        
            if not filtered_items:
                if currency_filter:
                    print(f"Курс для '{currency_filter}' не найден в кеше.\n")
                else:
                    print("Нет данных о курсах для отображения.\n")
                return
            
            for pair, data in filtered_items:
                rate = data['rate']
                if rate < 0.001:
                    formatted_rate = f"{rate:.8f}"
                elif rate < 1:
                    formatted_rate = f"{rate:.6f}"
                elif rate < 1000:
                    formatted_rate = f"{rate:.4f}"
                else:
                    formatted_rate = f"{rate:,.2f}"
                
                table.add_row([
                    pair,
                    formatted_rate,
                    data.get('source', 'Unknown')
                ])
            print(f"Rates from cache (updated at {formatted_refresh}):")
            print(table)
            if warning_msg:
                print(warning_msg)
            print()  
        except Exception as e:
            print(f"Ошибка при отображении курсов: {e}\n")

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
        elif command == 'update-rates':
            self.handle_update_rates(command_args)
        elif command == 'show-rates':
            self.handle_show_rates(command_args)
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