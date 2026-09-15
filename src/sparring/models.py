"""Plain data types shared across the pipeline. No behaviour lives here."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    """One subtitle cue after cleanup."""

    start_s: float
    end_s: float
    text: str


@dataclass(frozen=True)
class Transcript:
    video_id: str
    title: str
    url: str
    upload_date: str  # YYYYMMDD as yt-dlp reports it; "" if unknown
    duration_s: int
    segments: tuple[Segment, ...]

    def full_text(self) -> str:
        return " ".join(s.text for s in self.segments)


@dataclass(frozen=True)
class Chunk:
    """A retrieval unit: a window of transcript text with a seekable timestamp."""

    chunk_id: str
    video_id: str
    title: str
    text: str
    start_s: float
    url: str  # deep link with ?t=<start_s>


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    distance: float


@dataclass(frozen=True)
class Persona:
    name: str
    display_name: str
    channels: tuple[str, ...]
    system_prompt: str
    mental_models: tuple[str, ...] = ()
    style_rules: tuple[str, ...] = ()
    subtitle_langs: tuple[str, ...] = ("en",)


@dataclass(frozen=True)
class Answer:
    text: str
    sources: tuple[Hit, ...] = field(default_factory=tuple)
