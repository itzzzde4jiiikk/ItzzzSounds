#!/usr/bin/env bash
# Wrapper to launch Yandex Music together with ItzzzSounds (Discord Synced Lyrics)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# 1. Start ItzzzSounds in background, watching yandexmusic
if [ -f "$VENV_PYTHON" ]; then
    "$VENV_PYTHON" "$SCRIPT_DIR/run.py" --no-ui --watch-process yandexmusic &
    ITZ_PID=$!
else
    "$SCRIPT_DIR/start.sh" --no-ui --watch-process yandexmusic &
    ITZ_PID=$!
fi

# Cleanup handler when this wrapper or Yandex Music terminates
cleanup() {
    if [ -n "$ITZ_PID" ] && kill -0 "$ITZ_PID" 2>/dev/null; then
        kill -TERM "$ITZ_PID" 2>/dev/null
        wait "$ITZ_PID" 2>/dev/null
    fi
}
trap cleanup EXIT INT TERM

# 2. Run Yandex Music
if [ -x "/opt/yandex-music/yandexmusic" ]; then
    /opt/yandex-music/yandexmusic --gtk-version=3 "$@"
elif command -v yandex-music &>/dev/null; then
    /usr/bin/yandex-music --gtk-version=3 "$@"
else
    echo "[!] Ошибка: Не удалось найти исполняемый файл Яндекс Музыки."
fi
