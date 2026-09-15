"""Parse YouTube WebVTT auto-subtitles into clean, de-duplicated segments.

YouTube auto-subs repeat each line across consecutive cues (rolling caption
effect) and embed inline timing tags like <00:00:01.234><c>word</c>. We strip
the tags and drop a cue's line when it merely repeats the previous emitted line.
"""

from __future__ import annotations

import html
import re

from sparring.models import Segment

_TIMING = re.compile(
    r"^(?P<start>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def parse_timestamp(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 2:
        parts = ["0", *parts]
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def clean_line(line: str) -> str:
    # Entities first (so &nbsp; becomes whitespace), whitespace collapse last.
    return _WS.sub(" ", html.unescape(_TAG.sub("", line))).strip()


def parse_vtt(content: str) -> list[Segment]:
    segments: list[Segment] = []
    last_text = ""
    start = end = 0.0
    lines: list[str] = []
    in_cue = False

    def flush() -> None:
        nonlocal last_text, lines
        text = " ".join(lines).strip()
        lines = []
        if not text or text == last_text:
            return
        segments.append(Segment(start_s=start, end_s=end, text=text))
        last_text = text

    # Cues are delimited by timing lines, not blank lines: YouTube emits a
    # whitespace-only line between the timing and the text of every cue.
    for raw in content.splitlines():
        match = _TIMING.match(raw.strip())
        if match:
            if in_cue:
                flush()
            start = parse_timestamp(match.group("start"))
            end = parse_timestamp(match.group("end"))
            in_cue = True
            continue
        if not in_cue:
            continue
        cleaned = clean_line(raw)
        if cleaned and cleaned != last_text and cleaned not in lines:
            lines.append(cleaned)
    if in_cue:
        flush()
    return segments
