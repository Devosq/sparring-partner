# Architecture

One linear pipeline, one module per stage, every external dependency behind an
injectable callable so the core is unit-testable offline.

```
personas/<name>.yaml ──► persona.py ──► Persona
                                          │
YouTube ──► ingest.py ──► data/<name>/transcripts/<video_id>.json
             │  (yt-dlp: list channel, fetch auto-sub VTT)
             └─ vtt.py  (VTT → Segment[], de-duplicated rolling captions)
                                          │
                          chunk.py  (Segment[] → Chunk[], ~600 words, 100 overlap, deep link)
                                          │
                          index.py  (Chunk[] → chromadb collection in data/<name>/index/)
                                          │
question ──► chat.py  (retrieve top-k, cap per video, build prompt, call LLM) ──► Answer
                                          │
                          cli.py    (typer: ingest | index | ask | chat)
```

## Modules

| Module | Responsibility | External dependency | Injection point |
| --- | --- | --- | --- |
| `models.py` | Frozen dataclasses: `Segment`, `Transcript`, `Chunk`, `Hit`, `Persona`, `Answer`. | — | — |
| `persona.py` | Load + validate YAML into `Persona`. Raises `PersonaError`. | PyYAML | `SPARRING_PERSONAS_DIR` |
| `vtt.py` | Parse WebVTT, strip `<c>`/timing tags, drop repeated rolling lines. | — | — |
| `ingest.py` | List channel videos, fetch subtitles, save/load transcript JSON. Idempotent per video. | yt-dlp | `list_videos`, `fetch_subtitle` callables |
| `chunk.py` | Word-window chunking with overlap; keeps first-word timestamp; builds `?t=` deep link. | — | sizes |
| `index.py` | `VectorIndex`: upsert in batches, cosine query, per-video cap for diversity. | chromadb (+ its default ONNX MiniLM embedder) | `embedding_function`, `persist_dir=None` → in-memory |
| `chat.py` | System prompt = grounding rules + persona prompt + mental models + style. User turn = numbered SOURCES + QUESTION. | litellm | `llm` callable, `SPARRING_MODEL` |
| `cli.py` | Wiring and user-facing errors only. No business logic. | typer, python-dotenv | — |

## Key decisions

- **Subtitles, not audio.** YouTube auto-subs are good enough for retrieval and cost
  nothing. Whisper is a fallback for the minority of videos without them (open issue).
- **Local embeddings.** chromadb's bundled MiniLM (ONNX, ~80 MB, CPU) means ingest and
  index need no API key. Swap `embedding_function` in `VectorIndex` for a hosted model if
  quality demands it.
- **Persona as data.** Everything creator-specific is YAML. The grounding rules in
  `chat.GROUNDING_RULES` are the only prompt text in code and apply to every persona.
- **Citations are structural.** Every chunk carries a deep link; the prompt numbers
  sources and asks for `[n]` citations; the CLI prints the list. Hallucinated quotes are
  discouraged by instruction and checkable by link.
- **Diversity by cap, not MMR.** `max_per_video=2` keeps one long video from filling the
  context. Real MMR/re-ranking is an open issue if retrieval quality becomes the limit.
- **Immutable data.** All models are frozen dataclasses; stages return new values.

## Data layout

```
data/
  <persona>/
    raw/               yt-dlp scratch (VTT files)          gitignored
    transcripts/       <video_id>.json                     gitignored
    index/             chromadb persistent collection      gitignored
```

## Testing strategy

- `tests/conftest.py` provides `FakeEmbedder` (hashed bag-of-words) and an ephemeral
  `VectorIndex`, so index and chat tests run in milliseconds without downloads.
- Ingest tests inject fake `list_videos` / `fetch_subtitle`; the yt-dlp wrappers
  themselves are thin and verified by the manual end-to-end run documented in
  CHANGELOG.
- CLI tests use typer's `CliRunner` with the persona dir and data dir pointed at
  `tmp_path`.
