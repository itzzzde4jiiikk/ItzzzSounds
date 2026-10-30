"""
Terminal Dashboard UI using Rich with real-time lyric karaoke display and track progress.
"""

import math
from typing import Optional, List, Tuple
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live

from ..player.base import TrackInfo
from ..lyrics.parser import LyricLine, LyricTrack


def format_seconds(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    if seconds < 0:
        seconds = 0
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def make_progress_bar(current: float, total: float, width: int = 30) -> str:
    """Generate a text-based progress bar."""
    if total <= 0:
        return "━" * width
    ratio = min(1.0, max(0.0, current / total))
    pos = int(ratio * width)
    bar = "━" * pos + "●" + "─" * max(0, width - pos - 1)
    return bar


class TerminalDashboard:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.live: Optional[Live] = None

    def start(self):
        if not self.live:
            self.live = Live(
                self.render_empty(),
                console=self.console,
                refresh_per_second=4,
                transient=False,
            )
            self.live.start()

    def stop(self):
        if self.live:
            self.live.stop()
            self.live = None

    def render_empty(self) -> Panel:
        """Render waiting panel when no music is playing."""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold yellow", justify="right")
        table.add_column(style="white")

        table.add_row("🎵 Плеер:", "[dim]Ожидание Яндекс Музыки (запустите трек в приложении или браузере)...[/dim]")
        table.add_row("💬 Discord:", "[dim]Служба синхронизации активна[/dim]")

        header = Text.from_markup(
            "[bold cyan]🎵 ItzzzSounds[/bold cyan] [dim]—[/dim] [bold white]Синхронизация текста Яндекс Музыки в Discord[/bold white]"
        )

        return Panel(
            table,
            title=header,
            border_style="cyan",
            padding=(1, 2),
        )

    def render(
        self,
        track: Optional[TrackInfo],
        lyric_track: Optional[LyricTrack],
        current_line: Optional[LyricLine],
        rpc_connected: bool,
        status_enabled: bool,
        status_active: bool,
    ) -> Panel:
        if not track:
            return self.render_empty()

        pos = track.current_position
        dur = track.duration
        progress_bar = make_progress_bar(pos, dur, width=28)
        time_str = f"{format_seconds(pos)} / {format_seconds(dur)}"

        # Main Info Grid
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="bold cyan", justify="right")
        info_table.add_column(style="white")

        status_icon = "🟢" if track.is_playing else "⏸️"
        status_text = "Воспроизведение" if track.is_playing else "Пауза"
        info_table.add_row(f"{status_icon} Статус:", f"[bold green]{status_text}[/bold green] [dim]({track.player_name})[/dim]")
        info_table.add_row("📀 Трек:", f"[bold white]{track.title}[/bold white]")
        info_table.add_row("👤 Артист:", f"[bold yellow]{track.artist}[/bold yellow]")
        if track.album:
            info_table.add_row("💿 Альбом:", f"[dim]{track.album}[/dim]")
        info_table.add_row("⏱️ Время:", f"[bold cyan]{time_str}[/bold cyan]  {progress_bar}")

        # Discord status indicators
        rpc_badge = "[bold green]✓ Подключен[/bold green]" if rpc_connected else "[bold yellow]Ожидание...[/bold yellow]"
        status_badge = (
            "[bold green]✓ Активен[/bold green]"
            if status_active
            else ("[dim]Выключен[/dim]" if not status_enabled else "[bold yellow]Ожидание...[/bold yellow]")
        )
        info_table.add_row("💬 Discord:", f"RPC: {rpc_badge}  |  Custom Status: {status_badge}")

        # Lyrics Section
        lyrics_elements = []
        if lyric_track and lyric_track.is_synced:
            lyrics_table = Table.grid(padding=(0, 2))
            lyrics_table.add_column(style="dim", justify="right", width=10)
            lyrics_table.add_column(style="white")

            nearby = lyric_track.get_nearby_lines(pos, count_before=1, count_after=2)
            for _, line, is_active in nearby:
                ts_str = f"[{format_seconds(line.timestamp)}]"
                if is_active:
                    lyrics_table.add_row(
                        f"[bold yellow]▶ {ts_str}[/bold yellow]",
                        f"[bold yellow on #22223b] {line.text} [/bold yellow on #22223b]  [bold green]👈 Discord[/bold green]",
                    )
                else:
                    lyrics_table.add_row(f"[dim]{ts_str}[/dim]", f"[dim]{line.text}[/dim]")

            lyrics_panel = Panel(
                lyrics_table,
                title="[bold yellow]🎤 Текст в такт песни[/bold yellow]",
                border_style="yellow",
                padding=(0, 1),
            )
            lyrics_elements.append(lyrics_panel)
        elif lyric_track and not lyric_track.is_synced:
            no_sync_text = Text.from_markup("[dim yellow]⚠️ Текст песни найден, но без временной синхронизации (LRC)[/dim yellow]")
            lyrics_elements.append(no_sync_text)
        else:
            search_text = Text.from_markup("[dim]🔍 Поиск синхронизированного текста...[/dim]")
            lyrics_elements.append(search_text)

        # Footer
        footer = Text.from_markup(
            "\n[dim]Нажмите [bold red]Ctrl+C[/bold red] для выхода  |  Изменения в такт отправляются в Discord автоматически[/dim]"
        )

        content = Group(info_table, *lyrics_elements, footer)

        header = Text.from_markup(
            "[bold cyan]🎵 ItzzzSounds[/bold cyan] [dim]—[/dim] [bold white]Синхронизация текста в Discord[/bold white]"
        )

        return Panel(
            content,
            title=header,
            border_style="cyan",
            padding=(1, 2),
        )

    def update(
        self,
        track: Optional[TrackInfo],
        lyric_track: Optional[LyricTrack],
        current_line: Optional[LyricLine],
        rpc_connected: bool,
        status_enabled: bool,
        status_active: bool,
    ):
        if self.live:
            panel = self.render(
                track=track,
                lyric_track=lyric_track,
                current_line=current_line,
                rpc_connected=rpc_connected,
                status_enabled=status_enabled,
                status_active=status_active,
            )
            self.live.update(panel)
