"""Load and validate persona definitions from YAML."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from sparring.models import Persona

REQUIRED_KEYS = ("name", "display_name", "channels", "system_prompt")


class PersonaError(ValueError):
    """Raised when a persona file is missing or malformed."""


def personas_dir() -> Path:
    override = os.environ.get("SPARRING_PERSONAS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "personas"


def load_persona(name_or_path: str) -> Persona:
    path = Path(name_or_path)
    if path.suffix not in (".yaml", ".yml"):
        path = personas_dir() / f"{name_or_path}.yaml"
    if not path.is_file():
        raise PersonaError(f"persona file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PersonaError(f"invalid YAML in {path}: {exc}") from exc
    return _parse(raw, path)


def _parse(raw: object, path: Path) -> Persona:
    if not isinstance(raw, dict):
        raise PersonaError(f"{path}: top level must be a mapping")
    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise PersonaError(f"{path}: missing required keys {missing}")
    channels = _str_list(raw["channels"], "channels", path)
    if not channels:
        raise PersonaError(f"{path}: channels must contain at least one URL")
    return Persona(
        name=str(raw["name"]),
        display_name=str(raw["display_name"]),
        channels=tuple(channels),
        system_prompt=str(raw["system_prompt"]).strip(),
        mental_models=tuple(_str_list(raw.get("mental_models", []), "mental_models", path)),
        style_rules=tuple(_str_list(raw.get("style_rules", []), "style_rules", path)),
        subtitle_langs=tuple(_str_list(raw.get("subtitle_langs", ["en"]), "subtitle_langs", path)),
    )


def _str_list(value: object, key: str, path: Path) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise PersonaError(f"{path}: {key} must be a list of strings")
    return [v.strip() for v in value if v.strip()]
