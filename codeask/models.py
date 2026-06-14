"""Shared domain models for CodeAsk."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chunk:
    """A unit of indexed code content."""

    file: str
    start_line: int
    end_line: int
    content: str
    chunk_type: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk returned from retrieval with a relevance score."""

    file: str
    start_line: int
    end_line: int
    content: str
    chunk_type: str
    name: str | None
    relevance_score: float


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """Metadata describing an indexed project snapshot."""

    project_name: str
    indexed_at: str
    file_count: int
    chunk_count: int
    embedding_model: str
    version: str
