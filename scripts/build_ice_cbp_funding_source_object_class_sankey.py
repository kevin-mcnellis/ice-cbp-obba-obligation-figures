#!/usr/bin/env python3
"""Build 2025 funding-source-to-object-class charts for ICE and CBP."""

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

from object_class_bridge import (
    BRIDGE_FIELDNAMES,
    build_object_class_bridge_rows,
    project_object_class_name,
    sankey_display_label,
)
from special_graphics_tafs import (
    CBP_SEC_90002_FACILITIES_NOTE,
    graphics_source_bucket_for_row,
    is_cbp_sec_90002_facilities_special_row,
)

DEFAULT_INPUT = PROJECT_DIR / "ice_cbp_file_b_program_activity_object_class_monthly_and_quarterly_2024_01_to_2025_12.csv"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output"
CACHE_ROOT = PROJECT_DIR / "tmp"
TOP_N_OBJECT_CLASSES = 5
NODE_GAP_SHARE = 0.03
TEXT_LEFT = 0.03
TEXT_RIGHT = 0.98
BORDER_COLOR = "#000000"
BORDER_LINEWIDTH = 1.6
BORDER_INSET = 0.002
LEFT_X0 = 0.17
LEFT_X1 = 0.22
RIGHT_X0 = 0.74
RIGHT_X1 = 0.79
LEFT_LABEL_LINE_X = LEFT_X0 - 0.014
LEFT_LABEL_TEXT_X = LEFT_X0 - 0.022
RIGHT_LABEL_LINE_X = RIGHT_X1 + 0.015
RIGHT_LABEL_TEXT_X = RIGHT_X1 + 0.022
QUARTERLY_SCOPE = "quarterly"
PRIOR_QUARTER_END_MONTH = "2024-12"

METRIC_CONFIG = {
    "outlays": {
        "column": "outlays",
        "noun": "outlays",
        "title": {
            "ICE": "ICE: Most Personnel Outlays Still Came From Annual Appropriations in Calendar Year 2025",
            "CBP": "CBP: Most Personnel Outlays Still Came From Annual Appropriations in Calendar Year 2025",
        },
        "method_note": (
            "Calendar-year 2025 outlays come from cumulative quarter-end File B snapshots covering "
            "Dec. 31, 2024 to Mar. 31, 2025; Mar. 31 to Jun. 30; Jun. 30 to Sep. 30; and Oct. 1 to Dec. 31, 2025."
        ),
        "chart_data_name": "ice_cbp_2025_funding_source_object_class_chart_data.csv",
        "figure_stem": "{agency}_2025_funding_source_object_class",
    },
    "obligations": {
        "column": "obligated",
        "noun": "obligations",
        "title": {
            "ICE": "ICE: Calendar Year 2025 Obligations by Funding Source and Object Class",
            "CBP": "CBP: Calendar Year 2025 Obligations by Funding Source and Object Class",
        },
        "method_note": (
            "Calendar-year 2025 obligations come from cumulative quarter-end File B snapshots covering "
            "Dec. 31, 2024 to Mar. 31, 2025; Mar. 31 to Jun. 30; Jun. 30 to Sep. 30; and Oct. 1 to Dec. 31, 2025."
        ),
        "chart_data_name": "ice_cbp_2025_funding_source_object_class_obligations_chart_data.csv",
        "figure_stem": "{agency}_2025_funding_source_object_class_obligations",
    },
}

