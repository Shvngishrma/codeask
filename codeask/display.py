"""Rich terminal output helpers.

Implementation is intentionally deferred in this scaffold.
"""

from __future__ import annotations

from rich.console import Console

console = Console()


def show_header() -> None:
    """Render the application header."""

    console.print("[bold cyan]CodeAsk[/bold cyan] — Understand any codebase in minutes")


def show_placeholder(message: str) -> None:
    """Render a placeholder notice."""

    console.print(f"[yellow]{message}[/yellow]")
