"""Vector index over transcript chunks, backed by a local chromadb file.

The embedding function is injectable so tests run with a deterministic fake
and no model download.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

import chromadb
from chromadb.api.types import EmbeddingFunction, Where

from sparring.models import Chunk, Hit

log = logging.getLogger(__name__)

DEFAULT_MAX_HITS_PER_VIDEO = 2
DEFAULT_UPSERT_BATCH = 200


class IndexCorruptError(RuntimeError):
    """Raised when stored chunk metadata does not have the expected shape."""


class VectorIndex:
    def __init__(
        self,
        collection_name: str,
        persist_dir: Path | None = None,
        embedding_function: EmbeddingFunction[Any] | None = None,
        upsert_batch: int = DEFAULT_UPSERT_BATCH,
    ) -> None:
        self._upsert_batch = upsert_batch
        self._client = (
            chromadb.PersistentClient(path=str(persist_dir))
            if persist_dir is not None
            else chromadb.EphemeralClient()
        )
        kwargs: dict[str, Any] = {"metadata": {"hnsw:space": "cosine"}}
        if embedding_function is not None:
            kwargs["embedding_function"] = embedding_function
        self._collection = self._client.get_or_create_collection(collection_name, **kwargs)

    def count(self) -> int:
        return self._collection.count()

    def delete_videos(self, video_ids: Iterable[str]) -> None:
        """Drop every chunk of the given videos so a re-index never leaves stale ids behind."""
        ids: list[str | int | float | bool] = sorted(set(video_ids))
        if ids and self.count() > 0:
            in_clause: dict[Literal["$in", "$nin"], list[str | int | float | bool]] = {"$in": ids}
            where: Where = {"video_id": in_clause}
            self._collection.delete(where=where)

    def upsert(self, chunks: Iterable[Chunk]) -> int:
        batch: list[Chunk] = []
        total = 0
        for chunk in chunks:
            batch.append(chunk)
            if len(batch) >= self._upsert_batch:
                total += self._flush(batch)
                batch = []
        if batch:
            total += self._flush(batch)
        return total

    def _flush(self, batch: list[Chunk]) -> int:
        self._collection.upsert(
            ids=[c.chunk_id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[
                {"video_id": c.video_id, "title": c.title, "start_s": c.start_s, "url": c.url}
                for c in batch
            ],
        )
        log.info("upserted %d chunks", len(batch))
        return len(batch)

    def query(
        self,
        text: str,
        k: int = 8,
        max_per_video: int = DEFAULT_MAX_HITS_PER_VIDEO,
    ) -> list[Hit]:
        """Return up to k hits, capping hits per video so one long video cannot crowd out others."""
        total = self.count()
        if total == 0:
            return []
        fetch = min(k * 4, total)
        result = self._collection.query(
            query_texts=[text],
            n_results=fetch,
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        hits: list[Hit] = []
        per_video: dict[str, int] = {}
        for chunk_id, doc, meta, dist in zip(ids, documents, metadatas, distances, strict=True):
            start_s = meta.get("start_s")
            video_id = meta.get("video_id")
            if not isinstance(start_s, int | float) or not isinstance(video_id, str):
                raise IndexCorruptError(
                    f"corrupt metadata for {chunk_id}: {meta!r} — rebuild with `sparring index`"
                )
            if per_video.get(video_id, 0) >= max_per_video:
                continue
            per_video[video_id] = per_video.get(video_id, 0) + 1
            hits.append(
                Hit(
                    chunk=Chunk(
                        chunk_id=chunk_id,
                        video_id=video_id,
                        title=str(meta.get("title", "")),
                        text=doc,
                        start_s=float(start_s),
                        url=str(meta.get("url", "")),
                    ),
                    distance=float(dist),
                )
            )
            if len(hits) >= k:
                break
        return hits
