#!/usr/bin/env python3
"""Lightweight checks for the public ICE/CBP figure package."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
INPUT_PANEL = PROJECT_DIR / "ice_cbp_file_b_program_activity_object_class_monthly_and_quarterly_2024_01_to_2025_12.csv"

EXPECTED_FILES = [
    PROJECT_DIR / "output" / "figures" / "ice_cbp_intro_obligation_vs_appropriation.png",
    PROJECT_DIR / "output" / "figures" / "ice_cbp_intro_obligation_vs_appropriation.svg",
    PROJECT_DIR / "output" / "figures" / "ice_cbp_intro_obligation_vs_appropriation.meta.json",
    PROJECT_DIR / "output" / "figures" / "ice_cbp_2025_obba_object_class.png",
    PROJECT_DIR / "output" / "figures" / "ice_cbp_2025_obba_object_class.svg",
    PROJECT_DIR / "output" / "figures" / "ice_cbp_2025_obba_object_class.meta.json",
    PROJECT_DIR / "output" / "figures" / "cbp_2025_funding_source_object_class_obligations.png",
    PROJECT_DIR / "output" / "figures" / "cbp_2025_funding_source_object_class_obligations.svg",
    PROJECT_DIR / "output" / "figures" / "cbp_2025_funding_source_object_class_obligations.meta.json",
    PROJECT_DIR / "output" / "figures" / "ice_2025_funding_source_object_class_obligations.png",
    PROJECT_DIR / "output" / "figures" / "ice_2025_funding_source_object_class_obligations.svg",
    PROJECT_DIR / "output" / "figures" / "ice_2025_funding_source_object_class_obligations.meta.json",
    PROJECT_DIR / "output" / "data" / "ice_cbp_intro_obligation_vs_appropriation_chart_data.csv",
    PROJECT_DIR / "output" / "data" / "ice_cbp_2025_funding_source_object_class_obligations_chart_data.csv",
    PROJECT_DIR / "output" / "data" / "ice_cbp_2025_obba_object_class_chart_data.csv",
]

REQUIRED_QUARTERLY_MONTHS = {"2024-12", "2025-03", "2025-06", "2025-09", "2025-12"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def verify_files() -> None:
    missing_or_empty = [path for path in EXPECTED_FILES if not path.exists() or path.stat().st_size == 0]
    if missing_or_empty:
        fail("missing or empty expected files:\n" + "\n".join(f"- {path}" for path in missing_or_empty))

    for path in EXPECTED_FILES:
        if path.suffix == ".png":
            with path.open("rb") as handle:
                if handle.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
                    fail(f"not a valid PNG signature: {path}")


def verify_input_panel() -> None:
    if not INPUT_PANEL.exists() or INPUT_PANEL.stat().st_size == 0:
        fail(f"missing input panel: {INPUT_PANEL}")

    months: set[str] = set()
    agencies: set[str] = set()
    row_count = 0
    with INPUT_PANEL.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_fields = {
            "snapshot_month",
            "submission_scope",
            "snapshot_status",
            "agency",
            "tafs",
            "funding_source",
            "program_activity_name",
            "object_class_name",
            "obligated",
        }
        if reader.fieldnames is None or not required_fields.issubset(reader.fieldnames):
            missing = sorted(required_fields - set(reader.fieldnames or []))
            fail(f"input panel missing fields: {missing}")
        for row in reader:
            row_count += 1
            if row["submission_scope"] == "quarterly" and row["snapshot_status"] == "published snapshot":
                months.add(row["snapshot_month"])
                agencies.add(row["agency"])

    if row_count == 0:
        fail("input panel has zero rows")
    missing_months = REQUIRED_QUARTERLY_MONTHS - months
    if missing_months:
        fail(f"input panel missing required quarterly snapshot months: {sorted(missing_months)}")
    missing_agencies = {"ICE", "CBP"} - agencies
    if missing_agencies:
        fail(f"input panel missing required agencies: {sorted(missing_agencies)}")


def main() -> int:
    verify_files()
    verify_input_panel()
    print("PASS: public figure package files, PNG signatures, and input panel checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