AGENCY_ORDER = ["ICE", "CBP"]
SOURCE_BUCKET_ORDER = [
    "Annual appropriations - current year BA",
    "Annual appropriations - carryover BA",
    "Fee revenue",
    "OBBA",
]
SOURCE_BUCKET_COLORS = {
    "Annual appropriations - current year BA": "#2f5d8a",
    "Annual appropriations - carryover BA": "#b9c4d0",
    "Fee revenue": "#36a297",
    "OBBA": "#e76f51",
}
SOURCE_BUCKET_SHORT_LABELS = {
    "Annual appropriations - current year BA": "Annual appropriation (current year)",
    "Annual appropriations - carryover BA": "Annual appropriation (carryover)",
    "Fee revenue": "Fees and other revenues",
    "OBBA": "OBBA",
}
for cache_dir in (CACHE_ROOT, CACHE_ROOT / "mplconfig", CACHE_ROOT / "xdg-cache"):
    cache_dir.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_ROOT / "mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_ROOT / "xdg-cache"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--metric",
        choices=sorted(METRIC_CONFIG),
        default="outlays",
        help="File B metric to visualize.",
    )
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


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def normalize_object_class(object_class: str) -> str:
    return project_object_class_name(object_class)


def display_object_class_label(object_class: str) -> str:
    return sankey_display_label(object_class)


def source_bucket_for_row(row: dict[str, str]) -> str:
    return graphics_source_bucket_for_row(row)


def wrap_label(text: str, width: int = 34) -> str:
    if len(text) <= width:
        return text
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        projected = len(word) if not current else current_len + 1 + len(word)
        if projected > width and current:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len = projected
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def wrap_footer_text(text: str, width: int = 205) -> str:
    return textwrap.fill(text, width=width)


def build_footer_text(
    other_categories: list[str],
    metric_noun: str,
) -> str:
    line_one = (
        f"Notes: Calendar-year 2025 {metric_noun} are derived from cumulative quarter-end File B snapshots: "
        "Mar. 31, 2025 minus Dec. 31, 2024; Jun. 30 minus Mar. 31; Sep. 30 minus Jun. 30; plus Dec. 31, 2025. "
        '"Personnel expenses" groups pay and benefit categories.'
    )
    line_two = summarize_other_categories(other_categories)
    return wrap_footer_text(f"{line_one} {line_two} Source: USAspending.gov File B.")


def format_csv_number(value: float) -> str:
    return f"{value:.2f}"


def format_billions(value: float) -> str:
    return f"${value / 1_000_000_000:.2f}B"


