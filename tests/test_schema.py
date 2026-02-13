"""Schema validation tests for base case, family variant, suite, model output."""

import json
import pytest
from pathlib import Path

from clap.schema import (
    load_schema,
    validate_base_case,
    validate_family_variant,
    validate_suite_entry,
    validate_model_output,
    validate_audit_packet,
)


def test_load_schema():
    schema = load_schema("base_case")
    assert "properties" in schema
    assert "base_id" in schema["properties"]


def test_validate_base_case_valid():
    case = {
        "base_id": "base_htn_0001",
        "domain": "htn",
        "demographics": {"age_group": "55-64", "sex": "M"},
        "comorbidities": ["hypertension"],
        "meds": [{"name": "lisinopril", "dose": "10mg", "freq": "daily"}],
        "vitals": {"BP_sys": 140},
        "labs": {"Cr": 1.0},
        "allergies": [],
        "pregnancy_flag": False,
        "notes": "Synthetic.",
        "summary": "Synthetic HTN case.",
    }
    validate_base_case(case)


def test_validate_base_case_invalid_domain():
    case = {
        "base_id": "base_x_0001",
        "domain": "invalid_domain",
        "demographics": {"age_group": "55-64", "sex": "M"},
        "comorbidities": [],
        "meds": [],
        "vitals": {},
        "labs": {},
        "allergies": [],
        "pregnancy_flag": False,
        "notes": "",
        "summary": "",
    }
    with pytest.raises(Exception):
        validate_base_case(case)


def test_validate_family_variant_valid():
    v = {
        "variant_id": "var_htn_0001_renal_0",
        "base_id": "base_htn_0001",
        "variant_type": "renal_impairment",
        "expected_change_spec": {"risk_flags_expected": ["renal_dose_adjustment"], "forbidden_changes": []},
        "summary": "Synthetic variant.",
    }
    validate_family_variant(v)


def test_validate_model_output_valid():
    out = {
        "diagnosis": ["Dx"],
        "medications": [{"name": "M", "dose": "1", "freq": "daily", "duration": "7d", "rationale": "R"}],
        "monitoring": [],
        "contraindications_flagged": [],
        "risk_flags": [],
        "icd10_codes": [],
        "uncertainty": {"level": "low", "reasons": []},
    }
    validate_model_output(out)


def test_validate_model_output_invalid_uncertainty_level():
    out = {
        "diagnosis": [],
        "medications": [{"name": "M", "dose": "1", "freq": "daily", "duration": "7d", "rationale": "R"}],
        "monitoring": [],
        "contraindications_flagged": [],
        "risk_flags": [],
        "icd10_codes": [],
        "uncertainty": {"level": "invalid", "reasons": []},
    }
    with pytest.raises(Exception):
        validate_model_output(out)


def test_validate_audit_packet_minimal():
    packet = {
        "metadata": {"timestamp": "2025-01-01T00:00:00Z", "git_commit_hash": "abc", "config_hash": "def", "env_info": {}, "cli_command": ""},
        "gating": {"overall": "PASS", "gate_failures": []},
        "suite_summaries": {},
    }
    validate_audit_packet(packet)
