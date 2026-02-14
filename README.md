# CLAP: Clinical LLM Audit Pack

Release-governance harness for Clinical LLMs: generates a synthetic counterfactual-family dataset, runs multi-model evaluation via pluggable adapters, computes governance metrics and release gates, and produces an **Audit Packet** (JSON + PDF), figures, tables, and an arXiv-ready paper scaffold.

**No PHI. No real patient data. Synthetic only. Evaluation research only-not for clinical use.**

---

## Quickstart

```bash
# From repo root. Use uv (or pip) and Python 3.11+.
uv venv
uv pip install -e ".[dev]"

# One command to reproduce everything:
make all
```

This will: build data → run evaluation (mock by default) → generate audit packets → figures/tables → build paper PDF.

**Exact one command:** `make all`

---

## Outputs

| Location | Contents |
|----------|----------|
| `outputs/audit_packets/` | `audit_packet_*.json`, `audit_packet_*.pdf` |
| `outputs/tables/` | `metrics_summary.csv`, `cfc_by_domain.csv` |
| `outputs/figures/` | CFC, format compliance, NRT, canary leakage (PNG/SVG) |
| `outputs/logs/` | `clap_run.log` |
| `paper/paper.pdf` | Compiled paper (after `make paper`) |

---

## Mock vs real models

- **Mock (default):** No API keys. Uses deterministic `MockAdapter`; good for CI and offline runs. Note: the mock returns generic risk flags, so NRT/CFC gates may FAIL; this is expected and validates that the gating logic runs correctly.
  ```bash
  python -m clap run --config experiments/config_mock.yaml
  ```
- **Real LLM:** Set `adapter: openai` in config and set `OPENAI_API_KEY`. Outputs are cached under `outputs/cache/` by `hash(prompt+model+version)`.

---

## Commands

- `python -m clap run --config experiments/config.yaml` — Full pipeline (data if missing, eval, audit packet, figures, tables).
- `python -m clap build-data --config experiments/config.yaml` — Generate dataset only (`data/cases_base.jsonl`, `data/cases_family.jsonl`, `data/suites/*.jsonl`).
- `make all` — build data, run, figures, paper.
- `make smoke` — quick mock run with small data (`config_mock.yaml`).
- `make test` — run tests.

---

## Reproducibility

- **Seed:** Config key `seed` (default 42); propagated to data generator and mock adapter.
- **Versioning:** Audit packet includes `git_commit_hash` and `config_hash`.
- **Env capture:** Python version, OS, CLI command in packet.
- **Caching:** Model responses cached by prompt+model+version to avoid re-calls.

---

## Checklist (deliverables)

- [x] `data/`: cases_base.jsonl, cases_family.jsonl, suites/nrt100.jsonl, ambiguity.jsonl, policy_conflict.jsonl, schema/
- [x] `outputs/`: audit_packets (JSON + PDF), tables (CSV), figures (PNG/SVG), logs
- [x] `clap` package with `python -m clap run` and `python -m clap build-data`
- [x] `experiments/`: config.yaml, config_mock.yaml, config_schema.json
- [x] `paper/`: main.tex, sections/*.tex, bib.bib, figs/ (filled by make)
- [x] README, LICENSE (Apache-2.0), CITATION.cff
- [x] Tests: schema, JSON repair, metrics, smoke test

---

## Troubleshooting

- **Data not found:** Run `python -m clap build-data --config experiments/config.yaml` first, or run `python -m clap run` (it builds data if missing).
- **Paper does not build:** Ensure `outputs/figures/` has been generated (run `make run` first), then `make paper`. Copy of figures to `paper/figs/` is done by the Makefile.
- **LaTeX missing:** Install TeX Live or MiKTeX; then run `make paper` or `cd paper && latexmk -pdf main.tex`. On Windows without `make`, run the same commands in PowerShell after copying figures: `Copy-Item outputs\figures\* paper\figs\`.
- **OpenAI adapter:** Install `openai` and set `OPENAI_API_KEY`; if not set, runner falls back to mock.

---

## Limitations and ethics

- **Synthetic only:** No real patient data. Do not use for clinical decisions or as medical advice.
- **Mock adapter** is for pipeline validation only; it does not reflect real LLM behavior.
- Canary detection is exact string match; fuzzy leakage may not be caught.
- See `paper/sections/limitations.tex` and `paper/sections/ethics.tex` for more.

---

## What to edit in the paper before submission

1. **Results narrative:** Replace placeholder in `paper/sections/results.tex` with actual numbers and interpretation from your run.
2. **Related work:** Add real citations in `paper/sections/related.tex` and `paper/bib.bib` (do not fabricate).
3. **Figures:** Ensure `make paper` copies `outputs/figures/` to `paper/figs/` and that `results.tex` references them if desired.

---

## License

Apache-2.0. See [LICENSE](LICENSE). Cite via [CITATION.cff](CITATION.cff).
