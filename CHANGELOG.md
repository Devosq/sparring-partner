# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-09-15

V0: a working end-to-end pipeline for one persona, handed over for further development.

### Added

- `sparring ingest` — lists a persona's YouTube channel(s) with yt-dlp and saves
  auto-subtitles as transcript JSON. Idempotent per video.
- `sparring index` — chunks transcripts (600 words, 100 overlap, timestamped) into a
  local chromadb collection with on-device embeddings.
- `sparring ask` / `sparring chat` — retrieval-grounded answers in the persona's voice
  with numbered citations and deep links to the exact timestamp. Any LLM via litellm.
- `personas/hormozi.yaml` — Alex Hormozi persona: system prompt, 12 mental models,
  style rules.
- Test suite (50 tests, ~91 % coverage) that runs offline with a fake embedder.
- CI (ruff, ruff format, mypy --strict, pytest with 80 % coverage gate).

### Verified

- Real run on 2026-09-15: see the PR description for the ingest/index/ask output.
- Two independent code reviews (general + Python) before merge; all MEDIUM findings fixed:
  HTML entities decoded in subtitles, short tail chunks folded into the previous chunk,
  typed `IndexCorruptError` surfaced by the CLI, video-id shape validated before it
  becomes a file name, chat history capped at 10 turns.
