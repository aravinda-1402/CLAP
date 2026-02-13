"""Smoke test: run mock pipeline end-to-end quickly."""

import json
import tempfile
from pathlib import Path

import pytest

from clap.config import load_config
from clap.data_gen import generate_all
from clap.runner import run_evaluation


def test_smoke_mock_pipeline(tmp_path):
    """Run full pipeline with mock adapter and small data; check outputs exist."""
    # Use config_mock with overrides via temp config
    config_path = Path(__file__).resolve().parent.parent / "experiments" / "config_mock.yaml"
    config = load_config(config_path)
    config["data"]["n_base_cases"] = 20
    config["data"]["data_dir"] = str(tmp_path / "data")
    config["data"]["output_dir"] = str(tmp_path / "outputs")
    config["models"]["cache_dir"] = str(tmp_path / "outputs" / "cache")
    config["outputs"] = {
        "audit_dir": str(tmp_path / "outputs" / "audit_packets"),
        "tables_dir": str(tmp_path / "outputs" / "tables"),
        "figures_dir": str(tmp_path / "outputs" / "figures"),
        "logs_dir": str(tmp_path / "outputs" / "logs"),
    }
    tmp_config = tmp_path / "config.yaml"
    import yaml
    with open(tmp_config, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    run_evaluation(str(tmp_config))

    audit_dir = tmp_path / "outputs" / "audit_packets"
    assert audit_dir.exists()
    jsons = list(audit_dir.glob("*.json"))
    pdfs = list(audit_dir.glob("*.pdf"))
    assert len(jsons) >= 1
    assert len(pdfs) >= 1
    packet = json.loads(jsons[0].read_text(encoding="utf-8"))
    assert "metadata" in packet
    assert "gating" in packet
    assert packet["gating"]["overall"] in ("PASS", "FAIL")

    tables_dir = tmp_path / "outputs" / "tables"
    assert (tables_dir / "metrics_summary.csv").exists()
    figures_dir = tmp_path / "outputs" / "figures"
    assert figures_dir.exists()
    assert len(list(figures_dir.glob("*.png"))) >= 1
