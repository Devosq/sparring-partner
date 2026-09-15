import pytest

from sparring import chat
from sparring.index import VectorIndex
from sparring.models import Chunk, Hit, Persona


def _hit(n: int) -> Hit:
    return Hit(
        chunk=Chunk(
            chunk_id=f"v:{n}",
            video_id="v",
            title="Offer talk",
            text=f"source text {n}",
            start_s=65.0 + n,
            url=f"https://youtu.be/v?t={65 + n}",
        ),
        distance=0.1 * n,
    )


def test_system_prompt_contains_persona_parts(persona: Persona) -> None:
    prompt = chat.build_system_prompt(persona)
    assert "Test Creator" in prompt
    assert "You are a test persona." in prompt
    assert "- Model one" in prompt
    assert "- Be brief" in prompt
    assert "never claim to be" in prompt


def test_format_sources_numbers_and_timestamps() -> None:
    text = chat.format_sources([_hit(0), _hit(1)])
    assert text.startswith("SOURCES:")
    assert "[1] Offer talk @ 1:05 (https://youtu.be/v?t=65)" in text
    assert "[2] Offer talk @ 1:06" in text
    assert "source text 1" in text


def test_format_sources_empty() -> None:
    assert chat.format_sources([]) == "SOURCES: (none retrieved)"


def test_build_messages_includes_history_and_question(persona: Persona) -> None:
    history = [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "reply"}]
    messages = chat.build_messages(persona, "What now?", [_hit(0)], history)
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1]["content"].endswith("QUESTION: What now?")
    assert "[1] Offer talk" in messages[-1]["content"]


def test_ask_retrieves_then_calls_llm(persona: Persona, fake_index: VectorIndex) -> None:
    fake_index.upsert([_hit(0).chunk, _hit(1).chunk])
    seen: list[list[chat.Message]] = []

    def llm(messages: list[chat.Message]) -> str:
        seen.append(messages)
        return "answer [1]"

    answer = chat.ask("source text", persona, fake_index, llm=llm, top_k=1)
    assert answer.text == "answer [1]"
    assert len(answer.sources) == 1
    assert seen[0][0]["role"] == "system"


def test_model_name_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPARRING_MODEL", raising=False)
    assert chat.model_name() == chat.DEFAULT_MODEL
    monkeypatch.setenv("SPARRING_MODEL", "ollama/llama3")
    assert chat.model_name() == "ollama/llama3"


def test_litellm_call_wraps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    import litellm

    def boom(**kwargs: object) -> None:
        raise RuntimeError("no key")

    monkeypatch.setattr(litellm, "completion", boom)
    with pytest.raises(chat.LlmError, match="model call failed"):
        chat.litellm_call([{"role": "user", "content": "hi"}])


def test_litellm_call_rejects_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    import litellm

    class _Msg:
        content = "   "

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    monkeypatch.setattr(litellm, "completion", lambda **kwargs: _Resp())
    with pytest.raises(chat.LlmError, match="empty content"):
        chat.litellm_call([{"role": "user", "content": "hi"}])


def test_litellm_call_returns_stripped_text(monkeypatch: pytest.MonkeyPatch) -> None:
    import litellm

    class _Msg:
        content = "  hello  "

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    monkeypatch.setattr(litellm, "completion", lambda **kwargs: _Resp())
    assert chat.litellm_call([{"role": "user", "content": "hi"}]) == "hello"
