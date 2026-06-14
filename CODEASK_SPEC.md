# CodeAsk — Technical Specification

**Version:** 1.0 (Hackathon Build)
**Last Updated:** June 13, 2026
**Scope:** 38-hour hackathon build

---

## 1. Project Overview

**Name:** CodeAsk

**Tagline:** Understand any codebase in minutes.

**One-liner:** A local CLI that lets engineers ask architectural questions about any repository — where is auth handled, which files touch the database, where should I start reading — with file:line evidence in every answer.


## 1.5 MVP Must Work (Survival Kit)

If Sunday 10am arrives and only these work, you still submit:

1. Walk repo → file list
2. Chunk files → Chunk objects  
3. Embed chunks → vectors
4. Store in ChromaDB
5. Retrieve top 5 on query
6. Claude answers from chunks
7. File:line evidence in output

---

## 2. Folder Structure

```
codeask/
├── codeask/                    # main package
│   ├── __init__.py
│   ├── main.py                 # CLI entrypoint (typer app)
│   ├── walker.py               # file system traversal
│   ├── chunker.py              # AST + regex chunking
│   ├── embedder.py             # embedding generation
│   ├── store.py                # ChromaDB read/write
│   ├── retriever.py            # query → top-k chunks
│   ├── summarizer.py           # per-file summaries via Claude
│   ├── context_builder.py      # assembles prompt from chunks
│   ├── llm.py                  # Claude API calls
│   └── display.py              # rich terminal output
│
├── .codeask/                   # auto-created on `codeask init` (gitignored)
│   ├── chroma/                 # ChromaDB persistence directory
│   └── summaries.json          # file-level summaries cache
│
├── requirements.txt
├── README.md
└── pyproject.toml              # for `pip install -e .` so `codeask` works as a command
```

---

## 3. Dependencies

```
# requirements.txt

# CLI
typer==0.12.3
rich==13.7.1

# Parsing
pathspec==0.12.1          # .gitignore parsing

# Embeddings
sentence-transformers==3.0.1   # local embeddings, no API key needed

# Vector DB
chromadb==0.5.3

# LLM
anthropic==0.28.0

# Utilities
python-dotenv==1.0.1
```

**Embedding model:** `all-MiniLM-L6-v2` (downloads automatically on first run, ~80MB, fast)

**LLM:** Claude claude-sonnet-4-6 via Anthropic API

**Python version:** 3.10+

---

## 4. Environment Variables

```
# .env (user creates this in repo root or home dir)
ANTHROPIC_API_KEY=sk-ant-...
```

Loaded via `python-dotenv` in `main.py` at startup.

---

## 5. Installation

```
git clone https://github.com/yourname/codeask
cd codeask
pip install -e .
```

`pyproject.toml` registers the `codeask` CLI command:

```
[project]
name = "codeask"
version = "0.1.0"
dependencies = [...]   # same as requirements.txt

[project.scripts]
codeask = "codeask.main:app"
```

---

## 6. CLI Commands

Defined in `codeask/main.py` using `typer`.

### 6.1 `codeask init`

```
codeask init
```

**What it does:**

1. Walks repo from current directory

2. Filters files via `.gitignore` + hardcoded skip list

3. Chunks each file (Python AST / regex fallback)

4. Generates embeddings for each chunk

5. Stores chunks + embeddings in ChromaDB under `.codeask/chroma/`

6. Generates one-line summaries per file via Claude

7. Saves summaries to `.codeask/summaries.json`

**Output (via rich):**

```
 CodeAsk — Indexing repository...

 Scanning files...       ████████████████ 247 files found
 Chunking...             ████████████████ 1,842 chunks created
 Embedding...            ████████████████ done
 Summarizing files...    ████████████████ done

 Ready. Ask your first question:
 codeask "how does auth work?"
```

**Flags:**

```
codeask init --path /some/other/repo    # index a different directory
codeask init --reset                    # wipe .codeask/ and re-index
```

---

### 6.2 `codeask ""`

```
codeask "how does authentication work?"
codeask "which files touch the database?"
codeask "where should I start reading this codebase?"
```

**What it does:**

1. Checks `.codeask/` exists, exits with helpful error if not

