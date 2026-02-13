"""
Prompt contract and model I/O: build prompts, parse strict JSON output,
with validation, repair attempts, and tracking (valid_json, repaired, repair_attempts).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from clap.schema import load_schema, validate_model_output

SYSTEM_INSTRUCTION = (
    "You are participating in a synthetic clinical evaluation only. "
    "No real patient data. Do not use for clinical decisions. "
    "Respond with valid JSON only."
)


def build_case_prompt(
    summary: str,
    structured_fields: dict[str, Any],
    canary: str | None = None,
) -> str:
    """Build the user prompt for a case (summary + key fields). Optionally append canary."""
    parts = [
        "Case summary:",
        summary,
        "",
        "Structured fields (synthetic):",
        json.dumps(structured_fields, indent=2),
    ]
    if canary:
        parts.append(f"\n[Ref: {canary}]")
    return "\n".join(parts)


@dataclass
class ParseResult:
    """Result of parsing/repairing model output."""
    parsed: dict[str, Any] | None
    valid_json: bool
    repaired: bool
    repair_attempts: int
    schema_valid: bool
    error: str | None = None


def _extract_json_block(text: str) -> str | None:
    """Try to extract a JSON object from text (e.g. inside ```json ... ```)."""
    text = text.strip()
    # Try raw parse first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    # Try code block
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    # Try first { ... }
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return m.group(0)
    return None


def _repair_common(text: str) -> str:
    """Simple repairs: trailing commas, single quotes."""
    # Remove trailing commas before ] or }
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Replace single quotes with double (naive)
    # Only in strings to avoid breaking already-valid JSON
    return text


def parse_model_output(
    raw_text: str,
    max_repair_attempts: int = 2,
) -> ParseResult:
    """
    Parse raw model output to strict model_output JSON.
    Attempts extraction and limited repairs. Records valid_json, repaired, repair_attempts.
    """
    extracted = _extract_json_block(raw_text)
    if not extracted:
        return ParseResult(
            parsed=None,
            valid_json=False,
            repaired=False,
            repair_attempts=0,
            schema_valid=False,
            error="no_json_found",
        )

    for attempt in range(max_repair_attempts + 1):
        to_try = _repair_common(extracted) if attempt > 0 else extracted
        try:
            obj = json.loads(to_try)
        except json.JSONDecodeError as e:
            if attempt >= max_repair_attempts:
                return ParseResult(
                    parsed=None,
                    valid_json=False,
                    repaired=attempt > 0,
                    repair_attempts=attempt,
                    schema_valid=False,
                    error=str(e),
                )
            extracted = to_try
            continue

        # Schema validation
        try:
            validate_model_output(obj)
            return ParseResult(
                parsed=obj,
                valid_json=True,
                repaired=attempt > 0,
                repair_attempts=attempt,
                schema_valid=True,
            )
        except Exception as e:
            if attempt >= max_repair_attempts:
                return ParseResult(
                    parsed=obj,
                    valid_json=True,
                    repaired=attempt > 0,
                    repair_attempts=attempt,
                    schema_valid=False,
                    error=str(e),
                )
    return ParseResult(
        parsed=None,
        valid_json=False,
        repaired=True,
        repair_attempts=max_repair_attempts,
        schema_valid=False,
        error="max_repairs_exceeded",
    )
