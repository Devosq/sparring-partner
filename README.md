# sparring-partner

Chat with a creator persona that answers in their own frameworks and cites their own
videos. The first persona is Alex Hormozi; adding another creator is one YAML file.

**How it works:** YouTube auto-subtitles (no video download, no scraping) → cleaned
transcripts → overlapping chunks → local vector index (chromadb + on-device embeddings)
→ persona system prompt + retrieved sources → any LLM through litellm.

Everything runs locally except the LLM call. Transcripts never enter git.

## Quickstart

```bash
uv sync
cp env.example .env             # add ANTHROPIC_API_KEY (or set SPARRING_MODEL to another provider)
uv run sparring ingest --persona hormozi --limit 20
uv run sparring index --persona hormozi && uv run sparring ask "How should I price a SaaS pilot?"
```

`ask` prints the answer with numbered `[n]` citations and a source list of deep links
(`youtube.com/watch?v=…&t=<seconds>`). `sparring chat` opens a multi-turn session.

## Commands

| Command | What it does |
| --- | --- |
| `sparring ingest --persona NAME --limit N` | List the persona's channel(s) and save auto-subtitles as `data/NAME/transcripts/<id>.json`. Idempotent — re-run to add more. |
| `sparring index --persona NAME` | Chunk every transcript and upsert into `data/NAME/index/` (chromadb). Idempotent. |
| `sparring ask "question"` | One question, one answer with sources. |
| `sparring chat` | Interactive session with history. Empty line exits. |
| `-v` before the command | Verbose logging. |

Environment (see `env.example`; copy it to `.env`, which is ignored by git):

| Variable | Default | Meaning |
| --- | --- | --- |
| `SPARRING_MODEL` | `anthropic/claude-sonnet-5` | Any [litellm model string](https://docs.litellm.ai/docs/providers): `openai/gpt-4o`, `groq/llama-3.3-70b-versatile`, `ollama/llama3`, … |
| `ANTHROPIC_API_KEY` etc. | — | Whatever key the chosen provider needs. Ingest and index need no key. |
| `SPARRING_DATA_DIR` | `data` | Root for transcripts and indexes. |
| `SPARRING_PERSONAS_DIR` | `personas/` | Where `<name>.yaml` files live. |

## Adding a persona

Copy `personas/hormozi.yaml`, change `name`, `display_name`, `channels`, the
`system_prompt`, `mental_models` and `style_rules`. Run `ingest` and `index` with the
new `--persona`. No code changes.

## Development

```bash
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
uv run pytest          # coverage gate: 80 %
```

Tests never touch the network or download an embedding model (a deterministic fake
embedder lives in `tests/conftest.py`). See [ARCHITECTURE.md](ARCHITECTURE.md) for the
module map and [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.

## Status and roadmap

V0 is complete and verified end-to-end on 20 videos. Open work is tracked as GitHub
issues — start with the ones labelled `good first issue`. Highlights: full-channel
ingest, podcast RSS, Whisper fallback for videos without subtitles, an eval set, and a
Telegram or web UI.

## Notes on use

This is a private study and sparring tool built on publicly available subtitles. The
persona is explicitly instructed to say it is an AI and never to claim to be the real
person. Do not publish it under a real person's name or brand.

## License

MIT — see [LICENSE](LICENSE). The transcripts you download are not part of this
repository and are not covered by this license.
