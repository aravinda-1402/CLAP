"""JSON Schema loading and validation for CLAP dataset and outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import jsonschema

# Package root relative to this file
_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "data" / "schema"


def _schema_path(name: str) -> Path:
    return _SCHEMA_DIR / f"{name}.json"


def load_schema(name: str) -> dict[str, Any]:
    """Load a JSON Schema by name (e.g. base_case, family_variant, model_output, audit_packet, suite)."""
    path = _schema_path(name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_base_case(obj: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate object against base_case schema. Raises jsonschema.ValidationError if invalid."""
    schema = schema or load_schema("base_case")
    jsonschema.validate(instance=obj, schema=schema)


def validate_family_variant(obj: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate object against family_variant schema."""
    schema = schema or load_schema("family_variant")
    jsonschema.validate(instance=obj, schema=schema)


def validate_suite_entry(obj: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate object against suite schema."""
    schema = schema or load_schema("suite")
    jsonschema.validate(instance=obj, schema=schema)


def validate_model_output(obj: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate object against model_output schema."""
    schema = schema or load_schema("model_output")
    jsonschema.validate(instance=obj, schema=schema)


def validate_audit_packet(obj: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate object against audit_packet schema."""
    schema = schema or load_schema("audit_packet")
    jsonschema.validate(instance=obj, schema=schema)


def validate_jsonl_file(path: Path, schema_name: str, validator_fn: Callable[[dict, dict], None]) -> list[dict[str, Any]]:
    """Load JSONL and validate each line. Returns list of objects. Raises on first invalid line."""
    schema = load_schema(schema_name)
    objects = []
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.strip().splitlines()):
        if not line.strip():
            continue
        obj = json.loads(line)
        validator_fn(obj, schema)
        objects.append(obj)
    return objects
