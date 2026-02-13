"""Build audit packet as JSON and PDF (ReportLab)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clap.metrics import FCResult, GateResult


def _redact_canaries(text: str, canaries: list[str]) -> str:
    for c in canaries:
        text = text.replace(c, "[REDACTED]")
    return text


def build_audit_packet_json(
    config: dict[str, Any],
    config_hash: str,
    git_commit: str,
    env_info: dict[str, str],
    nrt_pass_rate: float,
    fc_result: FCResult,
    canary_leakage: float,
    cfc_by_domain: dict[str, float],
    cfc_overall: float,
    gate_result: GateResult,
    nrt_failures: list[tuple[str, list, Any]],
    parse_results: dict[str, Any],
    raw_outputs: dict[str, str],
    canaries: list[str],
) -> dict[str, Any]:
    """Build full audit packet dict (metadata, gating, suite summaries, worst failures, refs)."""
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit_hash": git_commit,
        "config_hash": config_hash,
        "env_info": env_info,
        "cli_command": env_info.get("cli_command", ""),
    }
    gating = {
        "overall": gate_result.overall,
        "gate_failures": gate_result.failures,
    }
    suite_summaries = {
        "nrt100": {"pass_rate": nrt_pass_rate, "description": "Safety non-regression"},
        "format_compliance": {
            "validity_rate": fc_result.validity_rate,
            "repair_rate": fc_result.repair_rate,
            "schema_violations": fc_result.schema_violations,
        },
        "canary_leakage": canary_leakage,
        "cfc": {"by_domain": cfc_by_domain, "overall": cfc_overall},
    }
    worst_failures = []
    for case_id, expected, observed in nrt_failures[:20]:
        obs_redacted = None
        if observed and isinstance(observed, dict):
            obs_redacted = json.dumps(observed)[:500]
            if canaries:
                obs_redacted = _redact_canaries(obs_redacted, canaries)
        worst_failures.append({
            "case_id": case_id,
            "expected_risk_flags": expected,
            "observed_summary": obs_redacted,
        })

    figures_dir = Path(config.get("outputs", {}).get("figures_dir", "outputs/figures"))
    tables_dir = Path(config.get("outputs", {}).get("tables_dir", "outputs/tables"))
    figure_refs = list(figures_dir.glob("*.png")) + list(figures_dir.glob("*.svg"))
    table_refs = list(tables_dir.glob("*.csv"))

    return {
        "metadata": metadata,
        "gating": gating,
        "suite_summaries": suite_summaries,
        "domain_breakdown": cfc_by_domain,
        "worst_failures": worst_failures,
        "figure_refs": [str(p) for p in figure_refs],
        "table_refs": [str(p) for p in table_refs],
    }


def build_audit_packet_pdf(packet: dict[str, Any], out_path: str, figures_dir: Path) -> None:
    """Generate PDF report using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

    doc = SimpleDocTemplate(out_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("CLAP Audit Packet", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))
    meta = packet.get("metadata", {})
    story.append(Paragraph(f"Timestamp: {meta.get('timestamp', 'N/A')}", styles["Normal"]))
    story.append(Paragraph(f"Config hash: {meta.get('config_hash', 'N/A')}", styles["Normal"]))
    story.append(Paragraph(f"Git commit: {meta.get('git_commit_hash', 'N/A')}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # PASS/FAIL box
    gating = packet.get("gating", {})
    overall = gating.get("overall", "UNKNOWN")
    color = colors.green if overall == "PASS" else colors.red
    story.append(Paragraph(f"<b>Overall: {overall}</b>", ParagraphStyle(name="Gate", textColor=color, fontSize=14)))
    failures = gating.get("gate_failures", [])
    if failures:
        for f in failures:
            story.append(Paragraph(f"• {f}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Suite summaries table
    sums = packet.get("suite_summaries", {})
    data = [["Metric", "Value"]]
    if "nrt100" in sums:
        data.append(["NRT pass rate", f"{sums['nrt100'].get('pass_rate', 0):.2%}"])
    if "format_compliance" in sums:
        fc = sums["format_compliance"]
        data.append(["JSON validity", f"{fc.get('validity_rate', 0):.2%}"])
        data.append(["Repair rate", f"{fc.get('repair_rate', 0):.2%}"])
    if "canary_leakage" in sums:
        data.append(["Canary leakage", f"{sums['canary_leakage']:.2%}"])
    if "cfc" in sums:
        data.append(["CFC overall", f"{sums['cfc'].get('overall', 0):.2f}"])
    t = Table(data, colWidths=[2.5 * inch, 3 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke)]))
    story.append(t)
    story.append(Spacer(1, 0.3 * inch))

    # Worst failures
    story.append(Paragraph("Top failures (NRT)", styles["Heading2"]))
    for w in packet.get("worst_failures", [])[:10]:
        story.append(Paragraph(f"Case: {w.get('case_id', '')}", styles["Normal"]))
        story.append(Paragraph(f"Expected flags: {w.get('expected_risk_flags', [])}", styles["Normal"]))
        story.append(Spacer(1, 0.1 * inch))
    story.append(Spacer(1, 0.2 * inch))

    # Figures (embed if exist)
    figs = packet.get("figure_refs", [])
    for ref in figs[:5]:
        p = Path(ref)
        if p.exists():
            try:
                img = Image(str(p), width=5 * inch, height=3 * inch)
                story.append(img)
                story.append(Spacer(1, 0.2 * inch))
            except Exception:
                story.append(Paragraph(f"[Figure: {p.name}]", styles["Normal"]))

    # Limitations / disclaimer
    story.append(PageBreak())
    story.append(Paragraph("Limitations & Ethical Disclaimer", styles["Heading2"]))
    story.append(Paragraph(
        "This audit packet is generated from synthetic data only. No real patient data (PHI) is used. "
        "CLAP is for evaluation and release governance research only; it must not be used for clinical decision-making "
        "or as medical advice. All case identifiers and demographics are synthetic.",
        styles["Normal"],
    ))

    doc.build(story)
