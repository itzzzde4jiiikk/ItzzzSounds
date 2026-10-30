"""
LRC (Lyric) parser and time-synchronization engine.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class LyricLine:
    timestamp: float  # seconds
    text: str


class LyricTrack:
    def __init__(self, raw_lrc: str, title: str = "", artist: str = ""):
        self.raw_lrc = raw_lrc
        self.title = title
        self.artist = artist
        self.lines: List[LyricLine] = []
        self._parse()

    def _parse(self) -> None:
        """Parse standard and enhanced LRC formats."""
        timestamp_pattern = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")
        lines_list: List[LyricLine] = []

        for line in self.raw_lrc.splitlines():
            line = line.strip()
            if not line:
                continue

            # Check for metadata tags like [ti:...], [ar:...]
            if re.match(r"^\[[a-zA-Z]+:", line):
                continue

            # Extract all timestamps in line (some LRC files have multiple timestamps for repeating choruses)
            timestamps = list(timestamp_pattern.finditer(line))
            if not timestamps:
                continue

            # The lyrics text is everything after the last timestamp
            last_match = timestamps[-1]
            text = line[last_match.end():].strip()

            # Clean word-level sync tags like <00:12.34> if present (Enhanced LRC)
            text = re.sub(r"<\d{1,2}:\d{2}(?:\.\d{1,3})?>", "", text).strip()

            for match in timestamps:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                millis_str = match.group(3)
                if millis_str:
                    # If 2 digits (e.g. .34) -> 0.34s; if 3 digits (.345) -> 0.345s
                    millis = float(f"0.{millis_str}")
                else:
                    millis = 0.0

                total_seconds = minutes * 60 + seconds + millis
                lines_list.append(LyricLine(timestamp=total_seconds, text=text))

        # Sort lines by timestamp
        lines_list.sort(key=lambda x: x.timestamp)
        self.lines = lines_list

    @property
    def is_synced(self) -> bool:
        return len(self.lines) > 0

    def get_current_line(
        self, current_time: float, pause_threshold: float = 7.0
    ) -> Tuple[Optional[LyricLine], Optional[LyricLine], float]:
        """
        Returns:
            (current_line, next_line, time_until_next)
        """
        if not self.lines:
            return None, None, 0.0

        # Before first line
        first_line = self.lines[0]
        if current_time < first_line.timestamp:
            time_until = first_line.timestamp - current_time
            return None, first_line, time_until

        # Binary search / scan for current active line
        current: Optional[LyricLine] = None
        next_line: Optional[LyricLine] = None
        idx = -1

        for i, line in enumerate(self.lines):
            if line.timestamp <= current_time:
                current = line
                idx = i
            else:
                next_line = line
                break

        time_until = (next_line.timestamp - current_time) if next_line else 999.0

        # Detect instrumental pauses between lines (after line 0)
        # E.g. if the line started seconds ago and the next line has a long gap
        if current and next_line and idx > 0:
            gap = next_line.timestamp - current.timestamp
            elapsed_since_line = current_time - current.timestamp
            if gap > pause_threshold and elapsed_since_line > 5.0:
                # We are in an instrumental gap
                pause_line = LyricLine(
                    timestamp=current.timestamp + elapsed_since_line,
                    text="🎵 (Музыкальный проигрыш) 🎸",
                )
                return pause_line, next_line, time_until

        return current, next_line, time_until

    def get_nearby_lines(
        self, current_time: float, count_before: int = 2, count_after: int = 3
    ) -> List[Tuple[int, LyricLine, bool]]:
        """
        Returns nearby lines for UI display: [(index, line, is_current), ...]
        """
        if not self.lines:
            return []

        current_idx = -1
        for i, line in enumerate(self.lines):
            if line.timestamp <= current_time:
                current_idx = i
            else:
                break

        start = max(0, current_idx - count_before)
        end = min(len(self.lines), current_idx + count_after + 1)

        result = []
        for i in range(start, end):
            is_active = (i == current_idx)
            result.append((i, self.lines[i], is_active))
        return result
