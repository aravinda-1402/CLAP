"""Configuration loading and hashing for reproducibility."""

from __future__ import annotations

import hashlib
import os
import platform
import sys
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Load YAML config from path."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_hash(config: dict[str, Any]) -> str:
    """Compute deterministic hash of config (for audit packet)."""
    # Sort keys for reproducibility
    blob = yaml.dump(config, default_flow_style=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def get_env_info() -> dict[str, str]:
    """Capture environment for audit packet."""
    return {
        "python_version": sys.version.split()[0],
        "os": platform.system(),
        "os_release": platform.release(),
    }