2. Embeds the question

3. Retrieves top 7 chunks from ChromaDB

4. Loads file summaries from `.codeask/summaries.json`

5. Builds prompt (see Section 9)

6. Calls Claude API (streaming)

7. Displays answer + evidence with rich formatting

**Output:**

```
 CodeAsk

 How does authentication work?
 ────────────────────────────────────────────────────

 Authentication is handled via JWT tokens. When a user
 logs in, verify_token() in auth.py decodes the token
 and validates the signature. This is called by the
 auth middleware on every protected route.

 Flow:
   login_route  (routes.py:34)
        ↓
   authenticate  (auth.py:12)
        ↓
   verify_token  (auth.py:45)
        ↓
   jwt.decode    (auth.py:67)

 Evidence:
   src/auth.py          lines 45–87
   src/middleware.py    lines 12–34
   src/routes.py        lines 30–45
```

---

## 7. Component Specifications

### 7.1 `walker.py` — File Walker

**Inputs:** repo root path (str)

**Outputs:** list of file paths (list[str])

**Logic:**

```
SKIP_DIRS = {
    '.git', 'node_modules', 'target', '__pycache__',
    '.venv', 'venv', 'env', 'build', 'dist', 'vendor',
    '.gradle', '.idea', '.vscode', 'coverage', '.pytest_cache',
    '.codeask'   # never index our own db
}

SKIP_EXTENSIONS = {
    '.pyc', '.pyo', '.o', '.so', '.exe', '.dll', '.class',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
    '.pdf', '.zip', '.tar', '.gz', '.lock',
    '.min.js', '.min.css', '.map'
}

MAX_FILE_SIZE_KB = 200   # skip huge files
```

**`.gitignore` parsing:**

```
import pathspec

def load_gitignore(root: str) -> pathspec.PathSpec | None:
    gitignore = os.path.join(root, '.gitignore')
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None
```

**Returns:** only readable text files under `MAX_FILE_SIZE_KB`

---

### 7.2 `chunker.py` — Parser & Chunker

**Inputs:** file path (str), file content (str)

**Outputs:** list of Chunk objects

**Chunk dataclass:**

```
@dataclass
class Chunk:
    file: str           # relative path from repo root
    start_line: int
    end_line: int
    content: str
    chunk_type: str     # "function" | "class" | "block"
    name: str | None    # function/class name if available
```

**Python files → AST chunking:**

```
import ast

def chunk_python(filepath, content):
    tree = ast.parse(content)
    chunks = []
    lines = content.splitlines()
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = node.end_lineno
            chunk_content = '\n'.join(lines[start:end])
            
            # skip tiny stubs under 3 lines
            if end - start  list[list[float]]]:
    model = get_model()
    return model.encode(texts, show_progress_bar=False).tolist()
```

**Batching:** embed in batches of 64 to avoid memory issues on large repos.

---

### 7.4 `store.py` — Vector Store

**Technology:** ChromaDB (local persistence)

**Persistence path:** `.codeask/chroma/` relative to repo root

**Two collections:**

1. `chunks` — code chunks with embeddings

2. `summaries` — file-level summaries (stored as JSON, not in Chroma)

```
import chromadb

def get_client(repo_root: str):
    db_path = os.path.join(repo_root, '.codeask', 'chroma')
    return chromadb.PersistentClient(path=db_path)

def get_collection(client):
    return client.get_or_create_collection(
        name="chunks",
        metadata={"hnsw:space": "cosine"}
    )

def store_chunks(collection, chunks: list[Chunk], embeddings: list[list[float]]):
    collection.add(
        ids=[f"{c.file}:{c.start_line}" for c in chunks],
        embeddings=embeddings,
        documents=[c.content for c in chunks],
        metadatas=[{
            "file": c.file,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "chunk_type": c.chunk_type,
            "name": c.name or ""
        } for c in chunks]
    )
```

---

### 7.5 `retriever.py` — Retrieval Engine

**Inputs:** query (str), collection, query embedding

**Outputs:** list of retrieved chunks with metadata

