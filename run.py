#!/usr/bin/env python3
"""
ItzzzSounds — Real-time Synchronized Yandex Music Lyrics in Discord (RPC & Custom Status).
"""

import argparse
import sys
import os

# Ensure the project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from itzzzsounds.config import Config, run_interactive_wizard
from itzzzsounds.app import App


def main():
    parser = argparse.ArgumentParser(
        description="ItzzzSounds: Красивое изменение описания и статуса в Discord в такт Яндекс Музыке",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Запустить интерактивный мастер настройки (RPC, токен статуса, стиль)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запустить в демонстрационном режиме (эмуляция воспроизведения без плеера)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(BASE_DIR, "config.json"),
        help="Путь к файлу конфигурации (по умолчанию config.json)",
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Отключить терминальный интерфейс (полезно для автозагрузки в фоне)",
    )
    parser.add_argument(
        "--watch-process",
        type=str,
        default=None,
        help="Имя процесса (например yandexmusic), за которым следить. При закрытии процесса ItzzzSounds завершится автоматически.",
    )

    args = parser.parse_args()

    # If --setup requested
    if args.setup:
        run_interactive_wizard(args.config)
        return

    # Check if config exists, if not prompt setup or create defaults
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"Файл настроек {config_path} не найден. Создаём конфигурацию по умолчанию...")
        config = Config(config_path)
    else:
        config = Config(config_path)

    if args.no_ui:
        config.data["ui"]["dashboard"] = False

    app = App(config=config, demo_mode=args.demo, watch_process=args.watch_process)
    app.start()


if __name__ == "__main__":
    main()
