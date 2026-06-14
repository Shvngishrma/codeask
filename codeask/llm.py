"""LLM provider abstractions for CodeAsk."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from collections.abc import Iterator

from .config import SETTINGS
from .exceptions import LLMProviderError


class LLMProvider(ABC):
    """Abstract base class for language model backends."""

    @abstractmethod
    def stream(self, prompt: str) -> Iterator[str]:
        """Yield a streaming response for a prompt."""

    def ask(self, prompt: str) -> str:
        """Return the full response for a prompt."""

        return "".join(self.stream(prompt))


@dataclass(slots=True)
class AnthropicProvider(LLMProvider):
    """Anthropic-backed Claude provider."""

    api_key: str
    model: str = SETTINGS.default_llm_model

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield Claude tokens for the provided prompt."""

        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise LLMProviderError("anthropic is not installed in the active environment.") from exc

        client = anthropic.Anthropic(api_key=self.api_key)

        try:
            with client.messages.stream(
                model=self.model,
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as exc:  # pragma: no cover - network/API dependent
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc



def create_provider(api_key: str | None = None) -> LLMProvider:
    """Create the default LLM provider from environment configuration."""

    resolved_api_key = api_key or os.getenv(SETTINGS.anthropic_api_key_env)
    if not resolved_api_key:
        raise LLMProviderError("ANTHROPIC_API_KEY is missing. Add it to your environment or .env file.")

    return AnthropicProvider(api_key=resolved_api_key)


@dataclass(slots=True)
class LocalProvider(LLMProvider):
    """Placeholder for a fully local model backend."""

    model: str = "local"

    def stream(self, prompt: str) -> Iterator[str]:
        """Return a completion from a local runtime."""

        raise LLMProviderError("LocalProvider is not implemented in the scaffold yet.")
