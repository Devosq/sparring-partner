from pathlib import Path

from sparring.index import VectorIndex
from sparring.models import Chunk
from tests.conftest import FakeEmbedder


def _chunk(video_id: str, n: int, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"{video_id}:{n}",
        video_id=video_id,
        title=f"Video {video_id}",
        text=text,
        start_s=float(n * 10),
        url=f"https://youtu.be/{video_id}?t={n * 10}",
    )


def test_empty_index_returns_nothing(fake_index: VectorIndex) -> None:
    assert fake_index.count() == 0
    assert fake_index.query("anything") == []


def test_upsert_is_idempotent_and_query_finds_matching_text(fake_index: VectorIndex) -> None:
    chunks = [
        _chunk("a", 0, "pricing your offer value equation"),
        _chunk("b", 0, "hiring people and leadership"),
    ]
    assert fake_index.upsert(chunks) == 2
    assert fake_index.upsert(chunks) == 2
    assert fake_index.count() == 2

    hits = fake_index.query("pricing offer", k=2)
    assert hits[0].chunk.video_id == "a"
    assert hits[0].chunk.url == "https://youtu.be/a?t=0"
    assert hits[0].distance <= hits[1].distance


def test_per_video_cap_promotes_diversity(fake_index: VectorIndex) -> None:
    same = [_chunk("a", n, "pricing pricing pricing") for n in range(5)]
    other = [_chunk("b", 0, "pricing and something else")]
    fake_index.upsert(same + other)

    hits = fake_index.query("pricing", k=4, max_per_video=2)
    assert len(hits) == 3
    assert sum(1 for h in hits if h.chunk.video_id == "a") == 2
    assert any(h.chunk.video_id == "b" for h in hits)


def test_persistent_index_survives_reopen(tmp_path: Path) -> None:
    first = VectorIndex("persist", persist_dir=tmp_path / "idx", embedding_function=FakeEmbedder())
    first.upsert([_chunk("a", 0, "persist me")])
    second = VectorIndex("persist", persist_dir=tmp_path / "idx", embedding_function=FakeEmbedder())
    assert second.count() == 1


def test_batching_flushes_in_pieces(fake_index: VectorIndex, monkeypatch: object) -> None:
    import sparring.index as index_mod

    setattr(index_mod, "UPSERT_BATCH", 3)  # noqa: B010
    try:
        chunks = [_chunk("a", n, f"text {n}") for n in range(7)]
        assert fake_index.upsert(chunks) == 7
        assert fake_index.count() == 7
    finally:
        setattr(index_mod, "UPSERT_BATCH", 200)  # noqa: B010
