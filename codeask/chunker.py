"""Code chunking utilities.

This module exposes a small, testable chunker that prefers Python AST
boundaries for `.py` files and falls back to line-based regex chunking for
other languages or when Python parsing fails.
"""

from __future__ import annotations

from typing import List
from pathlib import Path
import ast

from .models import Chunk
from .constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


def _chunk_python(file_path: Path, content: str) -> List[Chunk]:
    """Chunk Python source by AST nodes (functions/classes).

    Returns a list of `Chunk` instances. If a file contains no suitable AST
    nodes, an empty list is returned so callers can fall back to text chunking.
    """

    tree = ast.parse(content)
    lines = content.splitlines()
    chunks: List[Chunk] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # ast uses 1-based lineno indices
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)

            if start is None:
                continue
            if end is None:
                # best-effort: use last child's lineno if available
                try:
                    end = node.body[-1].lineno
                except Exception:
                    end = start

            # Skip very small stubs
            if (end - start + 1) < 3:
                continue

            start_idx = max(0, start - 1)
            end_idx = min(len(lines), end)
            chunk_content = "\n".join(lines[start_idx:end_idx])

            chunk_type = "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class"
            name = getattr(node, "name", None)

            chunks.append(
                Chunk(
                    file=str(file_path),
                    start_line=start,
                    end_line=end,
                    content=chunk_content,
                    chunk_type=chunk_type,
                    name=name,
                )
            )

    return chunks


def _chunk_text(file_path: Path, content: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Chunk]:
    """Chunk plain text by paragraph and fixed-size sliding windows.

    This is a simple and robust fallback used for non-Python files and for
    Python files that fail AST parsing.
    """

    lines = content.splitlines()
    if not lines:
        return []

    # Split by blank-line paragraphs to respect logical blocks
    paragraphs: List[List[str]] = []
    cur: List[str] = []
    for line in lines:
        if line.strip() == "":
            if cur:
                paragraphs.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        paragraphs.append(cur)

    # Re-join paragraphs and chunk by line windows
    chunks: List[Chunk] = []
    cursor = 0
    all_lines: List[str] = []
    para_starts: List[int] = []
    for p in paragraphs:
        para_starts.append(len(all_lines) + 1)  # 1-based line numbers
        all_lines.extend(p)
        all_lines.append("")  # preserve paragraph break

    total_lines = len(all_lines)
    if total_lines == 0:
        return []

    while cursor < total_lines:
        start = cursor
        end = min(total_lines, start + chunk_size)
        chunk_lines = all_lines[start:end]

        chunk_start_line = start + 1
        chunk_end_line = end

        chunk_content = "\n".join(chunk_lines).strip()
        if chunk_content:
            chunks.append(
                Chunk(
                    file=str(file_path),
                    start_line=chunk_start_line,
                    end_line=chunk_end_line,
                    content=chunk_content,
                    chunk_type="block",
                    name=None,
                )
            )

        # advance with overlap
        if end >= total_lines:
            break
        cursor = max(0, end - overlap)

    return chunks


def chunk_file(file_path: Path, content: str) -> List[Chunk]:
    """Chunk a single file into a list of `Chunk` objects.

    For `.py` files we use AST-based chunking with a fallback to text-based
    chunking when parsing fails. For other files we use the text chunker.
    """

    if file_path.suffix == ".py":
        try:
            py_chunks = _chunk_python(file_path, content)
            if py_chunks:
                return py_chunks
        except SyntaxError:
            # fall through to text chunking on parse error
            pass

    return _chunk_text(file_path, content)

