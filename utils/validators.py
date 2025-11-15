"""Input validation helpers."""

from __future__ import annotations

from typing import Any, Mapping


def validate_patient_payload(payload: Mapping[str, Any]) -> bool:
    """Return True if the payload passes basic validation checks."""

    return bool(payload)
