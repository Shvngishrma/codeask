# CodeAsk

Understand any codebase in minutes — a small, local CLI to ask
architectural and code-understanding questions against a repository and
receive concise answers with file:line evidence.

This repository is a working scaffold that implements a complete local
indexing and retrieval flow for code, with clear extension points for
summarization and alternate LLM backends.

## Status (what's implemented)

- Repository walking and `.gitignore`-aware file listing (`codeask.walker`).
- Deterministic chunking (AST-based for Python, text fallback) (`codeask.chunker`).
- Local embeddings using `sentence-transformers` (`codeask.embedder`).
- Persistent vector store backed by ChromaDB (`codeask.store`).
- Retrieval and top-k results mapping to `RetrievedChunk` objects (`codeask.retriever`).
- CLI entrypoint and orchestration (`codeask.main`) with `init`, `inspect`, and query modes.
- Metadata read/write helpers (`codeask.metadata`) and typed domain models (`codeask.models`).
- Anthropic/Claude provider abstraction (`codeask.llm`) and configuration (`codeask.config`).

## Status (deferred / scaffolded)

- File summarization implementation is a placeholder (`codeask.summarizer`) and raises `NotImplementedError`.
- Rich display helpers are minimal and intended to be extended (`codeask.display`).
- A fully local LLM `LocalProvider` is scaffolded but not implemented.

## Requirements

- Python 3.10+
- The runtime dependencies are declared in `pyproject.toml` and `requirements.txt`.

Install editable mode for development:

```bash
pip install -e .
```

Or install the pinned dependencies directly:

```bash
pip install -r requirements.txt
```

## Environment

Create a `.env` file or export the Anthropic key in your environment:

```env
ANTHROPIC_API_KEY=sk-xxx
```

The CLI will read environment variables via `python-dotenv` at startup.

## CLI Usage

The package exposes a `codeask` console script (registered in `pyproject.toml`).

- Initialize and index a repository (creates a `.codeask/` directory with Chroma persistence):

```bash
codeask init --path /path/to/repo
```

- Recreate the index from scratch:

```bash
codeask init --path /path/to/repo --reset
```

- Inspect retrieval output (no LLM call):

```bash
codeask inspect "how do I login?" --path /path/to/repo
```

- Ask a natural-language question (requires an indexed repository):

```bash
codeask "where should I start reading this codebase?"
```

When answering, CodeAsk loads top-k chunks from ChromaDB, builds a compact
prompt, and streams the LLM response. If the repository is not indexed you
will see an instructive error asking you to run `codeask init` first.

## `.codeask/` layout

After `init` this repository will contain a `.codeask` directory with:

```text
.codeask/
├── chroma/             # ChromaDB on-disk persistence
└── metadata.json       # indexing metadata (created by metadata.write)
```

## Project layout

```text
codeask/
├── codeask/                    # package source
│   ├── __init__.py
│   ├── main.py                 # CLI entrypoint and command dispatch
│   ├── walker.py               # repo traversal and .gitignore handling
│   ├── chunker.py              # AST & text chunking
│   ├── embedder.py             # sentence-transformers wrapper
│   ├── store.py                # ChromaDB persistence helpers
│   ├── retriever.py            # query → top-k chunk retrieval
│   ├── context_builder.py      # prompt assembly for the LLM
│   ├── llm.py                  # LLM provider abstraction (Anthropic)
│   ├── metadata.py             # read/write index metadata
│   ├── models.py               # dataclasses: Chunk, RetrievedChunk, ProjectMetadata
│   ├── summarizer.py           # file summarization (TODO)
│   └── display.py              # rich output helpers (minimal)
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Notes & Next Steps

- `codeask.summarizer` is intentionally unimplemented in this scaffold; the
	`init` flow currently indexes chunks and embeddings but file-level
	summarization must be added before summary caching is available.
- `codeask.llm.AnthropicProvider` requires a valid `ANTHROPIC_API_KEY`.
- The embedding model `all-MiniLM-L6-v2` is downloaded on first use by
	`sentence-transformers` and can require network access and temporary disk.

If you'd like, I can:

- Add a short quickstart example with a small local repo.
- Implement a simple summarizer using the same LLM provider.
- Add more rich output formatting and example screenshots.

-----

Updated to reflect the current implementation in the codebase.

