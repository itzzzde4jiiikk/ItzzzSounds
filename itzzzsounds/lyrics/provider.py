"""
Lyrics provider engine with multiple backends (LRCLIB, Yandex Music, SyncedLyrics, Local Cache).
"""

import logging
import re
import urllib.parse
from typing import Optional, Tuple
import requests

from .cache import LyricsCache
from .parser import LyricTrack

logger = logging.getLogger(__name__)


def clean_query(title: str, artist: str = "") -> Tuple[str, str]:
    """Clean track title and artist from extra tags for higher match probability."""
    # Remove 'на Яндекс Музыке' and similar suffixes (with or without dash/pipe)
    title = re.sub(r"(?:\s*[\—\-–|])?\s+на Яндекс Музыке.*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"(?:\s*[\—\-–|])?\s+Яндекс Музыка.*$", "", title, flags=re.IGNORECASE)

    # Remove (Remastered...), [Remastered...], (Official Video), [Deluxe], etc.
    title_clean = re.sub(
        r"[\(\[][^\)\]]*(?:remaster|deluxe|version|edition|bonus|official|audio|video|edit|live|mix)[^\)\]]*[\)\]]",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()

    # If title became empty, restore original
    if not title_clean:
        title_clean = title.strip()

    # Remove feat./ft. from artist for broader matching if needed
    artist_clean = re.sub(r"\s+(?:feat|ft)\.?\s+.*$", "", artist, flags=re.IGNORECASE).strip()

    return title_clean, artist_clean


class LyricsProvider:
    def __init__(self, yandex_token: Optional[str] = None, cache_dir: Optional[str] = None):
        self.yandex_token = yandex_token
        self.cache = LyricsCache(cache_dir)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ItzzzSounds-DiscordLyrics/1.0 (https://github.com)"
        })
        self._yandex_client = None
        if self.yandex_token:
            self._init_yandex_client()

    def _init_yandex_client(self):
        try:
            from yandex_music import Client
            self._yandex_client = Client(self.yandex_token).init()
            logger.info("Yandex Music client authenticated successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Yandex Music client: {e}")
            self._yandex_client = None

    def fetch_lyrics(self, title: str, artist: str = "", duration: Optional[float] = None) -> Optional[LyricTrack]:
        """
        Fetch synchronized lyrics for the track.
        Returns LyricTrack instance if found, or None.
        """
        if not title:
            return None

        # 1. Check local cache
        cached_lrc = self.cache.get(artist, title)
        if cached_lrc:
            logger.debug(f"Loaded lyrics from cache for: {artist} - {title}")
            track = LyricTrack(cached_lrc, title=title, artist=artist)
            if track.is_synced:
                return track

        clean_t, clean_a = clean_query(title, artist)

        # 2. Try LRCLIB (fastest & no token required)
        lrc = self._fetch_from_lrclib(clean_t, clean_a, duration)
        if not lrc and (clean_t != title or clean_a != artist):
            lrc = self._fetch_from_lrclib(title, artist, duration)

        # 3. Try Yandex Music API (if token available and LRCLIB didn't find it)
        if not lrc and self._yandex_client:
            lrc = self._fetch_from_yandex(clean_t, clean_a)

        # 4. Try syncedlyrics package as additional fallback
        if not lrc:
            lrc = self._fetch_from_syncedlyrics(clean_t, clean_a)

        if lrc:
            # Save to cache
            self.cache.set(artist, title, lrc)
            track = LyricTrack(lrc, title=title, artist=artist)
            return track

        return None

    def _fetch_from_lrclib(
        self, title: str, artist: str, duration: Optional[float] = None
    ) -> Optional[str]:
        """Query LRCLIB API directly."""
        # 1. Exact match /api/get
        try:
            params = {"track_name": title, "artist_name": artist}
            if duration and duration > 0:
                params["duration"] = str(int(duration))
            resp = self.session.get("https://lrclib.net/api/get", params=params, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics")
                if synced:
                    return synced
        except Exception as e:
            logger.debug(f"LRCLIB get error: {e}")

        # 2. Search query /api/search
        search_queries = []
        if artist and title:
            search_queries.append(f"{artist} {title}")
        search_queries.append(title)

        for q in search_queries:
            try:
                resp = self.session.get(
                    "https://lrclib.net/api/search", params={"q": q}, timeout=4
                )
                if resp.status_code == 200:
                    results = resp.json()
                    for item in results:
                        synced = item.get("syncedLyrics")
                        if synced:
                            return synced
            except Exception as e:
                logger.debug(f"LRCLIB search error: {e}")

        return None

    def _fetch_from_yandex(self, title: str, artist: str) -> Optional[str]:
        """Fetch lyrics from Yandex Music API via official client token."""
        if not self._yandex_client:
            return None
        try:
            query = f"{artist} {title}".strip()
            search_res = self._yandex_client.search(query, type_="track")
            if search_res and search_res.tracks and search_res.tracks.results:
                y_track = search_res.tracks.results[0]
                lyrics_info = self._yandex_client.tracks_lyrics(y_track.id)
                if lyrics_info:
                    raw_text = lyrics_info.fetch_lyrics()
                    if raw_text and ("[" in raw_text and ":" in raw_text):
                        return raw_text
        except Exception as e:
            logger.debug(f"Yandex Music API error: {e}")
        return None

    def _fetch_from_syncedlyrics(self, title: str, artist: str) -> Optional[str]:
        """Fallback to syncedlyrics module."""
        try:
            import syncedlyrics
            query = f"{artist} {title}".strip()
            # Only use reliable providers
            lrc = syncedlyrics.search(query, providers=["Lrclib"])
            if lrc:
                return lrc
        except Exception as e:
            logger.debug(f"syncedlyrics error: {e}")
        return None
