#!/usr/bin/env bash
# Remove Yandex Music + ItzzzSounds autostart integration

DESKTOP_FILE="$HOME/.local/share/applications/yandexmusic.desktop"
BIN_FILE1="$HOME/.local/bin/yandex-music"
BIN_FILE2="$HOME/.local/bin/yandexmusic"

if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo "✓ Удалён $DESKTOP_FILE"
fi

if [ -L "$BIN_FILE1" ] || [ -f "$BIN_FILE1" ]; then
    rm -f "$BIN_FILE1"
    echo "✓ Удалён $BIN_FILE1"
fi

if [ -L "$BIN_FILE2" ] || [ -f "$BIN_FILE2" ]; then
    rm -f "$BIN_FILE2"
    echo "✓ Удалён $BIN_FILE2"
fi

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "=========================================================="
echo "✓ Интеграция удалена. Яндекс Музыка возвращена к стандартному запуску."
echo "=========================================================="
