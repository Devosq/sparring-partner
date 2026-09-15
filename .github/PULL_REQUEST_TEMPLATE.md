<!-- Keep PRs small and independently testable. -->

## What & why
<!-- One or two sentences. Link the issue. -->

## How to verify
```bash
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
uv run pytest
```
<!-- If the change touches ingest/index/chat, paste one real `sparring ask` output. -->

## Checklist
- [ ] All four checks pass locally; new behaviour has tests
- [ ] Tests still run offline (no network, no model download)
- [ ] No secrets, no `data/` files, `.env` untouched
- [ ] CHANGELOG.md updated under `[Unreleased]` if user-visible
