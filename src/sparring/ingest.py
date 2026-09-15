"""Fetch a channel's videos and their auto-subtitles with yt-dlp.

Network access is isolated behind two injectable callables so the pipeline
logic is testable without touching YouTube.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sparring.models import Segment, Transcript
from sparring.vtt import parse_vtt

log = logging.getLogger(__name__)

# Video IDs become file names; anything outside this shape is refused before it touches a path.
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

VideoMeta = dict[str, Any]
ListVideos = Callable[[str, int], list[VideoMeta]]
FetchSubtitle = Callable[[str, tuple[str, ...], Path], Path | None]


class IngestError(RuntimeError):
    """Raised when yt-dlp fails in a way we cannot recover from."""


def yt_dlp_list_videos(channel_url: str, limit: int) -> list[VideoMeta]:
    import yt_dlp

    opts = {
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlistend": limit,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise IngestError(f"failed to list videos for {channel_url}: {exc}") from exc
    entries = (info or {}).get("entries") or []
    return [e for e in entries if e and e.get("id")][:limit]


def yt_dlp_fetch_subtitle(video_id: str, langs: tuple[str, ...], work_dir: Path) -> Path | None:
    import yt_dlp

    work_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": list(langs),
        "subtitlesformat": "vtt",
        "outtmpl": str(work_dir / "%(id)s.%(ext)s"),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    except yt_dlp.utils.DownloadError as exc:
        log.warning("subtitle download failed for %s: %s", video_id, exc)
        return None
    for lang in langs:
        candidate = work_dir / f"{video_id}.{lang}.vtt"
        if candidate.is_file():
            return candidate
    matches = sorted(work_dir.glob(f"{video_id}.*.vtt"))
    return matches[0] if matches else None


def transcript_path(data_dir: Path, video_id: str) -> Path:
    return data_dir / "transcripts" / f"{video_id}.json"


def save_transcript(data_dir: Path, transcript: Transcript) -> Path:
    path = transcript_path(data_dir, transcript.video_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(transcript), ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load_transcript(path: Path) -> Transcript:
    raw = json.loads(path.read_text(encoding="utf-8"))
    segments = tuple(Segment(**s) for s in raw.pop("segments"))
    return Transcript(segments=segments, **raw)


def load_all_transcripts(data_dir: Path) -> list[Transcript]:
    folder = data_dir / "transcripts"
    if not folder.is_dir():
        return []
    return [load_transcript(p) for p in sorted(folder.glob("*.json"))]


def ingest_channel(
    channel_url: str,
    data_dir: Path,
    limit: int,
    langs: tuple[str, ...] = ("en",),
    list_videos: ListVideos = yt_dlp_list_videos,
    fetch_subtitle: FetchSubtitle = yt_dlp_fetch_subtitle,
) -> dict[str, int]:
    """Download subtitles for up to `limit` videos. Idempotent: existing JSON is skipped."""
    stats = {"listed": 0, "saved": 0, "skipped": 0, "no_subtitles": 0}
    work_dir = data_dir / "raw"
    videos = list_videos(channel_url, limit)
    stats["listed"] = len(videos)
    for meta in videos:
        video_id = str(meta["id"])
        if not _VIDEO_ID.match(video_id):
            raise IngestError(f"refusing unexpected video id {video_id!r} from {channel_url}")
        if transcript_path(data_dir, video_id).is_file():
            stats["skipped"] += 1
            continue
        vtt_path = fetch_subtitle(video_id, langs, work_dir)
        if vtt_path is None:
            stats["no_subtitles"] += 1
            continue
        segments = parse_vtt(vtt_path.read_text(encoding="utf-8"))
        if not segments:
            log.warning("empty subtitles for %s", video_id)
            stats["no_subtitles"] += 1
            continue
        transcript = Transcript(
            video_id=video_id,
            title=str(meta.get("title") or video_id),
            url=str(meta.get("url") or f"https://www.youtube.com/watch?v={video_id}"),
            upload_date=str(meta.get("upload_date") or ""),
            duration_s=int(meta.get("duration") or 0),
            segments=tuple(segments),
        )
        save_transcript(data_dir, transcript)
        stats["saved"] += 1
        log.info("saved %s (%s, %d segments)", video_id, transcript.title, len(segments))
    return stats
