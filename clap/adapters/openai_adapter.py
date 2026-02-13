"""
OpenAI-compatible adapter. Only used if API key is set; otherwise skip gracefully.
Requires: openai package (optional dependency).
"""

from __future__ import annotations

import os
from typing import Any

from clap.adapters.base import Adapter, GenerationResult


def _get_client():
    """Lazy import and return OpenAI client if available and key set."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        return None


class OpenAIAdapter(Adapter):
    """OpenAI-compatible API adapter."""

    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None):
        self._model = model
        self._base_url = base_url
        self._client = _get_client()
        if self._client and base_url:
            self._client.base_url = base_url

    @property
    def model_id(self) -> str:
        return "openai"

    @property
    def version(self) -> str:
        return self._model

    def generate(self, case_prompt: str, case_id: str, **kwargs: Any) -> GenerationResult:
        import time
        if not self._client:
            raise RuntimeError("OpenAI client not available; set OPENAI_API_KEY or use mock adapter.")
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are participating in a synthetic clinical evaluation. Respond with valid JSON only."},
                {"role": "user", "content": case_prompt},
            ],
        )
        latency = time.perf_counter() - start
        choice = response.choices[0] if response.choices else None
        text = choice.message.content if choice else ""
        usage = response.usage
        pt = usage.prompt_tokens if usage else 0
        ct = usage.completion_tokens if usage else 0
        return GenerationResult(
            raw_text=text,
            model_id=self.model_id,
            version=self._model,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_seconds=latency,
            from_cache=False,
        )
