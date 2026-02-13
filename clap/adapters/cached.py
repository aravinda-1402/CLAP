"""Cache layer: store/load by hash(prompt + model_id + version)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clap.adapters.base import Adapter, GenerationResult


def _cache_key(prompt: str, model_id: str, version: str) -> str:
    h = hashlib.sha256(f"{prompt}|{model_id}|{version}".encode()).hexdigest()[:32]
    return h


class CachedAdapter(Adapter):
    """Wraps an adapter and caches results to disk by (prompt, model_id, version)."""

    def __init__(self, inner: Adapter, cache_dir: str | Path, enabled: bool = True):
        self._inner = inner
        self._cache_dir = Path(cache_dir)
        self._enabled = enabled
        if self._enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def version(self) -> str:
        return self._inner.version

    def _path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def generate(self, case_prompt: str, case_id: str, **kwargs: Any) -> GenerationResult:
        key = _cache_key(case_prompt, self.model_id, self.version)
        path = self._path(key)

        if self._enabled and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return GenerationResult(
                raw_text=data["raw_text"],
                model_id=data["model_id"],
                version=data["version"],
                prompt_tokens=data.get("prompt_tokens", 0),
                completion_tokens=data.get("completion_tokens", 0),
                latency_seconds=data.get("latency_seconds", 0),
                from_cache=True,
            )

        result = self._inner.generate(case_prompt, case_id=case_id, **kwargs)
        if self._enabled:
            payload = {
                "raw_text": result.raw_text,
                "model_id": result.model_id,
                "version": result.version,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "latency_seconds": result.latency_seconds,
            }
            path.write_text(json.dumps(payload, indent=0), encoding="utf-8")
        return result
