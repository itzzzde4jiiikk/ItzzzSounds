"""
Configuration loader, manager, and interactive setup wizard.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


DEFAULT_CONFIG: Dict[str, Any] = {
    "mode": "rpc",  # "rpc", "status", or "both"
    "rpc": {
        "enabled": True,
        "client_id": "1217562797999784007",  # Public verified Yandex Music Application ID
        "activity_type": "listening",  # "listening" (Слушает), "playing" (Играет)
        "details_format": "🎵 {title} — {artist}",
        "state_format": "🎤 {line}",
        "pause_text": "⏸️ На паузе",
        "no_lyrics_state": "🎧 Слушает в Яндекс Музыке",
        "min_update_interval": 3.0,
        "show_buttons": True,
        "show_time_scrubber": True,
    },
    "custom_status": {
        "enabled": False,
        "token": "",
        "format": "🎶 {line}",
        "emoji": "🎵",
        "min_update_interval": 3.0,
        "clear_on_pause": True,
    },
    "yandex_music": {
        "token": "",  # Optional, for direct Yandex catalog search & sync
        "preferred_players": [
            "yandex-music",
            "firefox",
            "chromium",
            "google-chrome",
            "brave",
            "edge",
            "opera",
        ],
    },
    "ui": {
        "dashboard": True,
        "show_lyrics_preview": True,
        "preview_lines": 3,
    },
}


class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Deep merge with defaults
                    self._deep_merge(self.data, loaded)
            except Exception as e:
                print(f"[!] Warning: Could not parse {self.config_path}: {e}")
        else:
            self.save()

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        for k, v in update.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[!] Warning: Could not save config to {self.config_path}: {e}")

    @property
    def mode(self) -> str:
        return self.data.get("mode", "rpc")

    @property
    def rpc(self) -> Dict[str, Any]:
        return self.data.get("rpc", {})

    @property
    def custom_status(self) -> Dict[str, Any]:
        return self.data.get("custom_status", {})

    @property
    def yandex_music(self) -> Dict[str, Any]:
        return self.data.get("yandex_music", {})

    @property
    def ui(self) -> Dict[str, Any]:
        return self.data.get("ui", {})


def run_interactive_wizard(config_path: str = "config.json") -> Config:
    """Friendly interactive setup wizard in Russian."""
    print("=" * 60)
    print("🎵 Настройка ItzzzSounds — Yandex Music Discord Synced Lyrics")
    print("=" * 60)

    cfg = Config(config_path)

    print("\n[1] Выберите режим отображения в Discord:")
    print("  1) Discord RPC (Rich Presence) — Рекомендуется! (Безопасно, не требует токена, показывает обложку, прогресс и слова)")
    print("  2) Custom Status (Статус-сообщение рядом с ником) — Требует Discord User Token")
    print("  3) Оба режима одновременно (RPC + Custom Status)")

    choice = input("\nВаш выбор [1/2/3, по умолчанию 1]: ").strip()
    if choice == "2":
        cfg.data["mode"] = "status"
        cfg.data["rpc"]["enabled"] = False
        cfg.data["custom_status"]["enabled"] = True
    elif choice == "3":
        cfg.data["mode"] = "both"
        cfg.data["rpc"]["enabled"] = True
        cfg.data["custom_status"]["enabled"] = True
    else:
        cfg.data["mode"] = "rpc"
        cfg.data["rpc"]["enabled"] = True
        cfg.data["custom_status"]["enabled"] = False

    if cfg.data["custom_status"]["enabled"]:
        print("\nДля Custom Status требуется токен Discord пользователя:")
        print("  (Инструкция: Нажмите F12 в Discord -> вкладка Сеть (Network) -> отфильтруйте '/api' -> найдите заголовок 'Authorization')")
        token = input("Введите ваш Discord User Token: ").strip()
        if token:
            cfg.data["custom_status"]["token"] = token

    print("\n[2] Токен Яндекс Музыки (Опционально):")
    print("  Тексты большинства песен загружаются автоматически через базу LRCLIB без токена.")
    print("  Но если у вас есть OAuth токен Яндекс Музыки, программа сможет брать официальные тексты напрямую.")
    ym_token = input("Введите токен Яндекс Музыки [оставьте пустым для пропуска]: ").strip()
    if ym_token:
        cfg.data["yandex_music"]["token"] = ym_token

    cfg.save()
    print(f"\n[✓] Настройки успешно сохранены в {config_path}!")
    return cfg
