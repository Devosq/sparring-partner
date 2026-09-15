# Contributing

## Setup

```bash
uv sync
cp env.example .env
uv run pytest
```

Python 3.12+, [uv](https://docs.astral.sh/uv/). No other tooling required.

## Workflow

1. Pick an issue (or open one). Issues labelled `good first issue` are scoped and
   self-contained.
2. Branch from `main`: `feat/<short-name>`, `fix/<short-name>`.
3. Keep PRs small and independently testable. One stage of the pipeline per PR is a
   good size.
4. Before pushing, all four must pass:

   ```bash
   uv run ruff check src tests
   uv run ruff format --check src tests
   uv run mypy
   uv run pytest
   ```

5. Open a PR against `main` using the template. CI runs the same four checks.

## Code rules

- Type annotations on every signature; `mypy --strict` is the gate. No `Any` in new
  code unless a third-party type forces it — then annotate the boundary.
- Frozen dataclasses for data; return new values instead of mutating.
- Network and model calls stay behind injectable callables (see `ingest.py`, `chat.py`,
  `index.py`). Tests must run offline and without downloading models.
- Handle errors at the boundary with a typed exception (`PersonaError`, `IngestError`,
  `LlmError`); the CLI turns them into a red one-liner and exit code 1. Never swallow.
- `logging`, not `print`, outside `cli.py`.
- Files stay under ~300 lines; split by responsibility, not by type.
- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`), English.

## Adding a persona

Copy `personas/hormozi.yaml`; the loader validates `name`, `display_name`, `channels`
and `system_prompt`. Add a test in `tests/test_persona.py` asserting the file loads.

## Adding a data source

Implement a new pair of `list_videos` / `fetch_subtitle` callables (or a new loader
that yields `Transcript` objects) and wire it in `cli.py`. Keep the `Transcript` shape
so chunking and indexing stay untouched.
