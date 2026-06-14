"""Repository walking utilities.

This module provides a deterministic repository file lister that:

- respects .gitignore via `pathspec`
- skips configured directories and file extensions
- skips binary and large files
- returns repository-relative `Path` objects sorted deterministically

The implementation is intentionally small and testable.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional
from pathlib import Path

import pathspec

from .constants import MAX_FILE_SIZE_KB, SKIP_DIRS, SKIP_EXTENSIONS


def load_gitignore(repo_root: Path) -> Optional[pathspec.PathSpec]:
    """Load a .gitignore at `repo_root` if present and return a PathSpec.

    Returns None if no .gitignore is found or it contains no rules.
    """

    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.is_file():
        return None

    try:
        with gitignore_path.open("r", encoding="utf-8") as fh:
            lines = [line.rstrip("\n") for line in fh if line.strip() and not line.strip().startswith("#")]
        if not lines:
            return None
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)
    except OSError:
        # If we cannot read .gitignore, behave as if it's absent.
        return None


def _is_binary_file(path: Path, sample_size: int = 1024) -> bool:
    """Heuristic: return True if a file appears to be binary.

    We check for NUL bytes and a ratio of non-text bytes in a sample.
    """

    try:
        with path.open("rb") as fh:
            sample = fh.read(sample_size)
    except OSError:
        # If the file cannot be read, treat as binary to skip it.
        return True

    if not sample:
        return False

    if b"\0" in sample:
        return True

    # Count bytes outside a relaxed printable range
    printable = set(range(32, 127)) | {9, 10, 13}
    nontext = sum(1 for b in sample if b not in printable)
    # If more than 30% of the sample is non-text, consider it binary.
    return (nontext / len(sample)) > 0.30


def _is_too_large(path: Path, max_kb: int = MAX_FILE_SIZE_KB) -> bool:
    """Return True when file is larger than `max_kb` kilobytes.

    Permission errors are surfaced as True so the file is skipped.
    """

    try:
        size = path.stat().st_size
        return size > (max_kb * 1024)
    except OSError:
        return True


def _matches_gitignore(spec: Optional[pathspec.PathSpec], rel_path: Path) -> bool:
    """Return True if `rel_path` (relative to repo root) matches the gitignore spec."""

    if spec is None:
        return False
    # pathspec expects posix-style paths
    try:
        return spec.match_file(rel_path.as_posix())
    except Exception:
        return False


def iter_files(repo_root: Path) -> Iterable[Path]:
    """Yield absolute file paths for files that should be indexed.

    Files are yielded in a deterministic order if the caller sorts the output.
    """

    repo_root = repo_root.resolve()
    spec = load_gitignore(repo_root)

    for root, dirs, files in os.walk(repo_root, topdown=True):
        root_path = Path(root)
        try:
            rel_root = root_path.relative_to(repo_root)
        except Exception:
            # If for any reason relative_to fails, compute a fallback string
            rel_root = Path(".")

        # Filter directories in-place to avoid descending into skipped dirs
        dirs_to_keep: List[str] = []
        for d in sorted(dirs):
            d_rel = (rel_root / d).as_posix()
            if d in SKIP_DIRS:
                continue
            if _matches_gitignore(spec, Path(d_rel)):
                continue
            dirs_to_keep.append(d)
        dirs[:] = dirs_to_keep

        for fname in sorted(files):
            file_path = root_path / fname
            rel_path = (rel_root / fname)

            # Skip by extension
            if file_path.suffix in SKIP_EXTENSIONS:
                continue

            # Skip gitignored files
            if _matches_gitignore(spec, rel_path):
                continue

            # Skip huge files and unreadable files
            if _is_too_large(file_path):
                continue

            # Skip binary files
            if _is_binary_file(file_path):
                continue

            yield file_path


def walk_repository(repo_root: Path) -> List[Path]:
    """Return a sorted list of repository-relative file paths to index.

    The returned list contains Path objects relative to `repo_root`.
    """

    repo_root = repo_root.resolve()
    results: List[Path] = []
    for absolute in iter_files(repo_root):
        try:
            rel = absolute.relative_to(repo_root)
            results.append(rel)
        except Exception:
            # Skip files we cannot relativize for any reason
            continue

    # Ensure deterministic ordering
    results_sorted = sorted(results, key=lambda p: p.as_posix())
    return results_sorted


def main() -> None:
    """Small CLI to exercise the walker.

    Example:
        python -m codeask.walker --path /path/to/repo
    """

    import argparse

    parser = argparse.ArgumentParser(description="List repository files for CodeAsk")
    parser.add_argument("--path", "-p", default=".", help="Repository root path")
    args = parser.parse_args()

    repo = Path(args.path).resolve()
    files = walk_repository(repo)
    for p in files:
        print(p.as_posix())
    print(f"\nFound {len(files)} files")


if __name__ == "__main__":
    main()
