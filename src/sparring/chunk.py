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
    min_tail = chunk_words // 2
    position = 0
    while True:
        end = position + chunk_words
        next_start = position + step
        # Fold a short tail into this window instead of emitting a near-empty chunk.
        is_last = end >= len(words) or len(words) - next_start < min_tail
        window = words[position:] if is_last else words[position:end]
        start_s = window[0][1]
        chunks.append(
            Chunk(
                chunk_id=f"{transcript.video_id}:{len(chunks)}",
                video_id=transcript.video_id,
                title=transcript.title,
                text=" ".join(w for w, _ in window),
                start_s=start_s,
                url=deep_link(transcript.url, start_s),
            )
        )
        if is_last:
            return chunks
        position = next_start


def _words_with_time(segments: tuple[Segment, ...]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for seg in segments:
        out.extend((w, seg.start_s) for w in seg.text.split())
    return out
