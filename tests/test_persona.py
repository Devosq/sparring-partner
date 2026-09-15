from pathlib import Path

import pytest

from sparring.persona import PersonaError, load_persona, personas_dir


def test_loads_persona_from_path(persona_file: Path) -> None:
    p = load_persona(str(persona_file))
    assert p.name == "tester"
    assert p.channels == ("https://www.youtube.com/@tester/videos",)
    assert p.mental_models == ("Model one",)
    assert p.subtitle_langs == ("en",)


def test_loads_persona_by_name_from_env_dir(
    persona_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPARRING_PERSONAS_DIR", str(persona_file.parent))
    assert personas_dir() == persona_file.parent
    assert load_persona("tester").display_name == "Test Creator"


def test_bundled_hormozi_persona_is_valid() -> None:
    p = load_persona("hormozi")
    assert p.display_name == "Alex Hormozi"
    assert len(p.mental_models) >= 5


def test_missing_file_raises() -> None:
    with pytest.raises(PersonaError, match="not found"):
        load_persona("nope-does-not-exist")


def test_missing_required_keys_raise(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("name: x\n", encoding="utf-8")
    with pytest.raises(PersonaError, match="missing required keys"):
        load_persona(str(path))


def test_channels_must_be_string_list(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "name: x\ndisplay_name: X\nchannels: nope\nsystem_prompt: hi\n", encoding="utf-8"
    )
    with pytest.raises(PersonaError, match="channels must be a list"):
        load_persona(str(path))


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("name: [unclosed\n", encoding="utf-8")
    with pytest.raises(PersonaError, match="invalid YAML"):
        load_persona(str(path))
