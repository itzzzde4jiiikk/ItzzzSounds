"""
Abstract player listener and data structures.
"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class TrackInfo:
    title: str
    artist: str
    album: str = ""
    duration: float = 0.0  # seconds
    position: float = 0.0  # seconds at query time
    is_playing: bool = False
    art_url: str = ""
    player_name: str = ""
    last_updated: float = 0.0  # epoch time

    @property
    def current_position(self) -> float:
        """Interpolated playback position based on elapsed time."""
        if not self.is_playing:
            return self.position
        elapsed = time.time() - self.last_updated
        pos = self.position + elapsed
        if self.duration > 0 and pos > self.duration:
            return self.duration
        return pos

    def is_same_track(self, other: Optional["TrackInfo"]) -> bool:
        if not other:
            return False
        return (
            self.title.strip().lower() == other.title.strip().lower()
            and self.artist.strip().lower() == other.artist.strip().lower()
        )


class BasePlayerListener:
    def poll(self) -> Optional[TrackInfo]:
        """Poll the active media player and return TrackInfo if playing/paused."""
        raise NotImplementedError
