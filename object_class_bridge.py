"""Shared object-class bridge from OMB S-83 titles to project and figure labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

OMB_SECTION_83_REFERENCE = "OMB Circular No. A-11 (2025), Section 83 / Exhibit 83A"
PERSONNEL_EXPENSES = "Personnel expenses"


@dataclass(frozen=True)
class ObjectClassDefinition:
    code: str
    official_name: str


@dataclass(frozen=True)
class ObjectClassBridge:
    source_object_class_name: str
    omb_object_class_code: str
    omb_object_class_name: str
    project_object_class_name: str
    sankey_display_label: str
    obba_display_label: str
    personnel_rollup_component: str
    source_label_matches_omb: str
    source_standard: str
    mapping_note: str


STANDARD_OBJECT_CLASS_DEFINITIONS = {
    "Advisory and assistance services": ObjectClassDefinition("25.1", "Advisory and assistance services"),
    "Benefits for former personnel": ObjectClassDefinition("13.0", "Benefits for former personnel"),
    "Civilian personnel benefits": ObjectClassDefinition("12.1", "Civilian personnel benefits"),
    "Communications, utilities, and miscellaneous charges": ObjectClassDefinition(
        "23.3", "Communications, utilities, and miscellaneous charges"
    ),
    "Equipment": ObjectClassDefinition("31.0", "Equipment"),
    "Financial transfers": ObjectClassDefinition("94.0", "Financial transfers"),
    "Full-time permanent": ObjectClassDefinition("11.1", "Full-time permanent"),
    "Grants, subsidies, and contributions": ObjectClassDefinition("41.0", "Grants, subsidies, and contributions"),
    "Insurance claims and indemnities": ObjectClassDefinition("42.0", "Insurance, claims, and indemnities"),
    "Interest and dividends": ObjectClassDefinition("43.0", "Interest and dividends"),
    "Land and structures": ObjectClassDefinition("32.0", "Land and structures"),
    "Medical care": ObjectClassDefinition("25.6", "Medical care"),
    "Military personnel benefits": ObjectClassDefinition("12.2", "Military personnel benefits"),
    "Operation and maintenance of equipment": ObjectClassDefinition("25.7", "Operation and maintenance of equipment"),
    "Operation and maintenance of facilities": ObjectClassDefinition("25.4", "Operation and maintenance of facilities"),
    "Other goods and services from Federal sources": ObjectClassDefinition(
        "25.3", "Other goods and services from Federal sources"
    ),
    "Other personnel compensation": ObjectClassDefinition("11.5", "Other personnel compensation"),
    "Other services from non-Federal sources": ObjectClassDefinition(
        "25.2", "Other services from non-Federal sources"
    ),
    "Other than full-time permanent": ObjectClassDefinition("11.3", "Other than full-time permanent"),
    "Printing and reproduction": ObjectClassDefinition("24.0", "Printing and reproduction"),
    "Refunds": ObjectClassDefinition("44.0", "Refunds"),
    "Rental payments to GSA": ObjectClassDefinition("23.1", "Rental payments to GSA"),
    "Rental payments to others": ObjectClassDefinition("23.2", "Rental payments to others"),
    "Research and development contracts": ObjectClassDefinition("25.5", "Research and development contracts"),
    "Special personal services payments": ObjectClassDefinition("11.8", "Special personal services payments"),
    "Subsistence and support of persons": ObjectClassDefinition("25.8", "Subsistence and support of persons"),
    "Supplies and materials": ObjectClassDefinition("26.0", "Supplies and materials"),
    "Transportation of things": ObjectClassDefinition("22.0", "Transportation of things"),
    "Travel and transportation of persons": ObjectClassDefinition("21.0", "Travel and transportation of persons"),
    "Unvouchered": ObjectClassDefinition("91.0", "Unvouchered"),
}

PERSONNEL_COMPONENT_NAMES = frozenset(
    {
        "Benefits for former personnel",
        "Civilian personnel benefits",
        "Full-time permanent",
        "Other personnel compensation",
        "Other than full-time permanent",
        "Special personal services payments",
    }
)

SANKEY_DISPLAY_OVERRIDES = {
    "Operation and maintenance of facilities": "Facilities operations and maintenance",
    "Travel and transportation of persons": "Travel and transportation",
    "Advisory and assistance services": "Advisory and assistance",
    "Other services from non-Federal sources": "Other services (non-Federal)",
    "Other goods and services from Federal sources": "Other goods and services (Federal)",
}

OBBA_DISPLAY_OVERRIDES = {
    "Operation and maintenance of facilities": "Facilities operations",
    "Travel and transportation of persons": "Travel and transportation",
    "Other services from non-Federal sources": "Other non-federal services",
    "Other goods and services from Federal sources": "Other federal goods/services",
}

BRIDGE_FIELDNAMES = [
    "source_object_class_name",
    "omb_object_class_code",
    "omb_object_class_name",
    "project_object_class_name",
    "sankey_display_label",
    "obba_display_label",
    "personnel_rollup_component",
    "source_label_matches_omb",
    "source_standard",
    "mapping_note",
]


def clean_object_class_name(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return "Unknown"
    return text


def object_class_definition(source_object_class_name: str) -> ObjectClassDefinition | None:
    return STANDARD_OBJECT_CLASS_DEFINITIONS.get(clean_object_class_name(source_object_class_name))


def is_personnel_object_class(source_object_class_name: str) -> bool:
    return clean_object_class_name(source_object_class_name) in PERSONNEL_COMPONENT_NAMES


def project_object_class_name(source_object_class_name: str) -> str:
    cleaned_name = clean_object_class_name(source_object_class_name)
    if cleaned_name in PERSONNEL_COMPONENT_NAMES:
        return PERSONNEL_EXPENSES
    return cleaned_name


def _display_label(project_name: str, overrides: dict[str, str]) -> str:
    return overrides.get(project_name, project_name)


def sankey_display_label(source_or_project_object_class_name: str) -> str:
    return _display_label(project_object_class_name(source_or_project_object_class_name), SANKEY_DISPLAY_OVERRIDES)


def obba_display_label(source_or_project_object_class_name: str) -> str:
    return _display_label(project_object_class_name(source_or_project_object_class_name), OBBA_DISPLAY_OVERRIDES)


def _mapping_note(source_name: str, definition: ObjectClassDefinition | None, project_name: str) -> str:
    if source_name == "Unknown":
        return "Source CSV contains an unknown or blank object-class label, so the pipeline retains an Unknown bucket."
    if source_name in PERSONNEL_COMPONENT_NAMES:
        return "OMB personnel compensation/benefit classes are rolled into the project's Personnel expenses category."
    if definition is None:
        return "No OMB Section 83 mapping is recorded locally for this source label; the project retains the source label."
    if source_name != sankey_display_label(source_name) or source_name != obba_display_label(source_name):
        return "Project retains the object class, while figure scripts use shorter publication labels."
    if source_name != project_name:
        return "Project normalizes the source label before charting."
    return "Project retains the OMB object class as its own category."


def build_object_class_bridge(source_object_class_name: str) -> ObjectClassBridge:
    source_name = clean_object_class_name(source_object_class_name)
    definition = object_class_definition(source_name)
    official_name = definition.official_name if definition else ""
    project_name = project_object_class_name(source_name)
    return ObjectClassBridge(
        source_object_class_name=source_name,
        omb_object_class_code=definition.code if definition else "",
        omb_object_class_name=official_name,
        project_object_class_name=project_name,
        sankey_display_label=sankey_display_label(source_name),
        obba_display_label=obba_display_label(source_name),
        personnel_rollup_component="yes" if source_name in PERSONNEL_COMPONENT_NAMES else "no",
        source_label_matches_omb="yes" if definition and source_name == official_name else "no" if definition else "",
        source_standard=OMB_SECTION_83_REFERENCE if definition else "",
        mapping_note=_mapping_note(source_name, definition, project_name),
    )


def _code_sort_key(code: str) -> tuple[int, tuple[int, ...] | tuple[()], str]:
    if not code:
        return (1, tuple(), "")
    parts = tuple(int(part) for part in code.split("."))
    return (0, parts, code)


def build_object_class_bridge_rows(source_object_class_names: Iterable[str]) -> list[dict[str, str]]:
    bridges = {
        build_object_class_bridge(name)
        for name in source_object_class_names
    }
    sorted_bridges = sorted(
        bridges,
        key=lambda bridge: (
            _code_sort_key(bridge.omb_object_class_code),
            bridge.source_object_class_name,
        ),
    )
    return [
        {
            "source_object_class_name": bridge.source_object_class_name,
            "omb_object_class_code": bridge.omb_object_class_code,
            "omb_object_class_name": bridge.omb_object_class_name,
            "project_object_class_name": bridge.project_object_class_name,
            "sankey_display_label": bridge.sankey_display_label,
            "obba_display_label": bridge.obba_display_label,
            "personnel_rollup_component": bridge.personnel_rollup_component,
            "source_label_matches_omb": bridge.source_label_matches_omb,
            "source_standard": bridge.source_standard,
            "mapping_note": bridge.mapping_note,
        }
        for bridge in sorted_bridges
    ]
