"""
End-to-end runner: load config, build data if needed, run evaluation,
compute metrics, apply gates, build audit packet (JSON + PDF), figures/tables.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from clap.config import config_hash, get_env_info, load_config
from clap.data_gen import generate_all
from clap.prompt_io import ParseResult, build_case_prompt, parse_model_output
from clap.schema import load_schema, validate_base_case, validate_family_variant
from clap.metrics import (
    cfc_aggregate,
    fc_aggregate,
    evaluate_gates,
    pc_leakage_rate,
    sng_check_case,
    sng_pass_rate,
)
from clap.adapters import MockAdapter, CachedAdapter

# Optional: OpenAI adapter (only if available)
try:
    from clap.adapters.openai_adapter import OpenAIAdapter
except ImportError:
    OpenAIAdapter = None

from clap.audit_packet import build_audit_packet_json, build_audit_packet_pdf
from clap.figures_tables import generate_figures_and_tables

logger = logging.getLogger("clap.runner")


def _get_git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.strip()[:16]
    except Exception:
        pass
    return "unknown"


def _resolve_adapter(config: dict[str, Any]):
    models = config.get("models", {})
    adapter_name = models.get("adapter", "mock")
    seed = config.get("seed", 42)
    version = models.get("mock_version", "v1")
    cache_dir = models.get("cache_dir", "outputs/cache")
    cache_enabled = models.get("cache_enabled", True)

    if adapter_name == "mock":
        inner = MockAdapter(seed=seed, version=version)
    elif adapter_name == "openai" and OpenAIAdapter is not None:
        inner = OpenAIAdapter(
            model=models.get("openai_model", "gpt-4o-mini"),
            base_url=models.get("openai_base_url"),
        )
    else:
        if adapter_name == "openai":
            logger.warning("OpenAI adapter requested but not available; using mock.")
        inner = MockAdapter(seed=seed, version=version)

    return CachedAdapter(inner, cache_dir=cache_dir, enabled=cache_enabled)


def _load_cases(data_dir: Path) -> tuple[list[dict], list[dict], dict[str, list[dict]]]:
    base_path = data_dir / "cases_base.jsonl"
    family_path = data_dir / "cases_family.jsonl"
    if not base_path.exists() or not family_path.exists():
        raise FileNotFoundError(f"Data not found. Run build-data first: {data_dir}")
    bases = [json.loads(line) for line in base_path.read_text().strip().splitlines() if line]
    variants = [json.loads(line) for line in family_path.read_text().strip().splitlines() if line]
    suites = {}
    for name in ["nrt100", "ambiguity", "policy_conflict"]:
        p = data_dir / "suites" / f"{name}.jsonl"
        if p.exists():
            suites[name] = [json.loads(l) for l in p.read_text().strip().splitlines() if l]
    return bases, variants, suites


def run_evaluation(config_path: str | Path) -> dict[str, Any]:
    """
    Full pipeline: load config, ensure data exists, run model on cases,
    compute metrics, gates, audit packet, figures/tables. Returns audit packet dict.
    """
    config = load_config(config_path)
    seed = config.get("seed", 42)
    data_dir = Path(config["data"]["data_dir"])
    out_dir = Path(config["data"]["output_dir"])
    outputs = config.get("outputs", {})
    audit_dir = Path(outputs.get("audit_dir", out_dir / "audit_packets"))
    tables_dir = Path(outputs.get("tables_dir", out_dir / "tables"))
    figures_dir = Path(outputs.get("figures_dir", out_dir / "figures"))
    logs_dir = Path(outputs.get("logs_dir", out_dir / "logs"))
    canaries = config.get("canaries", [])

    for d in [audit_dir, tables_dir, figures_dir, logs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Structured logging
    log_file = logs_dir / "clap_run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Ensure data exists
    if not (data_dir / "cases_base.jsonl").exists():
        logger.info("Building dataset...")
        generate_all(seed, config["data"].get("n_base_cases", 250), data_dir)

    bases, variants, suites = _load_cases(data_dir)
    adapter = _resolve_adapter(config)
    base_schema = load_schema("base_case")
    var_schema = load_schema("family_variant")

    # Build base_id -> base, variant_id -> variant, base_id -> domain
    base_by_id = {b["base_id"]: b for b in bases}
    var_by_id = {v["variant_id"]: v for v in variants}
    domain_by_base = {b["base_id"]: b["domain"] for b in bases}
    domain_by_var = {v["variant_id"]: domain_by_base.get(v["base_id"], "unknown") for v in variants}

    # Case list: all base + variant IDs we will run
    case_ids = [b["base_id"] for b in bases]
    for v in variants:
        case_ids.append(v["variant_id"])

    # Run model and parse
    parse_results: dict[str, ParseResult] = {}
    raw_outputs: dict[str, str] = {}
    canary_by_case: dict[str, list[str]] = {}
    for i, cid in enumerate(case_ids):
        if cid in base_by_id:
            case = base_by_id[cid]
            summary = case["summary"]
            structured = {k: v for k, v in case.items() if k != "summary"}
        else:
            case = var_by_id.get(cid)
            if not case:
                continue
            summary = case["summary"]
            structured = {"variant_id": cid, "base_id": case["base_id"], "expected_change_spec": case.get("expected_change_spec", {})}
        canary = canaries[i % len(canaries)] if canaries else None
        canary_by_case[cid] = [canary] if canary else []
        prompt = build_case_prompt(summary, structured, canary)
        result = adapter.generate(prompt, case_id=cid)
        raw_outputs[cid] = result.raw_text
        parse_results[cid] = parse_model_output(result.raw_text)

    # NRT suite evaluation
    nrt_cases = suites.get("nrt100", [])
    nrt_results = []
    for s in nrt_cases:
        case_id = s.get("base_id_or_variant_id")
        expected = s.get("expected_risk_flags") or ["safety_review_recommended"]
        out = None
        if case_id in parse_results and parse_results[case_id].parsed:
            out = parse_results[case_id].parsed
        nrt_results.append((expected, out))
    nrt_pass = sng_pass_rate(nrt_results)

    # FC
    fc_inputs = [(r.valid_json, r.repaired) for r in parse_results.values()]
    fc_result = fc_aggregate(fc_inputs)

    # PC
    pc_inputs = [(raw_outputs.get(cid, ""), canary_by_case.get(cid, [])) for cid in parse_results]
    canary_leak = pc_leakage_rate(pc_inputs)

    # CFC: need base+variant pairs
    family_results = []
    for v in variants:
        base_id = v["base_id"]
        var_id = v["variant_id"]
        base_out = parse_results[base_id].parsed if base_id in parse_results else None
        var_out = parse_results[var_id].parsed if var_id in parse_results else None
        family_results.append((v, base_out, var_out))
    domain_index = {**domain_by_base, **domain_by_var}
    cfc_by_domain, cfc_overall = cfc_aggregate(family_results, domain_index)

    # Gates
    gates_config = config.get("gates", {})
    gate_result = evaluate_gates(
        nrt_pass_rate=nrt_pass,
        json_validity=fc_result.validity_rate,
        canary_leakage=canary_leak,
        cfc_overall=cfc_overall,
        config_gates=gates_config,
    )

    # Audit packet
    env_info = get_env_info()
    env_info["cli_command"] = " ".join(sys.argv)
    # Figures and tables first (so packet can reference them)
    generate_figures_and_tables(
        cfc_by_domain=cfc_by_domain,
        cfc_overall=cfc_overall,
        fc_result=fc_result,
        nrt_pass=nrt_pass,
        nrt_total=len(nrt_cases),
        canary_leak=canary_leak,
        gate_result=gate_result,
        tables_dir=tables_dir,
        figures_dir=figures_dir,
    )

    # Audit packet (after figures so figure_refs exist)
    packet = build_audit_packet_json(
        config=config,
        config_hash=config_hash(config),
        git_commit=_get_git_commit(),
        env_info=env_info,
        nrt_pass_rate=nrt_pass,
        fc_result=fc_result,
        canary_leakage=canary_leak,
        cfc_by_domain=cfc_by_domain,
        cfc_overall=cfc_overall,
        gate_result=gate_result,
        nrt_failures=[(nrt_cases[i].get("case_id"), nrt_cases[i].get("expected_risk_flags"), nrt_results[i][1]) for i in range(len(nrt_cases)) if not sng_check_case(nrt_results[i][0], nrt_results[i][1])],
        parse_results=parse_results,
        raw_outputs=raw_outputs,
        canaries=canaries,
    )

    audit_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{adapter.model_id}_{adapter.version}"
    packet_path = audit_dir / f"audit_packet_{run_id}.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    logger.info("Wrote audit packet JSON: %s", packet_path)

    pdf_path = audit_dir / f"audit_packet_{run_id}.pdf"
    build_audit_packet_pdf(packet, str(pdf_path), figures_dir)
    logger.info("Wrote audit packet PDF: %s", pdf_path)

    return packet
