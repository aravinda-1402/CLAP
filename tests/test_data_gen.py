"""Dataset generator tests and schema validity of generated data."""

import json
import tempfile
from pathlib import Path

import pytest

from clap.data_gen import generate_all, DOMAINS
from clap.schema import load_schema, validate_base_case, validate_family_variant, validate_suite_entry


def test_generate_all_seeded_reproducible():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)
        b1, v1, s1 = generate_all(42, n_base=20, out_dir=path)
        b2, v2, s2 = generate_all(42, n_base=20, out_dir=path)
        # Same seed -> same first base_id
        assert b1[0]["base_id"] == b2[0]["base_id"]
        assert len(b1) == 20


def test_generated_base_cases_valid():
    bases, _, _ = generate_all(42, n_base=30, out_dir=None)
    schema = load_schema("base_case")
    for b in bases:
        validate_base_case(b, schema)
    domains_seen = {b["domain"] for b in bases}
    assert len(domains_seen) >= 2
    assert all(d in DOMAINS for d in domains_seen)


def test_generated_variants_valid():
    bases, variants, _ = generate_all(42, n_base=25, out_dir=None)
    schema = load_schema("family_variant")
    for v in variants:
        validate_family_variant(v, schema)
    assert len(variants) >= len(bases)


def test_suites_created():
    _, _, suites = generate_all(42, n_base=50, out_dir=None)
    assert "nrt100" in suites
    assert len(suites["nrt100"]) <= 100
    assert "ambiguity" in suites
    assert "policy_conflict" in suites


def test_jsonl_files_written():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)
        generate_all(42, n_base=15, out_dir=path)
        assert (path / "cases_base.jsonl").exists()
        assert (path / "cases_family.jsonl").exists()
        assert (path / "suites" / "nrt100.jsonl").exists()
        lines = (path / "cases_base.jsonl").read_text().strip().splitlines()
        assert len(lines) == 15
        obj = json.loads(lines[0])
        validate_base_case(obj)
