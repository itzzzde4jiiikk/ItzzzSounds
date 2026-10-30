"""
Linux MPRIS player listener using playerctl and DBus fallback.
"""

import json
import logging
import subprocess
import time
from typing import List, Optional

from .base import BasePlayerListener, TrackInfo

logger = logging.getLogger(__name__)


class MprisPlayerListener(BasePlayerListener):
    def __init__(self, preferred_players: Optional[List[str]] = None):
        if preferred_players is None:
            self.preferred_players = [
                "yandex-music",
                "yandex",
                "firefox",
                "chromium",
                "google-chrome",
                "brave",
                "edge",
                "opera",
                "vivaldi",
            ]
        else:
            self.preferred_players = preferred_players

    def _get_active_players(self) -> List[str]:
        """List all available MPRIS media players."""
        try:
            res = subprocess.run(
                ["playerctl", "-l"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                lines = [p.strip() for p in res.stdout.splitlines() if p.strip()]
                # Sort players based on preference
                def sort_key(player: str) -> int:
                    p_lower = player.lower()
                    for idx, pref in enumerate(self.preferred_players):
                        if pref in p_lower:
                            return idx
                    return len(self.preferred_players)

                lines.sort(key=sort_key)
                return lines
        except Exception as e:
            logger.debug(f"Error listing players: {e}")
        return []

    def poll(self) -> Optional[TrackInfo]:
        """Poll the best active player."""
        players = self._get_active_players()
        if not players:
            return None

        # Check each player in priority order
        for player in players:
            info = self._query_player(player)
            if info and (info.is_playing or info.title):
                return info

        return None

    def _query_player(self, player_name: str) -> Optional[TrackInfo]:
        """Query metadata and position for a specific player."""
        try:
            # 1. Query status
            res_status = subprocess.run(
                ["playerctl", "-p", player_name, "status"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res_status.returncode != 0:
                return None

            status_str = res_status.stdout.strip().lower()
            if status_str not in ("playing", "paused"):
                return None

            is_playing = (status_str == "playing")

            # 2. Query title, artist, album, artUrl, length
            format_str = "{{ xesam:title }}|||{{ xesam:artist }}|||{{ xesam:album }}|||{{ mpris:artUrl }}|||{{ mpris:length }}"
            res_meta = subprocess.run(
                ["playerctl", "-p", player_name, "metadata", "--format", format_str],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res_meta.returncode != 0:
                return None

            parts = res_meta.stdout.strip().split("|||")
            if len(parts) < 5:
                return None

            title = parts[0].strip()
            artist = parts[1].strip()
            album = parts[2].strip()
            art_url = parts[3].strip()
            length_raw = parts[4].strip()

            if not title:
                return None

            # Parse length (microseconds -> seconds)
            duration = 0.0
            if length_raw.isdigit():
                duration = float(length_raw) / 1_000_000.0

            # 3. Query position
            position = 0.0
            res_pos = subprocess.run(
                ["playerctl", "-p", player_name, "position"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res_pos.returncode == 0:
                try:
                    position = float(res_pos.stdout.strip())
                except ValueError:
                    position = 0.0

            return TrackInfo(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                position=position,
                is_playing=is_playing,
                art_url=art_url,
                player_name=player_name,
                last_updated=time.time(),
            )
        except Exception as e:
            logger.debug(f"Error querying player {player_name}: {e}")
            return None
