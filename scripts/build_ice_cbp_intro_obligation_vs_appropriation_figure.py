#!/usr/bin/env python3
"""Build an intro figure comparing CY2025 obligated vs. appropriated OBBA funding."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import textwrap
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output"
CACHE_ROOT = PROJECT_DIR / "tmp"
BORDER_COLOR = "#000000"
BORDER_LINEWIDTH = 1.6
BORDER_INSET = 0.002
PRIMARY_TEXT_COLOR = "#1b1f23"
FOOTER_TEXT_COLOR = "#4f5b66"
APPROPRIATED_COLOR = "#93a6ba"
APPROPRIATED_EDGE_COLOR = "#5e7288"
APPROPRIATED_LABEL_COLOR = "#23303b"
ANNUAL_ACT_COLOR = "#b86a50"
ANNUAL_ACT_EDGE_COLOR = "#7b412f"
ANNUAL_ACT_LABEL_COLOR = "#5d2c20"
OBLIGATED_COLOR = "#1f4e79"
AGENCY_ORDER = ["ICE", "CBP"]
MEASURE_ORDER = ["Annual Appropriations", "Appropriated", "Obligated"]
TITLE_TEXT = "OBBA Quadrupled ICE and CBP Funding: Most Remains Unobligated Through December 2025"
Y_AXIS_LABEL = "Billions of dollars"
Y_AXIS_MAX = 80_000_000_000
FOOTER_TEXT = textwrap.fill(
    (
        "Notes: Amounts are rounded to nearest $100 million. OBBA appropriations reflect statutory amounts in P.L. 119-21; "
        "FY25 annual appropriations reflect USAspending.gov File A total budgetary resources as of September 2025; "
        "obligations reflect USAspending.gov File B"
    ),
    width=125,
)

DATA_ROWS = [
    {
        "agency": "ICE",
        "measure": "Annual Appropriations",
        "amount": 10_647_190_528.35,
        "share_of_appropriated": 0.1422,
        "label_text": "$10.6B FY25 Annual Appropriations",
    },
    {
        "agency": "ICE",
        "measure": "Appropriated",
        "amount": 74_850_000_000,
        "share_of_appropriated": 1.0,
        "label_text": "OBBA Appropriation $74.9 billion",
        "display_amount_text": "$74.9 billion",
    },
    {
        "agency": "ICE",
        "measure": "Obligated",
        "amount": 3_800_000_000,
        "share_of_appropriated": 0.0508,
        "label_text": "$3.8B obligated (5%)",
    },
    {
        "agency": "CBP",
        "measure": "Annual Appropriations",
        "amount": 21_020_920_849.59,
        "share_of_appropriated": 0.3249,
        "label_text": "$21.0B FY25 Annual Appropriations",
    },
    {
        "agency": "CBP",
        "measure": "Appropriated",
        "amount": 64_700_000_000,
        "share_of_appropriated": 1.0,
        "label_text": "$64.7B OBBA Appropriation",
    },
    {
        "agency": "CBP",
        "measure": "Obligated",
        "amount": 11_300_000_000,
        "share_of_appropriated": 0.17,
        "label_text": "$11.3B obligated (17%)",
    },
]

for cache_dir in (CACHE_ROOT, CACHE_ROOT / "mplconfig", CACHE_ROOT / "xdg-cache"):
    cache_dir.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_ROOT / "mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_ROOT / "xdg-cache"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
        "axis_labels": {"x": "", "y": Y_AXIS_LABEL},
        "footer_text": FOOTER_TEXT,
        "panel_order": AGENCY_ORDER,
    }
    metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return metadata_path


def format_csv_number(value: float) -> str:
    return f"{value:.2f}"


def format_billions_axis(value: float, _pos: int) -> str:
    return f"${value / 1_000_000_000:.0f}B"


def format_amount_billions(value: float) -> str:
    return f"${value / 1_000_000_000:.1f}B"


def bar_color(agency: str, measure: str) -> str:
    if measure == "Appropriated":
        return APPROPRIATED_COLOR
    if measure == "Annual Appropriations":
        return ANNUAL_ACT_COLOR
    return OBLIGATED_COLOR


def write_chart_data(output_path: Path) -> None:
    fieldnames = [
        "agency",
        "measure",
        "amount",
        "share_of_appropriated",
        "label_text",
        "note",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in DATA_ROWS:
            writer.writerow(
                {
                    "agency": row["agency"],
                    "measure": row["measure"],
                    "amount": format_csv_number(float(row["amount"])),
                    "share_of_appropriated": f"{float(row['share_of_appropriated']):.4f}",
                    "label_text": row["label_text"],
                    "note": FOOTER_TEXT.replace("\n", " "),
                }
            )


def draw_figure(output_png: Path, output_svg: Path) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(1, 1, figsize=(12.9, 7.6))
    fig.patch.set_facecolor("white")

    x_positions = [0.0, 1.62]
    column_width = 0.54
    annual_column_width = column_width
    annual_offset = 0.76
    appropriated_label_gap = Y_AXIS_MAX * 0.012
    obligated_label_y_gap = Y_AXIS_MAX * 0.012
    annual_label_gap = Y_AXIS_MAX * 0.012

    agency_rows: dict[str, dict[str, dict[str, object]]] = {agency: {} for agency in AGENCY_ORDER}
    for row in DATA_ROWS:
        agency_rows[str(row["agency"])][str(row["measure"])] = row

    for agency, x_pos in zip(AGENCY_ORDER, x_positions):
        annual_row = agency_rows[agency]["Annual Appropriations"]
        appropriated_row = agency_rows[agency]["Appropriated"]
        obligated_row = agency_rows[agency]["Obligated"]
        annual_amount = float(annual_row["amount"])
        appropriated_amount = float(appropriated_row["amount"])
        obligated_amount = float(obligated_row["amount"])
        appropriated_label_amount = appropriated_row.get("display_amount_text") or format_amount_billions(appropriated_amount)
        agency_color = bar_color(agency, "Obligated")
        annual_x = x_pos - annual_offset

        ax.bar(
            annual_x,
            annual_amount,
            width=annual_column_width,
            color=ANNUAL_ACT_COLOR,
            edgecolor=ANNUAL_ACT_EDGE_COLOR,
            linewidth=1.35,
            zorder=2,
        )

        ax.bar(
            x_pos,
            appropriated_amount,
            width=column_width,
            color=APPROPRIATED_COLOR,
            edgecolor=APPROPRIATED_EDGE_COLOR,
            linewidth=1.35,
            zorder=1,
        )
        ax.bar(
            x_pos,
            obligated_amount,
            width=column_width,
            color=agency_color,
            edgecolor="#18324a",
            linewidth=1.4,
            zorder=3,
        )

        ax.text(
            annual_x,
            annual_amount + annual_label_gap,
            f"FY25 Annual\nAppropriations\n{format_amount_billions(annual_amount)}",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="semibold",
            color=ANNUAL_ACT_LABEL_COLOR,
            zorder=4,
        )

        ax.text(
            x_pos,
            appropriated_amount + appropriated_label_gap,
            f"OBBA Appropriation\n{appropriated_label_amount}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="semibold",
            color=APPROPRIATED_LABEL_COLOR,
            zorder=4,
        )
        ax.text(
            x_pos,
            obligated_amount + obligated_label_y_gap,
            f"{format_amount_billions(obligated_amount)}\nobligated",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color=agency_color,
            zorder=5,
        )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(AGENCY_ORDER, fontsize=13.5, fontweight="bold", color=PRIMARY_TEXT_COLOR)
    ax.tick_params(axis="x", length=0, pad=10)
    ax.tick_params(axis="y", labelsize=11, colors=PRIMARY_TEXT_COLOR, length=0)
    ax.yaxis.set_major_formatter(FuncFormatter(format_billions_axis))
    ax.set_yticks([0, 20_000_000_000, 40_000_000_000, 60_000_000_000])
    ax.set_xlim(-1.55, 2.95)
    ax.set_ylim(0, Y_AXIS_MAX * 1.08)
    ax.grid(axis="y", color="#d0d6dc", linewidth=0.8)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#111111")
    ax.spines["left"].set_linewidth(1.4)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#111111")
    ax.spines["bottom"].set_linewidth(1.4)
    ax.set_ylabel(Y_AXIS_LABEL, fontsize=13, color=PRIMARY_TEXT_COLOR)

    fig.suptitle(
        TITLE_TEXT,
        x=0.055,
        y=0.972,
        ha="left",
        fontsize=19,
        fontweight="bold",
        color=PRIMARY_TEXT_COLOR,
    )
    fig.text(
        0.012,
        0.03,
        FOOTER_TEXT,
        fontsize=12,
        color=FOOTER_TEXT_COLOR,
        ha="left",
        va="bottom",
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

    fig.tight_layout(rect=[0, 0.11, 1, 0.95])
    fig.savefig(output_png, dpi=220, bbox_inches="tight")
    sanitize_png_output(output_png)
    fig.savefig(output_svg, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    figure_dir, data_dir = ensure_output_dirs(args.output_dir)
    chart_data_path = data_dir / "ice_cbp_intro_obligation_vs_appropriation_chart_data.csv"
    output_png = figure_dir / "ice_cbp_intro_obligation_vs_appropriation.png"
    output_svg = figure_dir / "ice_cbp_intro_obligation_vs_appropriation.svg"

    write_chart_data(chart_data_path)
    draw_figure(output_png, output_svg)
    if args.write_metadata:
        metadata_path = write_figure_metadata(output_png)
        print(f"Wrote metadata: {metadata_path}")

    print(f"Wrote chart data: {chart_data_path}")
    print(f"Wrote figure: {output_png}")
    print(f"Wrote figure: {output_svg}")


if __name__ == "__main__":
    main()