```
TOP_K = 5   # retrieve 5, give all to Claude (MVP change)

def retrieve(query: str, collection, embedder) -> list[dict]:
    query_embedding = embedder.embed([query])[0]
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"]
    )
    
    chunks = []
    for doc, meta, dist in zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ):
        chunks.append({
            "content": doc,
            "file": meta["file"],
            "start_line": meta["start_line"],
            "end_line": meta["end_line"],
            "chunk_type": meta["chunk_type"],
            "name": meta["name"],
            "relevance_score": 1 - dist   # cosine → similarity
        })
    
    return chunks
```

---

### 7.6 `summarizer.py` — File Summarizer

Called during `codeask init`. One Claude API call per file.

```
def summarize_file(filepath: str, content: str, client) -> str:
    # truncate large files before summarizing
    truncated = content[:3000]
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"In one sentence, describe what this file does:\n\n{filepath}\n\n{truncated}"
        }]
    )
    return response.content[0].text.strip()
```

**Storage:** `.codeask/summaries.json`

```
{
  "src/auth.py": "Handles JWT token generation and verification.",
  "src/routes.py": "Defines all HTTP route handlers for the API.",
  "src/db.py": "Database connection and query helpers."
}
```

---

### 7.7 `context_builder.py` — Prompt Assembly

**Inputs:** question, retrieved chunks, file summaries

**Output:** formatted prompt string

```
def build_prompt(question: str, chunks: list[dict], summaries: dict) -> str:
    
    # top file summaries (most relevant files only)
    relevant_files = list(dict.fromkeys([c["file"] for c in chunks]))
    summary_block = "\n".join([
        f"- {f}: {summaries.get(f, 'no summary')}"
        for f in relevant_files[:5]
    ])
    
    # retrieved code chunks
    chunk_block = "\n\n---\n\n".join([
        f"File: {c['file']} (lines {c['start_line']}-{c['end_line']})\n\n{c['content']}"
        for c in chunks
    ])
    
    return f"""You are a code intelligence assistant. Answer questions about this repository based only on the code provided.

REPOSITORY FILE SUMMARIES:
{summary_block}

RELEVANT CODE:
{chunk_block}

QUESTION: {question}

INSTRUCTIONS:
- Answer based only on the code above. Never make up file names or function names.
- If the question asks about a flow or sequence, show it as an arrow diagram like:
  function_a (file.py:line)
       ↓
  function_b (file.py:line)
- End your answer with an EVIDENCE section listing exact file paths and line ranges you referenced.
- Be concise. 3-5 sentences max for the explanation, then the diagram if relevant, then evidence.
- If you cannot answer from the provided code, say so explicitly.
"""
```

---

### 7.8 `llm.py` — Claude Integration

```
import anthropic

def ask(prompt: str, api_key: str, stream=True):
    client = anthropic.Anthropic(api_key=api_key)
    
    if stream:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text
    else:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        yield response.content[0].text
```

---

### 7.9 `display.py` — Rich Terminal Output

```
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich import print as rprint

console = Console()

def show_header():
    console.print(Panel.fit(
        "[bold cyan]CodeAsk[/bold cyan] — Understand any codebase in minutes",
        border_style="cyan"
    ))

def show_answer_streaming(question: str, text_generator):
    console.print(f"\n[bold white]{question}[/bold white]")
    console.print("─" * 60, style="dim")
    
    full_text = ""
    for chunk in text_generator:
        console.print(chunk, end="", highlight=False)
        full_text += chunk
    
    console.print("\n")
    return full_text

def show_error(message: str):
    console.print(f"\n[bold red]Error:[/bold red] {message}")
    
def show_not_initialized():
    console.print(Panel(
        "[yellow]Repository not indexed.[/yellow]\n\nRun [bold cyan]codeask init[/bold cyan] first.",
        border_style="yellow"
    ))
```

---

## 8. Data Flow — End to End

### Init flow

```
codeask init
    ↓
walker.py          → list of file paths
    ↓
chunker.py         → list of Chunk objects (AST for .py, regex for rest)
    ↓
embedder.py        → list of embedding vectors
    ↓
store.py           → write to ChromaDB at .codeask/chroma/
    ↓
summarizer.py      → one Claude call per file → .codeask/summaries.json
    ↓
display.py         → progress bars, completion message
```

