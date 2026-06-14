"""Project-wide constants for CodeAsk."""

from __future__ import annotations

SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "target",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        "vendor",
        ".gradle",
        ".idea",
        ".vscode",
        "coverage",
        ".pytest_cache",
        ".codeask",
    }
)

SKIP_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pyc",
        ".pyo",
        ".o",
        ".so",
        ".exe",
        ".dll",
        ".class",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".lock",
        ".min.js",
        ".min.css",
        ".map",
    }
)

MAX_FILE_SIZE_KB: int = 200
DEFAULT_CHUNK_SIZE: int = 120
DEFAULT_CHUNK_OVERLAP: int = 20
DEFAULT_TOP_K: int = 5
DEFAULT_BATCH_SIZE: int = 64
DEFAULT_SUMMARY_MAX_CHARS: int = 3000
DEFAULT_ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
DEFAULT_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
SCHEMA_VERSION: str = "0.1.0"
