#!/usr/bin/env python3

from valutatrade_hub.cli.interface import CLIInterface


def main():
    """Главная функция приложения"""
    cli = CLIInterface()
    cli.run()

if __name__ == "__main__":
    main()