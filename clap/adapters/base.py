"""Adapter interface: generate(case_prompt) -> raw text."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class GenerationResult:
    """Raw model output plus metadata."""
    raw_text: str
    model_id: str
    version: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_seconds: float = 0.0
    from_cache: bool = False


class Adapter(ABC):
    """Interface for model adapters."""

    @abstractmethod
    def generate(self, case_prompt: str, case_id: str, **kwargs: Any) -> GenerationResult:
        """Return raw text response for the given prompt. case_id used for caching key."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...
