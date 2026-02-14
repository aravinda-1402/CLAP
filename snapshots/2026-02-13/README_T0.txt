T0 baseline snapshot — immutable evidence
==========================================
Date/time: 2026-02-13 (run completed 2026-02-14 00:41:39 UTC)
Model: GPT-4.1-mini (OpenAI)
Config: experiments/config.yaml (copied as config.yaml)
Git commit hash: 423f866aae1c2ff54c909cbc2f08dd3716eb97dc
Config hash: fdd134028f3d6d52

Key metrics (T0 — real model only, no mock)
-------------------------------------------
Overall gate: FAIL
NRT pass rate: 0.25 (25% — 25/100 cases passed)
CFC overall: 0.1663
JSON validity: 1.0 (100%)
Repair rate: 1.0 (100%)
Schema violations: 0
Canary leakage: 0.0

Gate failures: nrt_pass_rate 0.25 < 1.0; cfc_overall 0.1663 < 0.7

CFC by domain: anticoagulation 0.145, asthma_copd 0.167, chf 0.167, ckd_dosing 0.207, diabetes 0.173, htn 0.187, infection_antibiotics 0.14, pain_opioids 0.12, pregnancy_meds 0.13, thyroid 0.245

Top 5 NRT failure examples (case_id, expected_risk_flags):
  nrt_000: renal_dose_adjustment, eGFR_low
  nrt_001: allergy_flagged
  nrt_002: renal_dose_adjustment, eGFR_low
  nrt_003: drug_interaction
  nrt_004: renal_dose_adjustment, eGFR_low

Paper: Build paper.pdf locally with: cd paper && latexmk -pdf main.tex
(Figures are in paper/figs/; results.tex and methods.tex updated with T0 metrics.)
