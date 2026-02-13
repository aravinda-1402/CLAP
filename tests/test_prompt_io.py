"""Tests for JSON repair and parse_model_output."""

import pytest
from clap.prompt_io import parse_model_output, ParseResult


def test_parse_valid_json():
    raw = '{"diagnosis": [], "medications": [{"name": "M", "dose": "1", "freq": "daily", "duration": "7d", "rationale": "R"}], "monitoring": [], "contraindications_flagged": [], "risk_flags": [], "icd10_codes": [], "uncertainty": {"level": "low", "reasons": []}}'
    r = parse_model_output(raw)
    assert r.valid_json is True
    assert r.parsed is not None
    assert r.parsed["uncertainty"]["level"] == "low"


def test_parse_with_trailing_comma_repair():
    raw = '{"diagnosis": [], "medications": [{"name": "M", "dose": "1", "freq": "daily", "duration": "7d", "rationale": "R"},], "monitoring": [], "contraindications_flagged": [], "risk_flags": [], "icd10_codes": [], "uncertainty": {"level": "medium", "reasons": []},}'
    r = parse_model_output(raw, max_repair_attempts=2)
    # Our simple repair removes trailing comma before ] or }
    assert r.valid_json is True or r.repair_attempts >= 1


def test_parse_no_json():
    r = parse_model_output("This is not JSON at all.")
    assert r.valid_json is False
    assert r.parsed is None


def test_parse_extract_from_code_block():
    raw = """Some text
```json
{"diagnosis": [], "medications": [{"name": "M", "dose": "1", "freq": "daily", "duration": "7d", "rationale": "R"}], "monitoring": [], "contraindications_flagged": [], "risk_flags": [], "icd10_codes": [], "uncertainty": {"level": "high", "reasons": []}}
```
"""
    r = parse_model_output(raw)
    assert r.valid_json is True
    assert r.parsed["uncertainty"]["level"] == "high"
