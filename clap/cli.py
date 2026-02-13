"""CLAP CLI: run, build-data, etc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _config_path(s: str) -> Path:
    p = Path(s)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    return p


def cmd_build_data(args: argparse.Namespace) -> int:
    """Generate dataset only."""
    from clap.config import load_config
    from clap.data_gen import generate_all

    config = load_config(args.config)
    seed = config.get("seed", 42)
    n = config["data"].get("n_base_cases", 250)
    data_dir = Path(config["data"]["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "suites").mkdir(parents=True, exist_ok=True)
    generate_all(seed, n, data_dir)
    print(f"Generated data in {data_dir}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Full pipeline: data (if missing), eval, audit packet, figures, tables."""
    from clap.runner import run_evaluation

    run_evaluation(args.config)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="clap", description="CLAP: Clinical LLM Audit Pack")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run full evaluation pipeline")
    run_p.add_argument("--config", type=_config_path, default="experiments/config.yaml", help="Config YAML")
    run_p.set_defaults(func=cmd_run)

    build_p = sub.add_parser("build-data", help="Generate synthetic dataset only")
    build_p.add_argument("--config", type=_config_path, default="experiments/config.yaml", help="Config YAML")
    build_p.set_defaults(func=cmd_build_data)

    args = parser.parse_args()
    func = getattr(args, "func", None)
    if not func:
        parser.print_help()
        return 1
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
