#!/usr/bin/env bash
# Install Yandex Music + ItzzzSounds autostart integration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$SCRIPT_DIR/yandex-music-with-presence.sh"
DESKTOP_DIR="$HOME/.local/share/applications"
BIN_DIR="$HOME/.local/bin"

chmod +x "$WRAPPER"
chmod +x "$SCRIPT_DIR/start.sh"
chmod +x "$SCRIPT_DIR/run.py"

mkdir -p "$DESKTOP_DIR" "$BIN_DIR"

# 1. Create desktop entry override
DESKTOP_FILE="$DESKTOP_DIR/yandexmusic.desktop"
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=Yandex Music
Name[ru]=Яндекс Музыка
Exec=$WRAPPER %U
Terminal=false
Type=Application
Icon=yandexmusic
StartupWMClass=YandexMusic
Comment=Personal recommendations, mixes for any occasion and the latest musical releases
MimeType=x-scheme-handler/yandexmusic;
Categories=AudioVideo;Audio;
EOF

chmod +x "$DESKTOP_FILE"

# 2. Symlink terminal commands
ln -sf "$WRAPPER" "$BIN_DIR/yandex-music"
ln -sf "$WRAPPER" "$BIN_DIR/yandexmusic"

# 3. Update desktop database if available
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo "=========================================================="
echo "✓ Интеграция автозапуска успешно установлена!"
echo "=========================================================="
echo "Теперь при запуске Яндекс Музыки (через меню или терминал):"
echo "  1) Автоматически включится ItzzzSounds (синхронизация текста в Discord)."
echo "  2) При закрытии Яндекс Музыки ItzzzSounds сам автоматически завершит работу."
echo ""
echo "Чтобы удалить интеграцию, выполните: ./uninstall_autostart.sh"
echo "=========================================================="
