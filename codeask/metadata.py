"""Helpers for reading and writing repository metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import SETTINGS
from .exceptions import MetadataError
from .models import ProjectMetadata


def create_metadata(
    *,
    project_name: str,
    file_count: int,
    chunk_count: int,
    embedding_model: str | None = None,
    version: str | None = None,
) -> ProjectMetadata:
    """Create metadata for a freshly indexed repository."""

    return ProjectMetadata(
        project_name=project_name,
        indexed_at=datetime.now(timezone.utc).isoformat(),
        file_count=file_count,
        chunk_count=chunk_count,
        embedding_model=embedding_model or SETTINGS.default_embedding_model,
        version=version or SETTINGS.version,
    )


def metadata_to_dict(metadata: ProjectMetadata) -> dict[str, str | int]:
    """Convert metadata to a JSON-serializable dictionary."""

    return {
        "project_name": metadata.project_name,
        "indexed_at": metadata.indexed_at,
        "file_count": metadata.file_count,
        "chunk_count": metadata.chunk_count,
        "embedding_model": metadata.embedding_model,
        "version": metadata.version,
    }


def write_metadata(metadata_path: Path, metadata: ProjectMetadata) -> None:
    """Write metadata to disk as JSON."""

    try:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata_to_dict(metadata), indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise MetadataError(f"Unable to write metadata to {metadata_path}") from exc


def read_metadata(metadata_path: Path) -> ProjectMetadata:
    """Read project metadata from disk."""

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return ProjectMetadata(
            project_name=str(payload["project_name"]),
            indexed_at=str(payload["indexed_at"]),
            file_count=int(payload["file_count"]),
            chunk_count=int(payload["chunk_count"]),
            embedding_model=str(payload["embedding_model"]),
            version=str(payload["version"]),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MetadataError(f"Unable to read metadata from {metadata_path}") from exc


def metadata_exists(metadata_path: Path) -> bool:
    """Return whether metadata exists at the given path."""

    return metadata_path.is_file()