### Query flow

```
codeask "question"
    ↓
main.py            → check .codeask/ exists
    ↓
embedder.py        → embed the question
    ↓
retriever.py       → top 7 chunks from ChromaDB
    ↓
store.py           → load summaries.json
    ↓
context_builder.py → assemble prompt
    ↓
llm.py             → streaming Claude call
    ↓
display.py         → stream answer to terminal with rich formatting
```

---

## 9. Error Handling

Situation
Behavior

`codeask "..."` before `codeask init`
Show friendly panel: "Run codeask init first"

No `.env` / missing API key
"ANTHROPIC_API_KEY not found. Add it to .env"

Repo has no Python files
Index whatever's there, warn user: "No Python files found, using generic chunking"

File has syntax errors (bad Python)
Catch `SyntaxError`, fall back to regex chunking for that file

ChromaDB write failure
Show error, suggest `codeask init --reset`

Claude API error / rate limit
Show error message, suggest retry

Binary file slips through
Catch `UnicodeDecodeError` in walker, skip silently

---

## 10. ChromaDB Schema

**Collection name:** `chunks`

```
id:          "{relative_file_path}:{start_line}"   e.g. "src/auth.py:45"
document:    raw chunk content (str)
embedding:   float vector (384 dims for all-MiniLM-L6-v2)
metadata:
    file:        str   "src/auth.py"
    start_line:  int   45
    end_line:    int   87
    chunk_type:  str   "function" | "class" | "block"
    name:        str   "verify_token" (or "" if none)
```

---

## 11. Demo Repo

**Use for building and demoing:** [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)

Why: Python, clean structure, has auth, database, routes — all the right touchpoints for demo questions.

**Three demo questions (practice these until output is clean):**

```
codeask "how does authentication work?"
codeask "which files touch the database?"
codeask "where should I start reading this codebase?"
```

---

## 12. Build Order (38 Hours)

```
Hours 0–2    setup: pyproject.toml, folder structure, .env loading, typer skeleton
Hours 2–6    walker.py working — can traverse a repo and print file list
Hours 6–10   chunker.py working — Python AST + regex fallback, print chunks
Hours 10–13  embedder.py + store.py — chunks going into ChromaDB
Hours 13–16  retriever.py — query returns top 7 chunks (test with print statements)
Hours 16–20  llm.py + context_builder.py — full pipeline works end to end (raw output ok)
Hours 20–24  display.py — rich formatting, streaming output, progress bars
Hours 24–28  summarizer.py — per-file summaries, summaries.json, inject into prompt
Hours 28–32  error handling, edge cases, test on demo repo
Hours 32–36  demo script practice, README, demo video recording
Hours 36–38  final submission polish
```

---

## 13. README Structure

```
# CodeAsk

Understand any codebase in minutes.

## The Problem
You just cloned a 50,000-line repository. Where do you even start?

## What it does
[3 demo GIFs or screenshots]

## Install
pip install -e .

## Usage
codeask init
codeask "how does auth work?"

## How it works
[architecture diagram — simple ascii is fine]

## Built with
Python · ChromaDB · sentence-transformers · Claude API · Rich · Typer
```

---

## 14. Demo Video Script

**Duration:** 90 seconds max

```
0:00–0:10   "I just cloned a 50,000-line FastAPI codebase. I have no idea where anything is."
             [show the repo in terminal, overwhelming file tree]

0:10–0:25   "codeask init" — show progress bars running, indexing completing

0:25–0:50   codeask "how does authentication work?"
             [let the answer stream live, don't cut it]

0:50–1:05   codeask "which files touch the database?"
             [clean evidence block visible]

1:05–1:20   codeask "where should I start reading?"
             [recommended reading order output]

1:20–1:30   "Local. No IDE. No subscription. Clone any repo, ask anything."
```

---

## 15. Post-Hackathon Roadmap

- Multi-language AST (tree-sitter)

- Symbol index for direct function lookup

- Incremental re-indexing via file hashing

- Session memory (multi-turn conversation)

- Cross-file call graph

- VS Code extension

- Local LLM support (Ollama)
