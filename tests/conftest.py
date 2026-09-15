from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from sparring.index import VectorIndex
from sparring.models import Persona, Segment, Transcript

DIM = 64


class FakeEmbedder(EmbeddingFunction[Documents]):
    """Deterministic bag-of-words hashing embedder; no model download, no network."""

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002 - chroma's signature
        out: Embeddings = []
        for doc in input:
            vec = np.zeros(DIM, dtype=np.float32)
            for word in doc.lower().split():
                slot = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM
                vec[slot] += 1.0
            norm = np.float32(np.linalg.norm(vec)) or np.float32(1.0)
            out.append((vec / norm).astype(np.float32))
        return out

    @staticmethod
    def name() -> str:
        return "fake"

    def get_config(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> FakeEmbedder:
        return FakeEmbedder()


@pytest.fixture
def fake_index() -> VectorIndex:
    # EphemeralClient state is process-wide, so every test gets its own collection.
    return VectorIndex(
        collection_name=f"test-{uuid4().hex[:12]}", embedding_function=FakeEmbedder()
    )


@pytest.fixture
def persona() -> Persona:
    return Persona(
        name="tester",
        display_name="Test Creator",
        channels=("https://www.youtube.com/@tester/videos",),
        system_prompt="You are a test persona.",
        mental_models=("Model one",),
        style_rules=("Be brief",),
    )


def make_transcript(
    video_id: str = "vid1", words: int = 50, title: str = "Pricing talk"
) -> Transcript:
    segments = tuple(
        Segment(
            start_s=float(i * 5),
            end_s=float(i * 5 + 4),
            text=" ".join(f"w{i}_{j}" for j in range(5)),
        )
        for i in range(words // 5)
    )
    return Transcript(
        video_id=video_id,
        title=title,
        url=f"https://www.youtube.com/watch?v={video_id}",
        upload_date="20260101",
        duration_s=words,
        segments=segments,
    )


@pytest.fixture
def transcript() -> Transcript:
    return make_transcript()


@pytest.fixture
def persona_file(tmp_path: Path) -> Path:
    path = tmp_path / "tester.yaml"
    path.write_text(
        "name: tester\n"
        "display_name: Test Creator\n"
        "channels:\n  - https://www.youtube.com/@tester/videos\n"
        "system_prompt: |\n  You are a test persona.\n"
        "mental_models: [Model one]\n"
        "style_rules: [Be brief]\n",
        encoding="utf-8",
    )
    return path