def format_millions(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    return f"${value / 1_000_000:.0f}M"


def cy2025_total_from_quarter_ends(
    cumulative_values: dict[tuple[str, str, str, str], float],
    agency: str,
    source_bucket: str,
    object_class: str,
) -> float:
    dec_2024 = cumulative_values.get((agency, source_bucket, object_class, PRIOR_QUARTER_END_MONTH), 0.0)
    mar_2025 = cumulative_values.get((agency, source_bucket, object_class, "2025-03"), 0.0)
    jun_2025 = cumulative_values.get((agency, source_bucket, object_class, "2025-06"), 0.0)
    sep_2025 = cumulative_values.get((agency, source_bucket, object_class, "2025-09"), 0.0)
    dec_2025 = cumulative_values.get((agency, source_bucket, object_class, "2025-12"), 0.0)

    return (
        (mar_2025 - dec_2024)
        + (jun_2025 - mar_2025)
        + (sep_2025 - jun_2025)
        + dec_2025
    )


def spaced_positions(
    desired_positions: list[float],
    *,
    min_gap: float,
    lower: float = 0.04,
    upper: float = 0.96,
) -> list[float]:
    if not desired_positions:
        return []
    adjusted = desired_positions[:]
    adjusted[0] = min(adjusted[0], upper)
    for index in range(1, len(adjusted)):
        adjusted[index] = min(adjusted[index], adjusted[index - 1] - min_gap)
    if adjusted[-1] < lower:
        adjusted[-1] = lower
        for index in range(len(adjusted) - 2, -1, -1):
            adjusted[index] = max(adjusted[index], adjusted[index + 1] + min_gap)
    if adjusted[0] > upper:
        adjusted[0] = upper
        for index in range(1, len(adjusted)):
            adjusted[index] = min(adjusted[index], adjusted[index - 1] - min_gap)
    return adjusted


def verify_rows_against_source_totals(
    rows_by_agency: dict[str, list[dict[str, object]]],
    source_totals: dict[tuple[str, str], float],
) -> None:
    chart_totals = defaultdict(float)
    for agency in AGENCY_ORDER:
        for row in rows_by_agency[agency]:
            chart_totals[(agency, str(row["source_bucket"]))] += float(row["amount"])

    tolerance = 0.01
    for agency in AGENCY_ORDER:
        for source_bucket in SOURCE_BUCKET_ORDER:
            expected = source_totals.get((agency, source_bucket), 0.0)
            actual = chart_totals.get((agency, source_bucket), 0.0)
            if abs(expected - actual) > tolerance:
                raise RuntimeError(
                    "Sankey source-bucket totals do not match the fiscal-year-aware "
                    f"source aggregation for {agency} / {source_bucket}: "
                    f"expected {expected:.2f}, got {actual:.2f}"
                )


def build_rows(
    path: Path,
    metric_column: str,
) -> tuple[
    dict[str, list[dict[str, object]]],
    dict[str, list[str]],
    dict[tuple[str, str], float],
    dict[str, float],
]:
    cumulative_values = defaultdict(float)
    special_inclusion_totals = defaultdict(float)

    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["submission_scope"] != QUARTERLY_SCOPE or row["snapshot_status"] != "published snapshot":
                continue
            agency = row["agency"]
            if agency not in AGENCY_ORDER:
                continue
            source_bucket = source_bucket_for_row(row)
            if source_bucket not in SOURCE_BUCKET_ORDER:
                continue
            object_class = normalize_object_class(clean_text(row["object_class_name"]))
            month = row["snapshot_month"]
            amount = float(row[metric_column] or 0)
            cumulative_values[(agency, source_bucket, object_class, month)] += amount
            if is_cbp_sec_90002_facilities_special_row(row):
                special_inclusion_totals[agency] += amount

    by_agency_source_object = defaultdict(float)
    object_totals = defaultdict(float)
    source_totals = defaultdict(float)
    series_keys = {
        (agency, source_bucket, object_class)
        for agency, source_bucket, object_class, _month in cumulative_values
    }

    for agency, source_bucket, object_class in series_keys:
        # File B obligation and outlay fields are cumulative within each fiscal year, so a
        # calendar-year 2025 total has to bridge the FY2025-to-FY2026 reset at Dec. 31, 2025.
        total_2025 = cy2025_total_from_quarter_ends(
            cumulative_values,
            agency,
            source_bucket,
            object_class,
        )

        if total_2025 <= 0:
            continue

        by_agency_source_object[(agency, source_bucket, object_class)] += total_2025
        object_totals[(agency, object_class)] += total_2025
        source_totals[(agency, source_bucket)] += total_2025

    rows_by_agency: dict[str, list[dict[str, object]]] = {}
    other_categories_by_agency: dict[str, list[str]] = {}
    for agency in AGENCY_ORDER:
        agency_object_totals = sorted(
            (
                (object_class, amount)
                for (agency_key, object_class), amount in object_totals.items()
                if agency_key == agency
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        ranked_object_classes = [object_class for object_class, _amount in agency_object_totals[:TOP_N_OBJECT_CLASSES]]
        other_categories_by_agency[agency] = [
            object_class for object_class, _amount in agency_object_totals[TOP_N_OBJECT_CLASSES:]
        ]
        rows: list[dict[str, object]] = []
        for source_bucket in SOURCE_BUCKET_ORDER:
            other_amount = 0.0
            for (agency_key, source_bucket_key, object_class), amount in by_agency_source_object.items():
                if agency_key != agency or source_bucket_key != source_bucket:
                    continue
                if object_class in ranked_object_classes:
                    rows.append(
                        {
                            "agency": agency,
                            "source_bucket": source_bucket,
                            "object_class_name": object_class,
                            "amount": amount,
                        }
                    )
                else:
                    other_amount += amount
            if other_amount > 0:
                rows.append(
                    {
                        "agency": agency,
                        "source_bucket": source_bucket,
                        "object_class_name": "All other activities",
                        "amount": other_amount,
                    }
                )

        object_order = ranked_object_classes[:]
        if any(row["object_class_name"] == "All other activities" for row in rows):
            object_order.append("All other activities")
        order_lookup = {label: index for index, label in enumerate(object_order)}
        rows.sort(
            key=lambda row: (
                SOURCE_BUCKET_ORDER.index(str(row["source_bucket"])),
                order_lookup[str(row["object_class_name"])],
            )
        )
        rows_by_agency[agency] = rows

    verify_rows_against_source_totals(rows_by_agency, source_totals)
    return rows_by_agency, other_categories_by_agency, source_totals, special_inclusion_totals


def summarize_other_categories(other_categories: list[str]) -> str:
    if not other_categories:
        return 'No categories are grouped into "All Other Activities" in this chart.'
    return '"All Other Activities" groups smaller categories omitted from the chart.'


def write_chart_data(
    output_path: Path,
    rows_by_agency: dict[str, list[dict[str, object]]],
    metric_note: str,
    *,
    include_special_facilities_note: bool,
) -> None:
    fieldnames = ["agency", "source_bucket", "object_class_name", "amount", "snapshot_month", "note"]
    note = metric_note
    if include_special_facilities_note:
        note = f"{metric_note} {CBP_SEC_90002_FACILITIES_NOTE}"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for agency in AGENCY_ORDER:
            for row in rows_by_agency[agency]:
                writer.writerow(
                    {
                        "agency": row["agency"],
                        "source_bucket": row["source_bucket"],
                        "object_class_name": row["object_class_name"],
                        "amount": format_csv_number(float(row["amount"])),
                        "snapshot_month": "2025",
                        "note": note,
                    }
                )


def collect_source_object_classes(path: Path) -> list[str]:
    observed: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            agency = clean_text(row.get("agency", ""))
            if agency and agency not in AGENCY_ORDER:
                continue
            observed.add(clean_text(row.get("object_class_name", "")) or "Unknown")
    return sorted(observed)


def write_object_class_bridge(output_path: Path, source_object_classes: list[str]) -> None:
    rows = build_object_class_bridge_rows(source_object_classes)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRIDGE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_figure_metadata(
    output_png: Path,
    *,
    title: str,
    footer_text: str,
    panel_order: list[str],
) -> Path:
    metadata_path = output_png.with_suffix(".meta.json")
    payload = {
        "title": title,
        "axis_labels": {"x": "", "y": ""},
        "footer_text": footer_text,
        "panel_order": panel_order,
    }
    metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return metadata_path


def stacked_spans(labels: list[str], totals: dict[str, float]) -> dict[str, tuple[float, float]]:
    if not labels:
        return {}
    gap = NODE_GAP_SHARE
    available_height = 1.0 - gap * (len(labels) - 1)
    grand_total = sum(max(totals[label], 0.0) for label in labels)
    spans: dict[str, tuple[float, float]] = {}
    cursor = 1.0
    for label in labels:
        height = 0.0 if grand_total == 0 else available_height * totals[label] / grand_total
        top = cursor
        bottom = top - height
        spans[label] = (bottom, top)
        cursor = bottom - gap
    return spans


def flow_segments(
    labels: list[str],
    totals: dict[str, float],
    flows: dict[tuple[str, str], float],
    other_axis_labels: list[str],
    axis: str,
) -> dict[tuple[str, str], tuple[float, float]]:
    spans = stacked_spans(labels, totals)
    segments: dict[tuple[str, str], tuple[float, float]] = {}
    for label in labels:
        bottom, top = spans[label]
        height = top - bottom
        total = totals[label]
        cursor = top
        if axis == "left":
            ordered_other = other_axis_labels
        else:
            ordered_other = other_axis_labels
        for other in ordered_other:
            value = flows.get((label, other), 0.0) if axis == "left" else flows.get((other, label), 0.0)
            if value <= 0 or total <= 0 or height <= 0:
                continue
            seg_height = height * value / total
            segments[(label, other) if axis == "left" else (other, label)] = (cursor - seg_height, cursor)
            cursor -= seg_height
    return segments


def ribbon_polygon(
    left_bottom: float,
    left_top: float,
    right_bottom: float,
    right_top: float,
    color: str,
) -> Polygon:
    t = np.linspace(0, 1, 40)
    x_top = LEFT_X1 + (RIGHT_X0 - LEFT_X1) * t
    x_bottom = x_top[::-1]
    smooth = 3 * t**2 - 2 * t**3
    y_top = left_top + (right_top - left_top) * smooth
    y_bottom = left_bottom + (right_bottom - left_bottom) * smooth[::-1]
    points = np.column_stack(
        [
            np.concatenate([x_top, x_bottom]),
            np.concatenate([y_top, y_bottom]),
        ]
    )
    return Polygon(points, closed=True, facecolor=color, edgecolor="none", alpha=0.82)


def draw_panel(ax: plt.Axes, agency: str, rows: list[dict[str, object]]) -> None:
    category_fontsize = 10.2
    source_totals = {label: 0.0 for label in SOURCE_BUCKET_ORDER}
    object_totals = defaultdict(float)
    flows: dict[tuple[str, str], float] = {}

    for row in rows:
        source = str(row["source_bucket"])
        object_class = str(row["object_class_name"])
        amount = float(row["amount"])
        source_totals[source] += amount
        object_totals[object_class] += amount
        flows[(source, object_class)] = flows.get((source, object_class), 0.0) + amount

    object_labels = [
        label
        for label, _amount in sorted(object_totals.items(), key=lambda item: item[1], reverse=True)
    ]

    left_segments = flow_segments(SOURCE_BUCKET_ORDER, source_totals, flows, object_labels, axis="left")
    right_segments = flow_segments(object_labels, object_totals, flows, SOURCE_BUCKET_ORDER, axis="right")
    left_spans = stacked_spans(SOURCE_BUCKET_ORDER, source_totals)
    right_spans = stacked_spans(object_labels, object_totals)

    for source in SOURCE_BUCKET_ORDER:
        color = SOURCE_BUCKET_COLORS[source]
        for object_class in object_labels:
            amount = flows.get((source, object_class), 0.0)
            if amount <= 0:
                continue
            left_bottom, left_top = left_segments[(source, object_class)]
            right_bottom, right_top = right_segments[(source, object_class)]
            ax.add_patch(ribbon_polygon(left_bottom, left_top, right_bottom, right_top, color))

    for source in SOURCE_BUCKET_ORDER:
        bottom, top = left_spans[source]
        ax.add_patch(
            Rectangle(
                (LEFT_X0, bottom),
                LEFT_X1 - LEFT_X0,
                top - bottom,
                facecolor=SOURCE_BUCKET_COLORS[source],
                edgecolor="white",
                linewidth=1.0,
            )
        )
        mid = (bottom + top) / 2
    left_items = [
        (source, (left_spans[source][0] + left_spans[source][1]) / 2)
        for source in SOURCE_BUCKET_ORDER
    ]
    left_items.sort(key=lambda item: item[1], reverse=True)
    left_positions = spaced_positions([item[1] for item in left_items], min_gap=0.09)
    for (source, original_mid), label_y in zip(left_items, left_positions):
        ax.plot([LEFT_LABEL_LINE_X, LEFT_X0], [label_y, original_mid], color="#98a4af", linewidth=0.8)
        ax.text(
            LEFT_LABEL_TEXT_X,
            label_y,
            f"{SOURCE_BUCKET_SHORT_LABELS[source]}\n{format_millions(source_totals[source])}",
            ha="right",
            va="center",
            fontsize=category_fontsize,
            color="#000000",
        )

    right_items = []
    for object_class in object_labels:
        bottom, top = right_spans[object_class]
        ax.add_patch(
            Rectangle(
                (RIGHT_X0, bottom),
                RIGHT_X1 - RIGHT_X0,
                top - bottom,
                facecolor="#dfe6ee",
                edgecolor="white",
                linewidth=1.0,
            )
        )
        right_items.append((object_class, (bottom + top) / 2))

    right_items.sort(key=lambda item: item[1], reverse=True)
    right_positions = spaced_positions([item[1] for item in right_items], min_gap=0.085)
    for (object_class, original_mid), label_y in zip(right_items, right_positions):
        ax.plot([RIGHT_X1, RIGHT_LABEL_LINE_X], [original_mid, label_y], color="#98a4af", linewidth=0.8)
        ax.text(
            RIGHT_LABEL_TEXT_X,
            label_y,
            f"{wrap_label(display_object_class_label(object_class), 30)}\n{format_millions(object_totals[object_class])}",
            ha="left",
            va="center",
            fontsize=category_fontsize,
            color="#000000",
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def draw_figure_for_agency(
    agency: str,
    rows: list[dict[str, object]],
    other_categories: list[str],
    output_png: Path,
    output_svg: Path,
    title_text: str,
    metric_note: str,
    metric_noun: str,
    include_special_facilities_note: bool,
    write_metadata: bool,
) -> None:
    plt.style.use("seaborn-v0_8-white")
    fig, ax = plt.subplots(1, 1, figsize=(13.2, 6.2))
    fig.patch.set_facecolor("white")
    fig.patch.set_edgecolor("white")
    fig.patch.set_linewidth(0)

    draw_panel(ax, agency, rows)

    fig.suptitle(
        title_text,
        x=TEXT_LEFT,
        y=0.965,
        ha="left",
        fontsize=19.0,
        fontweight="bold",
    )
    footer_text = build_footer_text(
        other_categories,
        metric_noun,
    )
    fig.text(
        TEXT_LEFT,
        0.028,
        footer_text,
        fontsize=9.2,
        color="#4f5b66",
        ha="left",
        va="bottom",
        wrap=True,
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

    fig.subplots_adjust(left=0.06, right=0.98, top=0.86, bottom=0.16)
    fig.savefig(
        output_png,
        dpi=220,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        edgecolor=fig.get_edgecolor(),
    )
    sanitize_png_output(output_png)
    fig.savefig(
        output_svg,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        edgecolor=fig.get_edgecolor(),
    )
    if write_metadata:
        metadata_path = write_figure_metadata(
            output_png,
            title=title_text,
            footer_text=footer_text,
            panel_order=[agency],
        )
        print(f"Wrote metadata: {metadata_path}")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    metric_config = METRIC_CONFIG[args.metric]
    figure_dir, data_dir = ensure_output_dirs(args.output_dir)
    rows_by_agency, other_categories_by_agency, _source_totals, special_inclusion_totals = build_rows(
        args.input,
        metric_config["column"],
    )
    include_special_facilities_note = any(total > 0 for total in special_inclusion_totals.values())
    bridge_path = data_dir / "ice_cbp_object_class_bridge.csv"

    chart_data_path = data_dir / metric_config["chart_data_name"]
    write_chart_data(
        chart_data_path,
        rows_by_agency,
        metric_config["method_note"],
        include_special_facilities_note=include_special_facilities_note,
    )
    write_object_class_bridge(bridge_path, collect_source_object_classes(args.input))
    print(f"Wrote chart data: {chart_data_path}")
    print(f"Wrote object-class bridge: {bridge_path}")

    for agency in AGENCY_ORDER:
        figure_stem = metric_config["figure_stem"].format(agency=agency.lower())
        output_png = figure_dir / f"{figure_stem}.png"
        output_svg = figure_dir / f"{figure_stem}.svg"
        draw_figure_for_agency(
            agency,
            rows_by_agency[agency],
            other_categories_by_agency[agency],
            output_png,
            output_svg,
            metric_config["title"][agency],
            metric_config["method_note"],
            metric_config["noun"],
            include_special_facilities_note,
            args.write_metadata,
        )
        print(f"Wrote figure: {output_png}")
        print(f"Wrote figure: {output_svg}")


if __name__ == "__main__":
    main()
