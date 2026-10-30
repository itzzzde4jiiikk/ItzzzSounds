#!/usr/bin/env bash
# ItzzzSounds launcher script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "[!] Ошибка: Python 3 не установлен в системе."
    exit 1
fi

# Create virtualenv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Создание виртуального окружения Python..."
    python3 -m venv "$VENV_DIR"
fi

# Check if dependencies installed
if [ ! -f "$VENV_DIR/.installed" ]; then
    echo "[*] Установка зависимостей..."
    "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    touch "$VENV_DIR/.installed"
fi

# Run ItzzzSounds
exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/run.py" "$@"
