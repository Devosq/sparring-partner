"""Compose the persona prompt with retrieved sources and call the LLM.

The LLM call is a plain callable (messages -> text) so tests inject a stub and
the default goes through litellm, which supports Anthropic, OpenAI, Groq,
Ollama and more via the model string.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from sparring.index import VectorIndex
from sparring.models import Answer, Hit, Persona

Message = dict[str, str]
LlmCall = Callable[[list[Message]], str]

DEFAULT_MODEL = "anthropic/claude-sonnet-5"
DEFAULT_TOP_K = 8
MAX_TOKENS = 3000

GROUNDING_RULES = (
    "You are a sparring partner speaking in the voice and frameworks of {display_name}. "
    "You are not the real person and never claim to be; if asked, say you are an AI trained on "
    "their public talks.\n"
    "Ground every substantive claim in the numbered SOURCES below and cite them inline as [n]. "
    "If the sources do not cover the question, say so in one sentence, then reason from the "
    "frameworks listed here without inventing quotes.\n"
    "Answer in the same language the user writes in."
)


class LlmError(RuntimeError):
    """Raised when the model call fails."""


def model_name() -> str:
    return os.environ.get("SPARRING_MODEL", DEFAULT_MODEL)


def litellm_call(messages: list[Message]) -> str:
    import litellm

    try:
        response = litellm.completion(model=model_name(), messages=messages, max_tokens=MAX_TOKENS)
    except Exception as exc:  # litellm raises provider-specific subclasses
        raise LlmError(f"model call failed ({model_name()}): {exc}") from exc
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise LlmError(f"model returned empty content ({model_name()})")
    return content.strip()


def build_system_prompt(persona: Persona) -> str:
    parts = [GROUNDING_RULES.format(display_name=persona.display_name), persona.system_prompt]
    if persona.mental_models:
        parts.append("MENTAL MODELS:\n" + "\n".join(f"- {m}" for m in persona.mental_models))
    if persona.style_rules:
        parts.append("STYLE:\n" + "\n".join(f"- {r}" for r in persona.style_rules))
    return "\n\n".join(parts)


def format_sources(hits: list[Hit]) -> str:
    if not hits:
        return "SOURCES: (none retrieved)"
    lines = ["SOURCES:"]
    for n, hit in enumerate(hits, start=1):
        minutes, seconds = divmod(int(hit.chunk.start_s), 60)
        lines.append(f"[{n}] {hit.chunk.title} @ {minutes}:{seconds:02d} ({hit.chunk.url})")
        lines.append(hit.chunk.text)
        lines.append("")
    return "\n".join(lines).rstrip()


def build_messages(
    persona: Persona,
    question: str,
    hits: list[Hit],
    history: list[Message] | None = None,
) -> list[Message]:
    messages: list[Message] = [{"role": "system", "content": build_system_prompt(persona)}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": f"{format_sources(hits)}\n\nQUESTION: {question}"})
    return messages


def ask(
    question: str,
    persona: Persona,
    index: VectorIndex,
    llm: LlmCall | None = None,
    history: list[Message] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> Answer:
    call = llm if llm is not None else litellm_call
    hits = index.query(question, k=top_k)
    text = call(build_messages(persona, question, hits, history))
    return Answer(text=text, sources=tuple(hits))
