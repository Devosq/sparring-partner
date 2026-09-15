from sparring.vtt import clean_line, parse_timestamp, parse_vtt

YOUTUBE_AUTO_SUB = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.500 align:start position:0%

the<00:00:00.500><c> value</c><00:00:00.900><c> equation</c>

00:00:02.500 --> 00:00:02.510 align:start position:0%
the value equation


00:00:02.510 --> 00:00:05.000 align:start position:0%
the value equation
is<00:00:03.000><c> everything</c>

00:00:05.000 --> 00:00:07.000 align:start position:0%
is everything
&nbsp;
"""


def test_parse_timestamp_handles_both_forms() -> None:
    assert parse_timestamp("00:01:02.500") == 62.5
    assert parse_timestamp("01:02.500") == 62.5


def test_clean_line_strips_inline_tags_and_whitespace() -> None:
    assert clean_line("the<00:00:00.500><c> value</c>  equation") == "the value equation"


def test_parse_vtt_dedupes_rolling_captions() -> None:
    segments = parse_vtt(YOUTUBE_AUTO_SUB)
    texts = [s.text for s in segments]
    assert texts == ["the value equation", "is everything"]
    assert segments[0].start_s == 0.0
    assert segments[1].start_s == 2.51


def test_parse_vtt_ignores_header_and_empty_input() -> None:
    assert parse_vtt("WEBVTT\n\n") == []
    assert parse_vtt("") == []


def test_parse_vtt_without_trailing_blank_line() -> None:
    content = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello world"
    segments = parse_vtt(content)
    assert len(segments) == 1
    assert segments[0].text == "hello world"
    assert segments[0].end_s == 2.0
