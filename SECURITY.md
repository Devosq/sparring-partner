# Security

## Reporting

Do not open a public issue for a vulnerability. Email the repository owner (see the
GitHub profile of the `CODEOWNERS` entry) with a description and reproduction. You will
get an acknowledgement within 3 working days.

## Threat model

This tool runs locally and calls one external LLM API. The surfaces that matter:

| Surface | Risk | Control |
| --- | --- | --- |
| LLM API keys | Leak via git or logs | Keys live only in `.env` (gitignored) or the shell; `env.example` holds placeholders; nothing logs request bodies or keys. |
| Persona YAML | Prompt injection through a malicious persona file | Only load persona files you wrote. `yaml.safe_load` is used; no code execution from YAML. |
| Transcripts | Prompt injection through subtitle text | Retrieved text is placed in the user turn under a `SOURCES:` header and the system prompt instructs the model to treat it as quoted material. Treat answers as advice, not commands. |
| yt-dlp | Executes against arbitrary URLs from persona `channels` | Channel URLs come from your own YAML. `skip_download` is set; only subtitle files are written, under `data/<persona>/raw/`. |
| chromadb | Local file store | No network listener is started (`PersistentClient` / `EphemeralClient` only). |

## Secrets checklist before pushing

- `git diff --cached | grep -iE "sk-|api[_-]?key|token"` returns nothing.
- `.env` is untracked (`git status --ignored` shows it under ignored).
- No transcript JSON or index files are staged (`data/` is gitignored).

## Dependencies

`uv.lock` pins every version. Update deliberately with `uv lock --upgrade-package
<name>` and run the full test suite. Review yt-dlp and litellm release notes on upgrade;
both talk to external services.
