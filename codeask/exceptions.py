"""Custom exceptions for CodeAsk."""

from __future__ import annotations


class CodeAskError(Exception):
    """Base exception for CodeAsk failures."""


class RepositoryNotIndexedError(CodeAskError):
    """Raised when a user queries a repository that has not been indexed."""


class ConfigurationError(CodeAskError):
    """Raised when the runtime configuration is invalid or incomplete."""


class MetadataError(CodeAskError):
    """Raised when metadata cannot be read or written safely."""


class LLMProviderError(CodeAskError):
    """Raised when an LLM provider cannot satisfy a request."""
