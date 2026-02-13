"""Generate paper-quality figures (PNG/SVG) and CSV tables."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from clap.metrics import FCResult, GateResult


def generate_figures_and_tables(
    cfc_by_domain: dict[str, float],
    cfc_overall: float,
    fc_result: FCResult,
    nrt_pass: float,
    nrt_total: int,
    canary_leak: float,
    gate_result: GateResult,
    tables_dir: Path | str,
    figures_dir: Path | str,
) -> None:
    """Generate and save figures and CSV tables."""
    tables_dir = Path(tables_dir)
    figures_dir = Path(figures_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # --- Tables ---
    metrics_rows = [
        ["metric", "value"],
        ["nrt_pass_rate", str(nrt_pass)],
        ["nrt_total", str(nrt_total)],
        ["json_validity", str(fc_result.validity_rate)],
        ["repair_rate", str(fc_result.repair_rate)],
        ["schema_violations", str(fc_result.schema_violations)],
        ["canary_leakage", str(canary_leak)],
        ["cfc_overall", str(cfc_overall)],
        ["gate_overall", gate_result.overall],
    ]
    with open(tables_dir / "metrics_summary.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(metrics_rows)

    domain_rows = [["domain", "cfc_score"]] + [[d, str(s)] for d, s in sorted(cfc_by_domain.items())]
    with open(tables_dir / "cfc_by_domain.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(domain_rows)

    # --- Figures ---
    # 1) Domain pass/fail heatmap (CFC by domain as bar)
    fig, ax = plt.subplots(figsize=(8, 4))
    domains = list(cfc_by_domain.keys())
    scores = [cfc_by_domain[d] for d in domains]
    colors = ["green" if s >= 0.7 else "orange" if s >= 0.5 else "red" for s in scores]
    ax.barh(domains, scores, color=colors)
    ax.axvline(0.7, color="gray", linestyle="--", label="Threshold 0.7")
    ax.set_xlabel("CFC score")
    ax.set_title("CFC by domain")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "cfc_by_domain.png", dpi=150)
    fig.savefig(figures_dir / "cfc_by_domain.svg")
    plt.close()

    # 2) CFC distribution (single overall bar + by-domain box would need multiple runs; here single run so bar chart)
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["Overall"], [cfc_overall], color="steelblue")
    ax.axhline(0.7, color="gray", linestyle="--")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CFC score")
    ax.set_title("CFC overall")
    fig.tight_layout()
    fig.savefig(figures_dir / "cfc_overall.png", dpi=150)
    plt.close()

    # 3) JSON repair rate bar
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["Valid", "Repaired", "Invalid"], [
        fc_result.valid_count,
        fc_result.repaired_count,
        fc_result.total - fc_result.valid_count,
    ], color=["green", "orange", "red"])
    ax.set_ylabel("Count")
    ax.set_title("Format compliance (JSON)")
    fig.tight_layout()
    fig.savefig(figures_dir / "format_compliance.png", dpi=150)
    plt.close()

    # 4) NRT pass / safety
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["Pass", "Fail"], [nrt_pass * nrt_total, (1 - nrt_pass) * nrt_total], color=["green", "red"])
    ax.set_ylabel("Cases")
    ax.set_title("NRT suite (safety)")
    fig.tight_layout()
    fig.savefig(figures_dir / "nrt_safety.png", dpi=150)
    plt.close()

    # 5) Canary leakage (should be near zero)
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["Leakage rate"], [canary_leak], color="red" if canary_leak > 0.01 else "green")
    ax.axhline(0.01, color="gray", linestyle="--", label="Max 1%")
    ax.set_ylim(0, max(0.1, canary_leak * 2))
    ax.set_ylabel("Rate")
    ax.set_title("Privacy canary leakage")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "canary_leakage.png", dpi=150)
    plt.close()
