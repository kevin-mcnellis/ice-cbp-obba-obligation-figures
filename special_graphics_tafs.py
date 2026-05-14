"""TAFS handling for publication graphics.

The raw source panel can still expose `070-X-0532-000` as an X/no-year account,
but current publication graphics classify its Section 90002 facilities rows with
OBBA when File B supplies the explicit program-activity label below.
"""

from __future__ import annotations

from collections.abc import Mapping

CBP_SEC_90002_FACILITIES_TAFS = "070-X-0532-000"
CBP_SEC_90002_FACILITIES_PROGRAM_ACTIVITY = (
    "FACILITIES (PL 119-21, TITLE IX, SUBTITLE A, SEC. 90002)"
)
CBP_SEC_90002_FACILITIES_NOTE = (
    "CBP OBBA totals include 070-X-0532-000 rows where File B labels the "
    "program activity as FACILITIES (PL 119-21, TITLE IX, SUBTITLE A, SEC. "
    "90002)."
)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def is_cbp_sec_90002_facilities_special_row(row: Mapping[str, object]) -> bool:
    return (
        clean_text(row.get("agency")) == "CBP"
        and clean_text(row.get("tafs")) == CBP_SEC_90002_FACILITIES_TAFS
        and clean_text(row.get("program_activity_name"))
        == CBP_SEC_90002_FACILITIES_PROGRAM_ACTIVITY
    )


def graphics_source_bucket_for_row(row: Mapping[str, object]) -> str:
    if is_cbp_sec_90002_facilities_special_row(row):
        return "OBBA"

    funding_source = clean_text(row.get("funding_source"))
    if funding_source in {"Annual - FY25 Act", "Annual - FY26 Act"}:
        return "Annual appropriations - current year BA"
    if funding_source == "Prior annual act / carryover":
        return "Annual appropriations - carryover BA"
    if funding_source == "Fees / no-year / permanent":
        return "Fee revenue"
    if funding_source == "OBBA":
        return "OBBA"
    return funding_source or "Unknown"


def include_in_obba_graphics(row: Mapping[str, object]) -> bool:
    return graphics_source_bucket_for_row(row) == "OBBA"
