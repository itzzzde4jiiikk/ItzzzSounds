"""
Mock player listener for demo and testing without an active music player.
"""

import time
from typing import Optional
from .base import BasePlayerListener, TrackInfo


class MockPlayerListener(BasePlayerListener):
    def __init__(self, title: str = "Кукла колдуна", artist: str = "Король и Шут", duration: float = 203.0):
        self.title = title
        self.artist = artist
        self.album = "Акустический альбом"
        self.duration = duration
        self.start_time = time.time()
        self.is_playing = True

    def poll(self) -> Optional[TrackInfo]:
        elapsed = time.time() - self.start_time
        if elapsed > self.duration:
            self.start_time = time.time()
            elapsed = 0.0

        return TrackInfo(
            title=self.title,
            artist=self.artist,
            album=self.album,
            duration=self.duration,
            position=elapsed,
            is_playing=self.is_playing,
            player_name="demo-player",
            last_updated=time.time(),
        )
