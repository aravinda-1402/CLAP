# CLAP: one-command reproducibility
# Usage: make all (from repo root)

PYTHON ?= python
CONFIG ?= experiments/config.yaml

.PHONY: all build-data run figures paper test smoke clean

all: run paper
	@echo "CLAP full pipeline complete. Outputs: outputs/audit_packets, outputs/figures, outputs/tables, paper/paper.pdf"

build-data:
	$(PYTHON) -m clap build-data --config $(CONFIG)

run:
	$(PYTHON) -m clap run --config $(CONFIG)

figures: run
	@test -d outputs/figures && echo "Figures in outputs/figures"

paper: figures
	@mkdir -p paper/figs
	@cp outputs/figures/*.png outputs/figures/*.svg paper/figs/ 2>/dev/null || true
	cd paper && latexmk -pdf -interaction=nonstopmode main.tex
	@echo "Paper: paper/paper.pdf"

test:
	$(PYTHON) -m pytest tests/ -v

smoke:
	$(PYTHON) -m clap run --config experiments/config_mock.yaml
	@echo "Smoke test (mock) complete."

clean:
	rm -rf outputs/audit_packets/*.json outputs/audit_packets/*.pdf outputs/figures/*.png outputs/figures/*.svg outputs/tables/*.csv outputs/logs/*.log outputs/cache/*
	cd paper && latexmk -C 2>/dev/null || true
