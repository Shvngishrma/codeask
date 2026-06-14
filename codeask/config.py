"""Central configuration for CodeAsk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_BATCH_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_SUMMARY_MAX_CHARS,
    DEFAULT_TOP_K,
    SCHEMA_VERSION,
)


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed project settings used across the codebase."""

    codeask_dir_name: str = ".codeask"
    chroma_dir_name: str = "chroma"
    metadata_file_name: str = "metadata.json"
    summaries_file_name: str = "summaries.json"
    anthropic_api_key_env: str = "ANTHROPIC_API_KEY"
    default_embedding_model: str = DEFAULT_EMBEDDING_MODEL
    default_llm_model: str = DEFAULT_ANTHROPIC_MODEL
    default_top_k: int = DEFAULT_TOP_K
    batch_size: int = DEFAULT_BATCH_SIZE
    summary_max_chars: int = DEFAULT_SUMMARY_MAX_CHARS
    version: str = SCHEMA_VERSION

    def codeask_dir(self, repo_root: Path) -> Path:
        """Return the .codeask directory for a repository root."""

        return repo_root / self.codeask_dir_name

    def chroma_dir(self, repo_root: Path) -> Path:
        """Return the Chroma persistence directory for a repository root."""

        return self.codeask_dir(repo_root) / self.chroma_dir_name

    def metadata_path(self, repo_root: Path) -> Path:
        """Return the metadata file path for a repository root."""

        return self.codeask_dir(repo_root) / self.metadata_file_name

    def summaries_path(self, repo_root: Path) -> Path:
        """Return the summaries cache path for a repository root."""

        return self.codeask_dir(repo_root) / self.summaries_file_name


SETTINGS = Settings()
