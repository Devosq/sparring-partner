from pathlib import Path

from sparring.ingest import (
    ingest_channel,
    load_all_transcripts,
    load_transcript,
    save_transcript,
    transcript_path,
)
from sparring.models import Transcript

VTT = (
    "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello there\n\n"
    "00:00:01.000 --> 00:00:02.000\ngeneral kenobi\n"
)


def _list_videos(channel_url: str, limit: int) -> list[dict[str, object]]:
    return [{"id": f"v{i}", "title": f"Video {i}", "duration": 60} for i in range(limit)]


def _fetch_ok(video_id: str, langs: tuple[str, ...], work_dir: Path) -> Path | None:
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / f"{video_id}.en.vtt"
    path.write_text(VTT, encoding="utf-8")
    return path


def test_ingest_saves_transcripts_and_is_idempotent(tmp_path: Path) -> None:
    stats = ingest_channel(
        "chan", tmp_path, limit=3, list_videos=_list_videos, fetch_subtitle=_fetch_ok
    )
    assert stats == {"listed": 3, "saved": 3, "skipped": 0, "no_subtitles": 0}
    saved = load_all_transcripts(tmp_path)
    assert [t.video_id for t in saved] == ["v0", "v1", "v2"]
    assert saved[0].title == "Video 0"
    assert saved[0].url == "https://www.youtube.com/watch?v=v0"
    assert saved[0].full_text() == "hello there general kenobi"

    again = ingest_channel(
        "chan", tmp_path, limit=3, list_videos=_list_videos, fetch_subtitle=_fetch_ok
    )
    assert again == {"listed": 3, "saved": 0, "skipped": 3, "no_subtitles": 0}


def test_ingest_counts_missing_and_empty_subtitles(tmp_path: Path) -> None:
    def fetch(video_id: str, langs: tuple[str, ...], work_dir: Path) -> Path | None:
        if video_id == "v0":
            return None
        work_dir.mkdir(parents=True, exist_ok=True)
        path = work_dir / f"{video_id}.en.vtt"
        path.write_text("WEBVTT\n\n", encoding="utf-8")
        return path

    stats = ingest_channel(
        "chan", tmp_path, limit=2, list_videos=_list_videos, fetch_subtitle=fetch
    )
    assert stats == {"listed": 2, "saved": 0, "skipped": 0, "no_subtitles": 2}
    assert load_all_transcripts(tmp_path) == []


def test_save_and_load_roundtrip(tmp_path: Path, transcript: Transcript) -> None:
    path = save_transcript(tmp_path, transcript)
    assert path == transcript_path(tmp_path, "vid1")
    assert load_transcript(path) == transcript
