"""Prompt assembly helpers.

Implementation is intentionally deferred in this scaffold.
"""

from __future__ import annotations

from .models import ProjectMetadata, RetrievedChunk


def _format_chunk(chunk: RetrievedChunk) -> str:
    """Format a retrieved chunk for prompt inclusion."""

    name_suffix = f" :: {chunk.name}" if chunk.name else ""
    return (
        f"File: {chunk.file}\n"
        f"Lines: {chunk.start_line}-{chunk.end_line}\n"
        f"Type: {chunk.chunk_type}{name_suffix}\n"
        f"Score: {chunk.relevance_score:.2f}\n\n"
        f"{chunk.content.strip()}"
    )


def build_prompt(
    question: str,
    chunks: list[RetrievedChunk],
    metadata: ProjectMetadata,
    summaries: dict[str, str] | None = None,
) -> str:
    """Build a compact prompt for repository-grounded answering."""

    summaries = summaries or {}
    relevant_chunks = chunks[:5]
    chunk_block = "\n\n---\n\n".join(_format_chunk(chunk) for chunk in relevant_chunks)
    metadata_block = "\n".join(
        [
            f"project_name: {metadata.project_name}",
            f"indexed_at: {metadata.indexed_at}",
            f"file_count: {metadata.file_count}",
            f"chunk_count: {metadata.chunk_count}",
            f"embedding_model: {metadata.embedding_model}",
            f"version: {metadata.version}",
        ]
    )

    summary_files = list(dict.fromkeys(chunk.file for chunk in relevant_chunks))[:5]
    summary_block = "\n".join(f"- {file_name}: {summaries.get(file_name, 'no summary')}" for file_name in summary_files)

    return f"""You are answering questions about a code repository.

Use only the provided code context. Do not invent files, functions, or behavior.
If the answer is not supported by the context, say so explicitly.
Keep the explanation concise. If describing a flow, show it as an arrow diagram.
End with an EVIDENCE section listing exact file paths and line ranges.

QUESTION:
{question}

REPOSITORY METADATA:
{metadata_block}

FILE SUMMARIES:
{summary_block}

CODE CONTEXT:
{chunk_block}
"""
