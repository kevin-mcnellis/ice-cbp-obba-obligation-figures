#!/usr/bin/env python3
"""Build a calendar-year 2025 OBBA obligation-by-object-class figure for ICE and CBP."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from object_class_bridge import obba_display_label, project_object_class_name
from special_graphics_tafs import (
    CBP_SEC_90002_FACILITIES_NOTE,
    include_in_obba_graphics,
)

DEFAULT_INPUT = PROJECT_DIR / "ice_cbp_file_b_program_activity_object_class_monthly_and_quarterly_2024_01_to_2025_12.csv"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output"
CACHE_ROOT = PROJECT_DIR / "tmp"
QUARTERLY_SCOPE = "quarterly"
PRIOR_QUARTER_END_MONTH = "2024-12"
TOP_N = 10
MIN_DISPLAY_AMOUNT = 100_000_000
X_AXIS_MAX = 9_500_000_000
BORDER_COLOR = "#000000"
BORDER_LINEWIDTH = 1.6
BORDER_INSET = 0.002
AGENCY_COLORS = {
    "ICE": "#1f4e79",
    "CBP": "#2a9d8f",
}
AGENCY_ORDER = ["CBP", "ICE"]
TITLE_TEXT = "How CBP and ICE Obligated OBBA Funds in Calendar Year 2025"
X_AXIS_LABEL = "Calendar-Year 2025 OBBA obligations"
FOOTER_TEXT = "\n".join(
    [
        textwrap.fill(
            "Notes: Only categories with at least $100 million in calendar-year 2025 OBBA obligations are shown; smaller categories are omitted.",
            width=145,
        ),
        textwrap.fill(
            "Calendar-year 2025 totals are derived from cumulative quarter-end File B snapshots by differencing Mar. 31, Jun. 30, and Sep. 30 against the prior quarter and then adding Dec. 31, 2025. Source: USAspending.gov File B.",
            width=145,
        ),
    ]
)

for cache_dir in (CACHE_ROOT, CACHE_ROOT / "mplconfig", CACHE_ROOT / "xdg-cache"):
    cache_dir.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_ROOT / "mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_ROOT / "xdg-cache"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter, MultipleLocator
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--write-metadata",
        action="store_true",
        help="Write deterministic sidecar metadata JSON files for rendered figures.",
    )
    return parser.parse_args()


def ensure_output_dirs(output_dir: Path) -> tuple[Path, Path]:
    figure_dir = output_dir / "figures"
    data_dir = output_dir / "data"
    figure_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    return figure_dir, data_dir


def sanitize_png_output(path: Path) -> None:
    temp_path = path.with_suffix(".clean.png")
    with Image.open(path) as image:
        image.save(temp_path, format="PNG", optimize=False)
    os.replace(temp_path, path)
    try:
        os.removexattr(path, "com.apple.quarantine")
    except (AttributeError, OSError):
        pass


def write_figure_metadata(output_png: Path) -> Path:
    metadata_path = output_png.with_suffix(".meta.json")
    payload = {
        "title": TITLE_TEXT,
        "axis_labels": {"x": X_AXIS_LABEL, "y": ""},
        "footer_text": FOOTER_TEXT,
        "panel_order": AGENCY_ORDER,
    }
    metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return metadata_path


def wrap_label(text: str, width: int = 28) -> str:
    return "\n".join(textwrap.wrap(text, width=width)) if len(text) > width else text


def format_csv_number(value: float) -> str:
    return f"{value:.2f}"


def format_billions_axis(value: float, _pos: int) -> str:
    return f"${value / 1_000_000_000:.0f}B"


def format_millions_label(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    return f"${value / 1_000_000:.0f}M"


def normalize_object_class(object_class: str) -> str:
    return project_object_class_name(object_class)


def display_object_class(object_class: str) -> str:
    return obba_display_label(object_class)


def cy2025_total_from_quarter_ends(
    cumulative_values: dict[tuple[str, str, str], float],
    agency: str,
    object_class: str,
) -> float:
    dec_2024 = cumulative_values.get((agency, object_class, PRIOR_QUARTER_END_MONTH), 0.0)
    mar_2025 = cumulative_values.get((agency, object_class, "2025-03"), 0.0)
    jun_2025 = cumulative_values.get((agency, object_class, "2025-06"), 0.0)
    sep_2025 = cumulative_values.get((agency, object_class, "2025-09"), 0.0)
    dec_2025 = cumulative_values.get((agency, object_class, "2025-12"), 0.0)

    return (
        (mar_2025 - dec_2024)
        + (jun_2025 - mar_2025)
        + (sep_2025 - jun_2025)
        + dec_2025
    )


def build_object_class_rows(path: Path) -> dict[str, list[dict[str, object]]]:
    cumulative_values = defaultdict(float)

    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["submission_scope"] != QUARTERLY_SCOPE or row["snapshot_status"] != "published snapshot":
                continue
            if not include_in_obba_graphics(row):
                continue
            agency = row["agency"]
            if agency not in AGENCY_ORDER:
                continue
            object_class = normalize_object_class(row["object_class_name"] or "Unknown")
            cumulative_values[(agency, object_class, row["snapshot_month"])] += float(row["obligated"] or 0)

    by_class = defaultdict(lambda: defaultdict(float))
    series_keys = {(agency, object_class) for agency, object_class, _month in cumulative_values}
    for agency, object_class in series_keys:
        total_2025 = cy2025_total_from_quarter_ends(cumulative_values, agency, object_class)
        if total_2025 <= 0:
            continue
        by_class[object_class][agency] += total_2025

    rows_by_agency: dict[str, list[dict[str, object]]] = {}
    for agency in AGENCY_ORDER:
        agency_rows: list[dict[str, object]] = []
        for object_class, values in by_class.items():
            amount = values[agency]
            if amount < MIN_DISPLAY_AMOUNT:
                continue
            agency_rows.append(
                {
                    "object_class_name": object_class,
                    "agency": agency,
                    "amount": amount,
                }
            )
        agency_rows.sort(key=lambda row: row["amount"], reverse=True)
        if len(agency_rows) > TOP_N:
            tail = agency_rows[TOP_N:]
            agency_rows = agency_rows[:TOP_N]
            agency_rows.append(
                {
                    "object_class_name": "All other object classes",
                    "agency": agency,
                    "amount": sum(float(row["amount"]) for row in tail),
                }
            )
        rows_by_agency[agency] = agency_rows

    return rows_by_agency


def write_chart_data(output_path: Path, rows_by_agency: dict[str, list[dict[str, object]]]) -> None:
    fieldnames = ["object_class_name", "agency", "amount", "snapshot_month", "note"]
    note = (
        "Calendar-year 2025 OBBA obligations derived from cumulative quarter-end File B snapshots: "
        "Mar. 31, 2025 minus Dec. 31, 2024; Jun. 30 minus Mar. 31; Sep. 30 minus Jun. 30; plus Dec. 31, 2025. "
        + CBP_SEC_90002_FACILITIES_NOTE
    )
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for agency in AGENCY_ORDER:
            for row in rows_by_agency[agency]:
                writer.writerow(
                    {
                        "object_class_name": row["object_class_name"],
                        "agency": agency,
                        "amount": format_csv_number(float(row["amount"])),
                        "snapshot_month": "2025",
                        "note": note,
                    }
                )


def draw_figure(rows_by_agency: dict[str, list[dict[str, object]]], output_png: Path, output_svg: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 1, figsize=(12.8, 10.2), sharex=True)
    fig.patch.set_facecolor("white")

    max_amount = 0.0
    for agency in AGENCY_ORDER:
        max_amount = max(
            max_amount,
            max((float(row["amount"]) for row in rows_by_agency[agency]), default=0.0),
        )

    for ax, agency in zip(axes, AGENCY_ORDER):
        rows = rows_by_agency[agency]
        labels = [wrap_label(display_object_class(str(row["object_class_name"]))) for row in rows]
        y_positions = list(range(len(rows)))
        amounts = [float(row["amount"]) for row in rows]

        ax.barh(
            y_positions,
            amounts,
            color=AGENCY_COLORS[agency],
            edgecolor="white",
            linewidth=0.6,
        )

        for index, amount in enumerate(amounts):
            ax.text(
                amount + max_amount * 0.015,
                y_positions[index],
                format_millions_label(amount),
                va="center",
                ha="left",
                fontsize=10.5,
                color="#1b1f23",
                fontweight="bold",
            )

        ax.text(
            0.0,
            1.02,
            agency,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=13.5,
            fontweight="bold",
            color="#1b1f23",
        )
        ax.set_yticks(y_positions)
        ax.set_yticklabels(labels, fontsize=11, color=BORDER_COLOR)
        ax.tick_params(axis="x", labelsize=11, colors=BORDER_COLOR)
        ax.tick_params(axis="y", colors=BORDER_COLOR)
        ax.invert_yaxis()
        ax.xaxis.set_major_formatter(FuncFormatter(format_billions_axis))
        ax.xaxis.set_major_locator(MultipleLocator(2_000_000_000))
        ax.set_xlim(0, X_AXIS_MAX if max_amount else 1)
        ax.grid(axis="x", color="#d0d6dc", linewidth=0.8)
        ax.grid(axis="y", visible=False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BORDER_COLOR)
        ax.spines["bottom"].set_color(BORDER_COLOR)

    axes[-1].set_xlabel(X_AXIS_LABEL, fontsize=13, color=BORDER_COLOR)

    fig.suptitle(
        TITLE_TEXT,
        x=0.055,
        y=0.972,
        ha="left",
        fontsize=19,
        fontweight="bold",
    )
    fig.text(
        0.012,
        0.028,
        FOOTER_TEXT,
        fontsize=13,
        color="#4f5b66",
    )
    fig.add_artist(
        Rectangle(
            (BORDER_INSET, BORDER_INSET),
            1 - 2 * BORDER_INSET,
            1 - 2 * BORDER_INSET,
            transform=fig.transFigure,
            fill=False,
            linewidth=BORDER_LINEWIDTH,
            edgecolor=BORDER_COLOR,
            joinstyle="miter",
            zorder=1000,
        )
    )

    fig.tight_layout(rect=[0, 0.13, 1, 0.96], h_pad=1.0)
    fig.savefig(output_png, dpi=220, bbox_inches="tight")
    sanitize_png_output(output_png)
    fig.savefig(output_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    figure_dir, data_dir = ensure_output_dirs(args.output_dir)
    rows_by_agency = build_object_class_rows(args.input)

    chart_data_path = data_dir / "ice_cbp_2025_obba_object_class_chart_data.csv"
    output_png = figure_dir / "ice_cbp_2025_obba_object_class.png"
    output_svg = figure_dir / "ice_cbp_2025_obba_object_class.svg"

    write_chart_data(chart_data_path, rows_by_agency)
    draw_figure(rows_by_agency, output_png, output_svg)
    if args.write_metadata:
        metadata_path = write_figure_metadata(output_png)
        print(f"Wrote metadata: {metadata_path}")

    print(f"Wrote chart data: {chart_data_path}")
    print(f"Wrote figure: {output_png}")
    print(f"Wrote figure: {output_svg}")


if __name__ == "__main__":
    main()
