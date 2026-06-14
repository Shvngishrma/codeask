"""Retrieval utilities for CodeAsk.

This module keeps the retrieval surface intentionally small: embed the query,
query ChromaDB, and return structured `RetrievedChunk` objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence, TYPE_CHECKING

from .config import SETTINGS
from .models import RetrievedChunk

if TYPE_CHECKING:  # pragma: no cover - typing only
    from chromadb.api.models.Collection import Collection


TOP_K: int = SETTINGS.default_top_k


def retrieve(
    query: str,
    collection: "Collection",
    embed_fn: Callable[[Sequence[str]], list[list[float]]],
) -> list[RetrievedChunk]:
    """Return the top matching chunks for a query.

    Args:
        query: Natural-language question from the user.
        collection: ChromaDB collection containing indexed code chunks.
        embed_fn: Function that converts text to embeddings.
    """

    if not query.strip():
        return []

    query_embedding = embed_fn([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0] or []
    metadatas = results.get("metadatas", [[]])[0] or []
    distances = results.get("distances", [[]])[0] or []

    if not documents or not metadatas or not distances:
        return []

    chunks: list[RetrievedChunk] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        file_name = str(metadata.get("file", ""))
        start_line = int(metadata.get("start_line", 0))
        end_line = int(metadata.get("end_line", 0))
        chunk_type = str(metadata.get("chunk_type", ""))
        name_value = metadata.get("name", "")
        name = str(name_value) if name_value else None

        chunks.append(
            RetrievedChunk(
                file=file_name,
                start_line=start_line,
                end_line=end_line,
                content=str(document),
                chunk_type=chunk_type,
                name=name,
                relevance_score=1.0 - float(distance),
            )
        )

    return chunks


def _smoke_test() -> None:
    """Run a small smoke test against an in-memory Chroma collection."""

    from tempfile import TemporaryDirectory

    import chromadb

    from .embedder import embed_texts
    from .models import Chunk
    from .store import get_collection

    with TemporaryDirectory() as tmp_dir:
        client = chromadb.PersistentClient(path=str(Path(tmp_dir) / ".codeask" / "chroma"))
        collection = get_collection(client)

        sample_chunk = Chunk(
            file="src/auth.py",
            start_line=10,
            end_line=20,
            content="def login(user):\n    return token\n",
            chunk_type="function",
            name="login",
        )
        collection.add(
            ids=["src/auth.py:10"],
            documents=[sample_chunk.content],
            embeddings=embed_texts([sample_chunk.content]),
            metadatas=[
                {
                    "file": sample_chunk.file,
                    "start_line": sample_chunk.start_line,
                    "end_line": sample_chunk.end_line,
                    "chunk_type": sample_chunk.chunk_type,
                    "name": sample_chunk.name or "",
                }
            ],
        )

        hits = retrieve("how do I login?", collection, embed_texts)
        print(f"Smoke test hits: {len(hits)}")
        if hits:
            print(hits[0])


def main() -> None:
    """Entry point for `python -m codeask.retriever`."""

    _smoke_test()


if __name__ == "__main__":
    main()
