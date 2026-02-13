"""CLAP model adapters: mock and OpenAI-compatible."""

from clap.adapters.base import Adapter, GenerationResult
from clap.adapters.mock_adapter import MockAdapter
from clap.adapters.cached import CachedAdapter

__all__ = ["Adapter", "GenerationResult", "MockAdapter", "CachedAdapter"]
