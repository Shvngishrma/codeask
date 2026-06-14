"""CodeAsk CLI entrypoint."""

from __future__ import annotations

import argparse
import shutil
import sys
import textwrap
from pathlib import Path

from rich.console import Console
from dotenv import load_dotenv

from .chunker import chunk_file
from .config import SETTINGS
from .embedder import embed_texts
from .exceptions import CodeAskError, LLMProviderError, RepositoryNotIndexedError
from .context_builder import build_prompt
from .llm import create_provider
from .metadata import create_metadata, metadata_exists, read_metadata, write_metadata
from .models import ProjectMetadata
from .retriever import retrieve
from .store import get_client, get_collection, reset_collection, store_chunks
from .walker import walk_repository

console = Console()


def _resolve_repo_root(path: str | None = None) -> Path:
    """Resolve the repository root for a command."""

    return Path(path).expanduser().resolve() if path else Path.cwd().resolve()


def _metadata_path(repo_root: Path) -> Path:
    """Return the metadata file path for a repository root."""

    return SETTINGS.metadata_path(repo_root)


def _codeask_dir(repo_root: Path) -> Path:
    """Return the .codeask directory for a repository root."""

    return SETTINGS.codeask_dir(repo_root)


def _print_results(results: list) -> None:
    """Print retrieval results in a plain, judge-friendly format."""

    print("Top Results")
    print()
    if not results:
        print("No results found")
        return

    for index, chunk in enumerate(results, start=1):
        line_range = f"lines {chunk.start_line}-{chunk.end_line}"
        score = f"score={chunk.relevance_score:.2f}"
        name_part = f" ({chunk.name})" if chunk.name else ""
        print(f"{index}. {chunk.file}{name_part} {line_range} {score}")


def _print_inspect_results(results: list) -> None:
    """Print retrieval results with compact chunk previews for debugging."""

    print("Retrieved Chunks")
    print()
    if not results:
        print("No results found")
        return

    for index, chunk in enumerate(results, start=1):
        preview = " ".join(chunk.content.strip().split())
        preview = textwrap.shorten(preview, width=300, placeholder="...")
        line_range = f"lines {chunk.start_line}-{chunk.end_line}"
        score = f"score={chunk.relevance_score:.2f}"
        print(f"{index}.")
        print(f"File: {chunk.file}")
        print(f"Lines: {line_range}")
        print(f"Score: {score}")
        print()
        print(preview)
        if index != len(results):
            print()
            print("-" * 16)
            print()


def _index_repository(repo_root: Path, reset: bool) -> None:
    """Walk, chunk, embed, and store a repository index."""

    codeask_dir = _codeask_dir(repo_root)
    if reset and codeask_dir.exists():
        shutil.rmtree(codeask_dir)

    codeask_dir.mkdir(parents=True, exist_ok=True)

    relative_files = walk_repository(repo_root)
    chunks = []
    for rel_path in relative_files:
        try:
            content = (repo_root / rel_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        chunks.extend(chunk_file(rel_path, content))

    if not chunks:
        raise CodeAskError("No chunks were created. Repository may not contain supported source files.")

    embeddings = embed_texts([chunk.content for chunk in chunks])
    client = get_client(repo_root)
    reset_collection(client)
    collection = get_collection(client)
    store_chunks(collection, chunks, embeddings)

    metadata = create_metadata(
        project_name=repo_root.name,
        file_count=len(relative_files),
        chunk_count=len(chunks),
        embedding_model=SETTINGS.default_embedding_model,
        version=SETTINGS.version,
    )
    write_metadata(SETTINGS.metadata_path(repo_root), metadata)

    print(f"Found {len(relative_files)} files")
    print(f"Created {len(chunks)} chunks")
    print("Generated embeddings")
    print("Stored in ChromaDB")
    print("Done")


def _query_repository(repo_root: Path, question: str) -> list:
    """Load the index and return retrieval results for a question."""

    metadata_path = _metadata_path(repo_root)
    if not metadata_exists(metadata_path):
        raise RepositoryNotIndexedError("Repository not indexed. Run `codeask init` first.")

    _ = read_metadata(metadata_path)
    client = get_client(repo_root)
    collection = get_collection(client)
    return retrieve(question, collection, embed_texts)


def _load_project_metadata(repo_root: Path) -> ProjectMetadata:
    """Load project metadata for prompt assembly."""

    metadata_path = _metadata_path(repo_root)
    if not metadata_exists(metadata_path):
        raise RepositoryNotIndexedError("Repository not indexed. Run `codeask init` first.")

    return read_metadata(metadata_path)


def _answer_repository(repo_root: Path, question: str) -> None:
    """Retrieve context, build a prompt, and stream a Claude answer."""

    metadata = _load_project_metadata(repo_root)
    chunks = _query_repository(repo_root, question)
    prompt = build_prompt(question=question, chunks=chunks, metadata=metadata, summaries={})
    provider = create_provider()

    print("Answer")
    print()
    try:
        for text in provider.stream(prompt):
            print(text, end="", flush=True)
        print()
    except LLMProviderError as exc:
        console.print(f"Error: {exc}")
        raise SystemExit(1) from exc


def init(path: str = ".", reset: bool = False) -> None:
    """Initialize a repository for CodeAsk."""

    repo_root = _resolve_repo_root(path)

    try:
        _index_repository(repo_root, reset)
    except CodeAskError as exc:
        console.print(f"Error: {exc}")
        raise SystemExit(1) from exc


def inspect(query: str, path: str = ".") -> None:
    """Inspect retrieval output without any LLM involvement."""

    repo_root = _resolve_repo_root(path)

    try:
        results = _query_repository(repo_root, query)
        _print_inspect_results(results)
    except CodeAskError as exc:
        console.print(f"Error: {exc}")
        raise SystemExit(1) from exc


def _parse_and_run(argv: list[str]) -> None:
    """Parse command arguments and dispatch to the right handler."""

    if not argv or argv[0] in {"--help", "-h"}:
        print("Usage:")
        print("  codeask init [--path PATH] [--reset]")
        print("  codeask inspect QUERY [--path PATH]")
        print("  codeask \"question\"")
        return

    if argv[0] == "init":
        parser = argparse.ArgumentParser(prog="codeask init", add_help=True)
        parser.add_argument("--path", default=".")
        parser.add_argument("--reset", action="store_true")
        args = parser.parse_args(argv[1:])
        init(path=args.path, reset=args.reset)
        return

    if argv[0] == "inspect":
        parser = argparse.ArgumentParser(prog="codeask inspect", add_help=True)
        parser.add_argument("query")
        parser.add_argument("--path", default=".")
        args = parser.parse_args(argv[1:])
        inspect(query=args.query, path=args.path)
        return

    if argv[0].startswith("-"):
        print("Usage:")
        print("  codeask init [--path PATH] [--reset]")
        print("  codeask inspect QUERY [--path PATH]")
        print("  codeask \"question\"")
        raise SystemExit(2)

    question = argv[0]
    repo_root = Path.cwd().resolve()

    try:
        _answer_repository(repo_root, question)
    except CodeAskError as exc:
        console.print(f"Error: {exc}")
        raise SystemExit(1) from exc


def main() -> None:
    """CLI entrypoint."""

    load_dotenv()
    _parse_and_run(sys.argv[1:])


if __name__ == "__main__":
    main()
