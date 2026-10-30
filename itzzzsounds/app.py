"""
Main application coordinator for ItzzzSounds.
"""

import logging
import signal
import sys
import subprocess
import time
from typing import Optional

from .config import Config
from .player.base import BasePlayerListener, TrackInfo
from .player.mpris import MprisPlayerListener
from .player.mock import MockPlayerListener
from .lyrics.provider import LyricsProvider
from .lyrics.parser import LyricTrack, LyricLine
from .discord.rpc import DiscordRpcManager
from .discord.status import DiscordStatusManager
from .ui.dashboard import TerminalDashboard

logger = logging.getLogger("ItzzzSounds")


class App:
    def __init__(self, config: Config, demo_mode: bool = False, watch_process: Optional[str] = None):
        self.config = config
        self.demo_mode = demo_mode
        self.watch_process = watch_process
        self.running = False
        self._seen_watched_process = False
        self._start_time = 0.0

        # Initialize Player Listener
        if demo_mode:
            self.player: BasePlayerListener = MockPlayerListener()
        else:
            self.player = MprisPlayerListener(
                preferred_players=config.yandex_music.get("preferred_players")
            )

        # Initialize Lyrics Provider
        ym_token = config.yandex_music.get("token") or None
        self.lyrics_provider = LyricsProvider(yandex_token=ym_token)

        # Initialize Discord RPC
        rpc_cfg = config.rpc
        self.rpc = DiscordRpcManager(
            client_id=rpc_cfg.get("client_id", "1217562797999784007"),
            min_update_interval=rpc_cfg.get("min_update_interval", 3.0),
            enabled=rpc_cfg.get("enabled", True),
            activity_type=rpc_cfg.get("activity_type", "listening"),
        )

        # Initialize Discord Custom Status
        status_cfg = config.custom_status
        self.status = DiscordStatusManager(
            auth_token=status_cfg.get("token"),
            min_update_interval=status_cfg.get("min_update_interval", 3.0),
            emoji_name=status_cfg.get("emoji", "🎵"),
            enabled=status_cfg.get("enabled", False),
        )

        # Initialize UI Dashboard
        self.dashboard = TerminalDashboard()

        # State tracking
        self.current_track: Optional[TrackInfo] = None
        self.current_lyric_track: Optional[LyricTrack] = None
        self.last_lyric_line: Optional[str] = None
        self.last_poll_time = 0.0

    def start(self):
        """Main application lifecycle loop."""
        self.running = True
        self._start_time = time.time()
        self._seen_watched_process = False

        # Signal handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

        # Connect RPC if enabled
        if self.rpc.enabled:
            self.rpc.connect()

        # Start Dashboard
        if self.config.ui.get("dashboard", True):
            self.dashboard.start()

        poll_interval = 0.5  # seconds
        last_mpris_poll = 0.0
        last_watch_check = 0.0

        try:
            while self.running:
                now = time.time()

                # Process watcher: exit if watched process is closed
                if self.watch_process and (now - last_watch_check >= 1.5):
                    last_watch_check = now
                    is_running = self._is_watched_process_running()
                    if is_running:
                        self._seen_watched_process = True
                    else:
                        if self._seen_watched_process:
                            # Process was running and has now exited
                            logger.info(f"Процесс '{self.watch_process}' закрыт. Завершение работы ItzzzSounds...")
                            break
                        elif (now - self._start_time) > 20.0:
                            # Process wasn't detected within grace period
                            logger.info(f"Процесс '{self.watch_process}' не был запущен. Завершение работы...")
                            break

                # Poll MPRIS player every 1.0 - 1.5 seconds (or on startup)
                if now - last_mpris_poll >= 1.2 or self.current_track is None:
                    last_mpris_poll = now
                    polled_track = self.player.poll()
                    self._handle_polled_track(polled_track)

                # Process current playback & synchronized lyrics
                active_line = self._process_lyrics(now)

                # Flush any pending Discord updates throttled by rate limit
                self.rpc.flush_pending()
                self.status.flush_pending()

                # Update terminal UI
                if self.config.ui.get("dashboard", True):
                    self.dashboard.update(
                        track=self.current_track,
                        lyric_track=self.current_lyric_track,
                        current_line=active_line,
                        rpc_connected=self.rpc.is_connected,
                        status_enabled=self.status.enabled,
                        status_active=bool(self.status._last_text),
                    )

                time.sleep(poll_interval)
        finally:
            self.cleanup()

    def _is_watched_process_running(self) -> bool:
        if not self.watch_process:
            return False
        # If given a PID
        if self.watch_process.isdigit():
            pid = int(self.watch_process)
            try:
                import os
                os.kill(pid, 0)
                # Ensure it's not a zombie
                try:
                    with open(f"/proc/{pid}/status", "r") as f:
                        for line in f:
                            if line.startswith("State:") and "Z" in line:
                                return False
                except Exception:
                    pass
                return True
            except OSError:
                return False

        try:
            import os
            my_pid = str(os.getpid())
            # Check exact process name first (pgrep -x)
            res = subprocess.run(
                ["pgrep", "-x", self.watch_process],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if res.returncode == 0:
                pids = [p.strip() for p in res.stdout.splitlines() if p.strip() and p.strip() != my_pid]
                if pids:
                    return True

            # Fallback to pattern matching, excluding our own PID
            res2 = subprocess.run(
                ["pgrep", "-f", self.watch_process],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if res2.returncode == 0:
                pids = [p.strip() for p in res2.stdout.splitlines() if p.strip() and p.strip() != my_pid]
                if pids:
                    return True
            return False
        except Exception:
            return False

    def _handle_polled_track(self, new_track: Optional[TrackInfo]):
        """Detect track changes, seek updates, or pauses."""
        if not new_track:
            # Player closed or stopped
            if self.current_track is not None:
                self.current_track = None
                self.current_lyric_track = None
                self.last_lyric_line = None
                self.rpc.clear()
                self.status.clear()
            return

        # Check if song changed
        if not self.current_track or not new_track.is_same_track(self.current_track):
            self.current_track = new_track
            self.last_lyric_line = None
            # Fetch lyrics
            self.current_lyric_track = self.lyrics_provider.fetch_lyrics(
                title=new_track.title,
                artist=new_track.artist,
                duration=new_track.duration,
            )
            # Send immediate track update to RPC
            self._update_discord_for_track(new_track, initial=True)
        else:
            # Same track, update position & playback status
            self.current_track.position = new_track.position
            self.current_track.is_playing = new_track.is_playing
            self.current_track.last_updated = new_track.last_updated

            if not new_track.is_playing and self.config.rpc.get("pause_text"):
                # Handle pause
                pause_text = self.config.rpc.get("pause_text", "⏸️ На паузе")
                self.rpc.update_presence(
                    details=self._format_details(new_track),
                    state=pause_text,
                    small_image="pause",
                    small_text="Пауза",
                )
                if self.config.custom_status.get("clear_on_pause", True):
                    self.status.clear()

    def _process_lyrics(self, now: float) -> Optional[LyricLine]:
        """Calculates current lyric line and syncs with Discord."""
        if not self.current_track or not self.current_track.is_playing:
            return None

        if not self.current_lyric_track or not self.current_lyric_track.is_synced:
            # Fallback when no lyrics available
            if self.last_lyric_line is None:
                no_lyrics = self.config.rpc.get(
                    "no_lyrics_state", "🎧 Слушает в Яндекс Музыке"
                )
                self._update_discord_lyrics(no_lyrics, self.current_track)
                self.last_lyric_line = no_lyrics
            return None

        pos = self.current_track.current_position
        curr_line, next_line, time_until_next = self.current_lyric_track.get_current_line(pos)

        line_text = ""
        if curr_line:
            line_text = curr_line.text.strip()
        else:
            # Intro
            line_text = "🎵 (Вступление)"

        if line_text != self.last_lyric_line:
            self.last_lyric_line = line_text
            self._update_discord_lyrics(line_text, self.current_track)

        return curr_line

    def _format_details(self, track: TrackInfo) -> str:
        fmt = self.config.rpc.get("details_format", "🎵 {title} — {artist}")
        return fmt.format(title=track.title, artist=track.artist, album=track.album)

    def _format_rpc_state(self, line: str, track: TrackInfo) -> str:
        fmt = self.config.rpc.get("state_format", "🎤 {line}")
        return fmt.format(line=line, title=track.title, artist=track.artist)

    def _format_custom_status(self, line: str, track: TrackInfo) -> str:
        fmt = self.config.custom_status.get("format", "🎶 {line}")
        return fmt.format(line=line, title=track.title, artist=track.artist)

    def _update_discord_for_track(self, track: TrackInfo, initial: bool = False):
        """Update Discord when a new track begins."""
        now = time.time()
        pos = track.current_position
        dur = track.duration

        start_ts = int(now - pos) if self.config.rpc.get("show_time_scrubber", True) else None
        end_ts = int(now + (dur - pos)) if (dur > 0 and self.config.rpc.get("show_time_scrubber", True)) else None

        details = self._format_details(track)
        state = "🎶 Загрузка текста..." if initial else self._format_rpc_state("", track)

        buttons = None
        if self.config.rpc.get("show_buttons", True):
            buttons = [{"label": "Слушать в Яндекс Музыке", "url": "https://music.yandex.ru"}]

        self.rpc.update_presence(
            details=details,
            state=state,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            large_image="yandex_music",
            large_text=track.album or "Яндекс Музыка",
            small_image="play",
            small_text="Воспроизведение",
            buttons=buttons,
            force=initial,
        )

    def _update_discord_lyrics(self, line_text: str, track: TrackInfo):
        """Push lyric line to RPC and/or Custom Status."""
        now = time.time()
        pos = track.current_position
        dur = track.duration

        start_ts = int(now - pos) if self.config.rpc.get("show_time_scrubber", True) else None
        end_ts = int(now + (dur - pos)) if (dur > 0 and self.config.rpc.get("show_time_scrubber", True)) else None

        # 1. Discord RPC
        if self.rpc.enabled:
            details = self._format_details(track)
            state = self._format_rpc_state(line_text, track)
            buttons = None
            if self.config.rpc.get("show_buttons", True):
                buttons = [{"label": "Слушать в Яндекс Музыке", "url": "https://music.yandex.ru"}]

            self.rpc.update_presence(
                details=details,
                state=state,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                large_image="yandex_music",
                large_text=track.album or "Яндекс Музыка",
                small_image="play",
                small_text="Воспроизведение",
                buttons=buttons,
            )

        # 2. Discord Custom Status
        if self.status.enabled:
            status_text = self._format_custom_status(line_text, track)
            self.status.update_status(status_text)

    def _handle_exit(self, signum, frame):
        self.running = False

    def cleanup(self):
        """Clean shutdown restoring Discord status and stopping UI."""
        self.dashboard.stop()
        print("\n[ItzzzSounds] Завершение работы...")
        self.rpc.clear()
        self.rpc.close()
        self.status.clear()
        print("[ItzzzSounds] До свидания! 🎵")
