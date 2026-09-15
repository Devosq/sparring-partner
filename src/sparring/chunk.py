"""Turn transcript segments into overlapping retrieval chunks.

Sizes are in words; ~600 words is roughly 800 tokens of spoken English.
"""

from __future__ import annotations

from sparring.models import Chunk, Segment, Transcript

DEFAULT_CHUNK_WORDS = 600
DEFAULT_OVERLAP_WORDS = 100


def deep_link(url: str, start_s: float) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={int(start_s)}"


def chunk_transcript(
    transcript: Transcript,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[Chunk]:
    if chunk_words <= 0 or overlap_words < 0 or overlap_words >= chunk_words:
        raise ValueError("require 0 <= overlap_words < chunk_words and chunk_words > 0")
    words = _words_with_time(transcript.segments)
    if not words:
        return []
    chunks: list[Chunk] = []
    step = chunk_words - overlap_words
    index = 0
    position = 0
    while position < len(words):
        window = words[position : position + chunk_words]
        start_s = window[0][1]
        chunks.append(
            Chunk(
                chunk_id=f"{transcript.video_id}:{index}",
                video_id=transcript.video_id,
                title=transcript.title,
                text=" ".join(w for w, _ in window),
                start_s=start_s,
                url=deep_link(transcript.url, start_s),
            )
        )
        index += 1
        if position + chunk_words >= len(words):
            break
        position += step
    return chunks


def _words_with_time(segments: tuple[Segment, ...]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for seg in segments:
        out.extend((w, seg.start_s) for w in seg.text.split())
    return out
