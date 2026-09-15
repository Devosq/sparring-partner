from pathlib import Path
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from sparring import chat as chat_mod
from sparring import cli
from sparring.index import VectorIndex
from sparring.ingest import save_transcript
from tests.conftest import FakeEmbedder, make_transcript

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, persona_file: Path, tmp_path: Path) -> None:
    monkeypatch.setenv("SPARRING_PERSONAS_DIR", str(persona_file.parent))
    monkeypatch.setenv("SPARRING_DATA_DIR", str(tmp_path / "data"))
    shared = VectorIndex(f"tester-{uuid4().hex[:12]}", embedding_function=FakeEmbedder())
    monkeypatch.setattr(cli, "_index", lambda data_dir, name: shared)


def test_no_args_shows_help() -> None:
    result = runner.invoke(cli.app, [])
    assert "ingest" in result.output and "ask" in result.output


def test_unknown_persona_fails_cleanly() -> None:
    result = runner.invoke(cli.app, ["index", "--persona", "ghost"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_ingest_reports_totals(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_ingest(
        channel: str, data_dir: Path, limit: int, langs: tuple[str, ...]
    ) -> dict[str, int]:
        calls.append((channel, limit))
        return {"listed": limit, "saved": limit, "skipped": 0, "no_subtitles": 0}

    monkeypatch.setattr(cli, "ingest_channel", fake_ingest)
    result = runner.invoke(cli.app, ["ingest", "--persona", "tester", "--limit", "5"])
    assert result.exit_code == 0, result.output
    assert calls == [("https://www.youtube.com/@tester/videos", 5)]
    assert "saved 5" in result.output


def test_index_requires_transcripts() -> None:
    result = runner.invoke(cli.app, ["index", "--persona", "tester"])
    assert result.exit_code == 1
    assert "no transcripts" in result.output


def test_index_then_ask_end_to_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    save_transcript(tmp_path / "data" / "tester", make_transcript(words=30))
    result = runner.invoke(cli.app, ["index", "--persona", "tester"])
    assert result.exit_code == 0, result.output
    assert "1 transcripts → 1 chunks" in result.output

    monkeypatch.setattr(chat_mod, "litellm_call", lambda messages: "grounded answer [1]")
    result = runner.invoke(cli.app, ["ask", "w0_0 w0_1", "--persona", "tester"])
    assert result.exit_code == 0, result.output
    assert "grounded answer [1]" in result.output
    assert "[1] Pricing talk — https://www.youtube.com/watch?v=vid1&t=0" in result.output


def test_ask_surfaces_llm_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(messages: list[chat_mod.Message]) -> str:
        raise chat_mod.LlmError("model call failed (x)")

    monkeypatch.setattr(chat_mod, "litellm_call", boom)
    result = runner.invoke(cli.app, ["ask", "hi", "--persona", "tester"])
    assert result.exit_code == 1
    assert "model call failed" in result.output


def test_chat_loop_runs_until_empty_line(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["first answer", "second answer"])
    monkeypatch.setattr(chat_mod, "litellm_call", lambda messages: next(answers))
    result = runner.invoke(cli.app, ["chat", "--persona", "tester"], input="one\ntwo\n\n")
    assert result.exit_code == 0, result.output
    assert "first answer" in result.output and "second answer" in result.output
