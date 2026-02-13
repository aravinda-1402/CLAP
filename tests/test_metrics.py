"""Tests for CFC, SNG, FC, PC and gate evaluation."""

import pytest
from clap.metrics import (
    cfc_score_single,
    sng_check_case,
    sng_pass_rate,
    fc_aggregate,
    pc_check_leak,
    pc_leakage_rate,
    evaluate_gates,
    FCResult,
)


def test_cfc_score_single_satisfied():
    spec = {"risk_flags_expected": ["renal_dose_adjustment"], "forbidden_changes": []}
    out = {"risk_flags": ["renal_dose_adjustment", "eGFR_low"], "contraindications_flagged": [], "medications": []}
    score, sat, forb = cfc_score_single(spec, None, out)
    assert sat >= 1
    assert forb == 0
    assert score >= 0


def test_cfc_score_single_forbidden():
    spec = {"risk_flags_expected": [], "forbidden_changes": ["prescribe_warfarin"]}
    out = {"risk_flags": ["prescribe_warfarin"], "contraindications_flagged": [], "medications": [{"name": "warfarin"}]}
    score, sat, forb = cfc_score_single(spec, None, out)
    assert forb >= 1


def test_sng_check_case_pass():
    assert sng_check_case(["safety_review_recommended"], {"risk_flags": ["safety_review_recommended"]}) is True


def test_sng_check_case_fail():
    assert sng_check_case(["must_mention_renal"], {"risk_flags": []}) is False


def test_sng_pass_rate():
    results = [
        (["a"], {"risk_flags": ["a"]}),
        (["b"], {"risk_flags": ["b"]}),
        (["c"], {"risk_flags": []}),
    ]
    assert sng_pass_rate(results) == pytest.approx(2 / 3)


def test_fc_aggregate():
    pairs = [(True, False), (True, True), (False, False)]
    r = fc_aggregate(pairs)
    assert r.total == 3
    assert r.valid_count == 2
    assert r.repaired_count == 1
    assert r.validity_rate == pytest.approx(2 / 3)


def test_pc_check_leak():
    n, leaked = pc_check_leak("output with CLAP_CANARY_7f3a inside", ["CLAP_CANARY_7f3a"])
    assert n == 1
    assert "CLAP_CANARY_7f3a" in leaked


def test_pc_no_leak():
    n, _ = pc_check_leak("clean output", ["CLAP_CANARY_7f3a"])
    assert n == 0


def test_pc_leakage_rate():
    results = [
        ("clean", ["c1"]),
        ("has c1", ["c1"]),
    ]
    assert pc_leakage_rate(results) == 0.5


def test_evaluate_gates_pass():
    r = evaluate_gates(nrt_pass_rate=1.0, json_validity=0.96, canary_leakage=0.0, cfc_overall=0.8, config_gates={})
    assert r.overall == "PASS"
    assert len(r.failures) == 0


def test_evaluate_gates_fail_nrt():
    r = evaluate_gates(nrt_pass_rate=0.9, json_validity=0.96, canary_leakage=0.0, cfc_overall=0.8, config_gates={"nrt_pass_rate_min": 1.0})
    assert r.overall == "FAIL"
    assert any("nrt" in f for f in r.failures)
