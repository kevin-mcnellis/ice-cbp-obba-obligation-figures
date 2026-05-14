#!/usr/bin/env python3
"""Rebuild and verify the current published `new_post` graphics."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
OUTPUT_DIR = PROJECT_DIR / "output"

COMMANDS = [
    [
        SCRIPTS_DIR / "build_ice_cbp_intro_obligation_vs_appropriation_figure.py",
        "--write-metadata",
    ],
    [
        SCRIPTS_DIR / "build_ice_cbp_funding_source_object_class_sankey.py",
        "--metric",
        "obligations",
        "--write-metadata",
    ],
    [
        SCRIPTS_DIR / "build_ice_cbp_obba_object_class_figure 4.py",
        "--write-metadata",
    ],
]

EXPECTED_OUTPUTS = [
    OUTPUT_DIR / "data" / "ice_cbp_intro_obligation_vs_appropriation_chart_data.csv",
    OUTPUT_DIR / "figures" / "ice_cbp_intro_obligation_vs_appropriation.png",
    OUTPUT_DIR / "figures" / "ice_cbp_intro_obligation_vs_appropriation.svg",
    OUTPUT_DIR / "figures" / "ice_cbp_intro_obligation_vs_appropriation.meta.json",
    OUTPUT_DIR / "data" / "ice_cbp_2025_funding_source_object_class_obligations_chart_data.csv",
    OUTPUT_DIR / "figures" / "ice_2025_funding_source_object_class_obligations.png",
    OUTPUT_DIR / "figures" / "ice_2025_funding_source_object_class_obligations.svg",
    OUTPUT_DIR / "figures" / "ice_2025_funding_source_object_class_obligations.meta.json",
    OUTPUT_DIR / "figures" / "cbp_2025_funding_source_object_class_obligations.png",
    OUTPUT_DIR / "figures" / "cbp_2025_funding_source_object_class_obligations.svg",
    OUTPUT_DIR / "figures" / "cbp_2025_funding_source_object_class_obligations.meta.json",
    OUTPUT_DIR / "data" / "ice_cbp_2025_obba_object_class_chart_data.csv",
    OUTPUT_DIR / "figures" / "ice_cbp_2025_obba_object_class.png",
    OUTPUT_DIR / "figures" / "ice_cbp_2025_obba_object_class.svg",
    OUTPUT_DIR / "figures" / "ice_cbp_2025_obba_object_class.meta.json",
]


def run_command(args: list[Path | str]) -> None:
    command = [sys.executable, "-B", *(str(arg) for arg in args)]
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=PROJECT_DIR, check=True)


def verify_outputs() -> None:
    missing_or_empty = [path for path in EXPECTED_OUTPUTS if not path.exists() or path.stat().st_size == 0]
    if missing_or_empty:
        details = "\n".join(f"- {path}" for path in missing_or_empty)
        raise SystemExit(f"FAIL: missing or empty publication graphics outputs:\n{details}")
    print(f"PASS: verified {len(EXPECTED_OUTPUTS)} non-empty publication graphics outputs.")


def main() -> None:
    for command in COMMANDS:
        run_command(command)
    verify_outputs()


if __name__ == "__main__":
    main()
