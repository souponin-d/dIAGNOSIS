"""Utilities for deriving structured patient features."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
import re

_STAGE_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("Tis", "N0", "M0", "0"),
    ("T1", "N0", "M0", "IA"),
    ("T0", "N1mi", "M0", "IB"),
    ("T1", "N1mi", "M0", "IB"),
    ("T0", "N1", "M0", "IIA"),
    ("T1", "N1", "M0", "IIA"),
    ("T2", "N0", "M0", "IIA"),
    ("T2", "N1", "M0", "IIB"),
    ("T3", "N0", "M0", "IIB"),
    ("T0", "N2", "M0", "IIIA"),
    ("T1", "N2", "M0", "IIIA"),
    ("T2", "N2", "M0", "IIIA"),
    ("T3", "N1", "M0", "IIIA"),
    ("T3", "N2", "M0", "IIIA"),
    ("T4", "N0", "M0", "IIIB"),
    ("T4", "N1", "M0", "IIIB"),
    ("T4", "N2", "M0", "IIIB"),
)


def calculate_stage(patient_data: Mapping[str, str] | None) -> str:
    """Return the AJCC stage derived from TNM categories."""

    if not patient_data:
        return "—"

    t_category = normalize_category(patient_data.get("T", ""), "T")
    n_category = normalize_category(patient_data.get("N", ""), "N")
    m_category = normalize_category(patient_data.get("M", ""), "M")

    if not (t_category and n_category and m_category):
        return "—"

    if m_category == "M1":
        return "IV"
    if n_category == "N3" and m_category == "M0":
        return "IIIC"

    for t_rule, n_rule, m_rule, stage in _STAGE_RULES:
        if t_category == t_rule and n_category == n_rule and m_category == m_rule:
            return stage

    return "—"


def normalize_category(value: str, category_type: str) -> str:
    """Extract the condensed TNM token from a descriptive string."""

    if not value:
        return ""

    head = value.split("—", 1)[0].strip()
    head = head.split(" ", 1)[0].strip()

    if not head:
        return ""

    if category_type == "T":
        if head.lower().startswith("tis"):
            return "Tis"
        match = re.match(r"(T\d+)", head)
        if match:
            return match.group(1)
        return head if head.startswith("T") else ""

    if category_type == "N":
        if head.startswith(("c", "p")) and len(head) > 1:
            head = head[1:]
        mi_match = re.match(r"(N\d+mi)", head)
        if mi_match:
            return mi_match.group(1)
        match = re.match(r"(N\d+)", head)
        if match:
            return match.group(1)
        return head if head.startswith("N") else ""

    if category_type == "M":
        if head.startswith(("c", "p")) and len(head) > 1:
            head = head[1:]
        match = re.match(r"(M\d)", head)
        if match:
            return match.group(1)
        return head if head.startswith("M") else ""

    return ""


def calculate_age(birth_date: str | None) -> int | None:
    """Calculate the completed years of age based on the provided date."""

    if not birth_date:
        return None

    cleaned = birth_date.strip()
    if not cleaned or "_" in cleaned:
        return None

    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            break
        except ValueError:
            parsed = None
    if not parsed:
        return None

    today = date.today()
    years = today.year - parsed.year
    if (today.month, today.day) < (parsed.month, parsed.day):
        years -= 1
    return max(0, years)
