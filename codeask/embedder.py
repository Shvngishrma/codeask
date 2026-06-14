"""Embedding utilities for CodeAsk.

This module provides a small, production-friendly boundary around the local
sentence-transformers model used for indexing and query embedding.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence, TYPE_CHECKING

from .config import SETTINGS
from .exceptions import ConfigurationError

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_model(model_name: str | None = None) -> "SentenceTransformer":
    """Load and cache the embedding model.

    The default model is `all-MiniLM-L6-v2`, which provides a small 384-dim
    embedding space suitable for fast local indexing.
    """

    resolved_model_name = model_name or SETTINGS.default_embedding_model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ConfigurationError(
            "sentence-transformers is required for embeddings. Install project dependencies first."
        ) from exc

    try:
        return SentenceTransformer(resolved_model_name)
    except Exception as exc:  # pragma: no cover - model download/runtime failures depend on env
        raise ConfigurationError(f"Failed to load embedding model: {resolved_model_name}") from exc


def embed_texts(
    texts: Sequence[str],
    *,
    model_name: str | None = None,
    batch_size: int | None = None,
) -> list[list[float]]:
    """Embed texts into a list of floating-point vectors.

    Args:
        texts: Input strings to encode.
        model_name: Optional override for the embedding model.
        batch_size: Optional override for encode batch size.

    Returns:
        A list of embedding vectors, one per input text.
    """

    if not texts:
        return []

    model = get_model(model_name)
    resolved_batch_size = batch_size or SETTINGS.batch_size

    embeddings = model.encode(
        list(texts),
        batch_size=resolved_batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )

    return embeddings.tolist()

