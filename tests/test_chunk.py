import pytest

from sparring.chunk import chunk_transcript, deep_link
from sparring.models import Transcript
from tests.conftest import make_transcript


def test_deep_link_appends_timestamp() -> None:
    assert (
        deep_link("https://www.youtube.com/watch?v=abc", 65.9)
        == "https://www.youtube.com/watch?v=abc&t=65"
    )
    assert deep_link("https://youtu.be/abc", 5) == "https://youtu.be/abc?t=5"


def test_chunks_cover_all_words_with_overlap() -> None:
    transcript = make_transcript(words=50)
    chunks = chunk_transcript(transcript, chunk_words=20, overlap_words=5)
    assert [c.chunk_id for c in chunks] == ["vid1:0", "vid1:1", "vid1:2"]
    assert len(chunks[0].text.split()) == 20
    # second chunk starts 15 words in (20 - 5 overlap)
    assert chunks[1].text.split()[0] == "w3_0"
    assert chunks[1].start_s == 15.0
    assert chunks[1].url.endswith("&t=15")
    # last chunk is the tail and shorter
    assert len(chunks[-1].text.split()) == 20
    assert chunks[-1].text.split()[-1] == "w9_4"


def test_single_short_transcript_is_one_chunk() -> None:
    chunks = chunk_transcript(make_transcript(words=10), chunk_words=600)
    assert len(chunks) == 1
    assert chunks[0].start_s == 0.0


def test_empty_transcript_yields_no_chunks(transcript: Transcript) -> None:
    empty = Transcript(**{**transcript.__dict__, "segments": ()})
    assert chunk_transcript(empty) == []


@pytest.mark.parametrize(("chunk_words", "overlap"), [(0, 0), (10, 10), (10, -1)])
def test_invalid_sizes_raise(chunk_words: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_transcript(make_transcript(), chunk_words=chunk_words, overlap_words=overlap)
