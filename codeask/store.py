"""ChromaDB persistence helpers for CodeAsk.

This module intentionally stays thin: it exposes a direct persistent client,
one collection factory, and a small write helper for indexed chunks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, TYPE_CHECKING

import chromadb

from .constants import DEFAULT_TOP_K
from .models import Chunk

if TYPE_CHECKING:  # pragma: no cover - typing only
    from chromadb.api.client import ClientAPI
    from chromadb.api.models.Collection import Collection


COLLECTION_NAME: str = "chunks"


def get_store_path(repo_root: Path) -> Path:
    """Return the on-disk directory used for ChromaDB persistence."""

    return repo_root / ".codeask" / "chroma"


def get_client(repo_root: Path) -> "chromadb.PersistentClient":
    """Create a persistent ChromaDB client rooted at the repository store."""

    store_path = get_store_path(repo_root)
    store_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(store_path))


def get_collection(client: "ClientAPI") -> "Collection":
    """Return the primary CodeAsk collection using cosine distance."""

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection(client: "ClientAPI") -> None:
    """Delete the primary collection if it already exists."""

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        # Chroma raises different exceptions depending on version/state.
        pass


def _chunk_id(chunk: Chunk) -> str:
    """Build a stable ChromaDB record id for a chunk."""

    return f"{chunk.file}:{chunk.start_line}"


def store_chunks(
    collection: "Collection",
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
) -> None:
    """Persist chunks and embeddings in ChromaDB.

    Args:
        collection: The ChromaDB collection to write to.
        chunks: Code chunks to persist.
        embeddings: Embedding vectors aligned with `chunks`.
    """

    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must have the same length")

    if not chunks:
        return

    collection.add(
        ids=[_chunk_id(chunk) for chunk in chunks],
        documents=[chunk.content for chunk in chunks],
        embeddings=[list(vector) for vector in embeddings],
        metadatas=[
            {
                "file": chunk.file,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type,
                "name": chunk.name or "",
            }
            for chunk in chunks
        ],
    )


def _smoke_test() -> None:
    """Run a tiny end-to-end persistence smoke test."""

    from tempfile import TemporaryDirectory

    from .models import Chunk

    with TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir)
        client = get_client(repo_root)
        collection = get_collection(client)

        store_chunks(
            collection,
            chunks=[
                Chunk(
                    file="src/example.py",
                    start_line=1,
                    end_line=3,
                    content="def hello():\n    return 'world'\n",
                    chunk_type="function",
                    name="hello",
                )
            ],
            embeddings=[[0.1] * 384],
        )

        result = collection.query(
            query_embeddings=[[0.1] * 384],
            n_results=min(DEFAULT_TOP_K, 1),
            include=["documents", "metadatas", "distances"],
        )
        print("Smoke test query result count:", len(result["documents"][0]))


def main() -> None:
    """Entry point for `python -m codeask.store`."""

    _smoke_test()


if __name__ == "__main__":
    main()
