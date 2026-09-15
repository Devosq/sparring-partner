"""Command-line entry point: ingest -> index -> ask / chat."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from dotenv import load_dotenv

from sparring import chat as chat_mod
from sparring.chunk import chunk_transcript
from sparring.index import IndexCorruptError, VectorIndex
from sparring.ingest import IngestError, ingest_channel, load_all_transcripts
from sparring.models import Answer
from sparring.persona import PersonaError, load_persona

MAX_HISTORY_MESSAGES = 20  # 10 turns

app = typer.Typer(
    help="Spar with a creator persona grounded in their own transcripts.",
    no_args_is_help=True,
)

PersonaOpt = Annotated[
    str, typer.Option("--persona", "-p", help="Persona name (personas/<name>.yaml) or a path.")
]
DataDirOpt = Annotated[
    Path | None, typer.Option("--data-dir", help="Root for transcripts and the index.")
]


def _data_dir(value: Path | None) -> Path:
    return value if value is not None else Path(os.environ.get("SPARRING_DATA_DIR", "data"))


def _persona_dir(data_dir: Path, persona_name: str) -> Path:
    return data_dir / persona_name


def _index(data_dir: Path, persona_name: str) -> VectorIndex:
    return VectorIndex(
        collection_name=persona_name,
        persist_dir=_persona_dir(data_dir, persona_name) / "index",
    )


def _fail(message: str) -> NoReturn:
    typer.secho(message, err=True, fg=typer.colors.RED)
    raise typer.Exit(code=1)


def _trim_history(history: list[chat_mod.Message]) -> list[chat_mod.Message]:
    """Keep the prompt bounded: only the most recent turns go to the model."""
    return history[-MAX_HISTORY_MESSAGES:]


def _force_utf8_console() -> None:
    # Windows consoles default to a legacy code page and crash on "→" or "ä".
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


@app.callback()
def _setup(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    _force_utf8_console()
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command()
def ingest(
    persona: PersonaOpt = "hormozi",
    limit: Annotated[int, typer.Option(help="Max videos per channel.")] = 20,
    data_dir: DataDirOpt = None,
) -> None:
    """Download auto-subtitles for the persona's channels into data/<persona>/transcripts."""
    try:
        p = load_persona(persona)
    except PersonaError as exc:
        _fail(str(exc))
    target = _persona_dir(_data_dir(data_dir), p.name)
    totals = {"listed": 0, "saved": 0, "skipped": 0, "no_subtitles": 0}
    for channel in p.channels:
        typer.echo(f"ingesting {channel} (limit {limit})")
        try:
            stats = ingest_channel(channel, target, limit=limit, langs=p.subtitle_langs)
        except IngestError as exc:
            _fail(str(exc))
        totals = {key: totals[key] + stats[key] for key in totals}
    typer.echo(
        f"listed {totals['listed']} · saved {totals['saved']} · skipped {totals['skipped']} "
        f"· no subtitles {totals['no_subtitles']}"
    )


@app.command()
def index(persona: PersonaOpt = "hormozi", data_dir: DataDirOpt = None) -> None:
    """Chunk all saved transcripts and upsert them into the local vector index."""
    try:
        p = load_persona(persona)
    except PersonaError as exc:
        _fail(str(exc))
    root = _data_dir(data_dir)
    transcripts = load_all_transcripts(_persona_dir(root, p.name))
    if not transcripts:
        _fail("no transcripts found — run `sparring ingest` first")
    chunks = [c for t in transcripts for c in chunk_transcript(t)]
    vector_index = _index(root, p.name)
    vector_index.delete_videos(t.video_id for t in transcripts)
    upserted = vector_index.upsert(chunks)
    typer.echo(
        f"{len(transcripts)} transcripts → {upserted} chunks · "
        f"index now holds {vector_index.count()}"
    )


def _print_answer(answer: Answer) -> None:
    typer.echo(answer.text)
    if answer.sources:
        typer.echo("\nSources:")
        for n, hit in enumerate(answer.sources, start=1):
            typer.echo(f"  [{n}] {hit.chunk.title} — {hit.chunk.url}")


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="One question; prints the answer with sources.")],
    persona: PersonaOpt = "hormozi",
    data_dir: DataDirOpt = None,
) -> None:
    """Ask one question and exit."""
    try:
        p = load_persona(persona)
        answer = chat_mod.ask(question, p, _index(_data_dir(data_dir), p.name))
    except (PersonaError, chat_mod.LlmError, IndexCorruptError) as exc:
        _fail(str(exc))
    _print_answer(answer)


@app.command()
def chat(persona: PersonaOpt = "hormozi", data_dir: DataDirOpt = None) -> None:
    """Interactive multi-turn session. Ctrl-C or an empty line exits."""
    try:
        p = load_persona(persona)
    except PersonaError as exc:
        _fail(str(exc))
    vector_index = _index(_data_dir(data_dir), p.name)
    history: list[chat_mod.Message] = []
    typer.echo(
        f"Sparring with {p.display_name} (model {chat_mod.model_name()}). Empty line to quit."
    )
    while True:
        try:
            question = typer.prompt("you", default="", show_default=False).strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not question:
            break
        try:
            answer = chat_mod.ask(question, p, vector_index, history=history)
        except IndexCorruptError as exc:
            _fail(str(exc))
        except chat_mod.LlmError as exc:
            typer.secho(str(exc), err=True, fg=typer.colors.RED)
            continue
        _print_answer(answer)
        history = _trim_history(
            [
                *history,
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer.text},
            ]
        )


def main() -> None:
    app()
