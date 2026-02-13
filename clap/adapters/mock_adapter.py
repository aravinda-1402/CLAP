"""
Mock adapter: deterministic, seeded, returns plausible structured JSON.
Supports multiple versions to simulate regression (e.g. v1 baseline vs v2 candidate).
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any

from clap.adapters.base import Adapter, GenerationResult


def _make_plausible_output(seed: int, case_id: str, version: str) -> dict[str, Any]:
    """Generate deterministic plausible model_output JSON."""
    # Deterministic seed from case_id and version (hash() is not cross-run stable)
    seed_bytes = f"{seed}_{case_id}_{version}".encode()
    seed_int = int(hashlib.sha256(seed_bytes).hexdigest()[:8], 16)
    rng = random.Random(seed_int)

    level = rng.choice(["low", "medium", "high"])
    reasons = ["Synthetic evaluation response."]
    if level != "low":
        reasons.append("Insufficient information in case.")

    return {
        "diagnosis": ["Synthetic diagnosis for evaluation only."],
        "medications": [
            {
                "name": "synthetic_med",
                "dose": "as per protocol",
                "freq": "daily",
                "duration": "evaluation only",
                "rationale": "Synthetic response.",
            }
        ],
        "monitoring": ["Routine monitoring per synthetic protocol."],
        "contraindications_flagged": ["None in synthetic case."],
        "risk_flags": ["safety_review_recommended", "synthetic_case"],
        "icd10_codes": ["Z00.00"],
        "uncertainty": {"level": level, "reasons": reasons},
    }


class MockAdapter(Adapter):
    """Deterministic mock that returns valid model_output JSON."""

    def __init__(self, seed: int = 42, version: str = "v1"):
        self._seed = seed
        self._version = version
        self._model_id = "mock"

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def version(self) -> str:
        return self._version

    def generate(self, case_prompt: str, case_id: str, **kwargs: Any) -> GenerationResult:
        out = _make_plausible_output(self._seed, case_id, self._version)
        raw_text = json.dumps(out, indent=2)
        # Deterministic token proxy
        n = len(raw_text) // 4
        return GenerationResult(
            raw_text=raw_text,
            model_id=self._model_id,
            version=self._version,
            prompt_tokens=len(case_prompt) // 4,
            completion_tokens=n,
            latency_seconds=0.01,
            from_cache=False,
        )
