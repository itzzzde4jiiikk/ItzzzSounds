"""
Local file cache for synchronized lyrics (.lrc).
"""

import os
import re
from pathlib import Path
from typing import Optional


class LyricsCache:
    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".cache" / "ItzzzSounds" / "lyrics"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize(self, text: str) -> str:
        """Sanitize artist/title to safe filename."""
        text = text.lower().strip()
        text = re.sub(r'[\\/*?:"<>|]', "", text)
        text = re.sub(r"\s+", "_", text)
        return text[:100]

    def _get_path(self, artist: str, title: str) -> Path:
        s_artist = self._sanitize(artist) if artist else "unknown"
        s_title = self._sanitize(title) if title else "unknown"
        return self.cache_dir / f"{s_artist}_{s_title}.lrc"

    def get(self, artist: str, title: str) -> Optional[str]:
        path = self._get_path(artist, title)
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def set(self, artist: str, title: str, lrc_content: str) -> None:
        if not lrc_content or not lrc_content.strip():
            return
        path = self._get_path(artist, title)
        try:
            path.write_text(lrc_content, encoding="utf-8")
        except Exception:
            pass
