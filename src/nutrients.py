from __future__ import annotations

from typing import Iterable

import pandas as pd

from .config import NUTRIENT_CODES
from .utils import as_float, numeric_series


def available_nutrient_codes(items: pd.DataFrame) -> list[str]:
    """Return registered nutrients that have at least one declared numeric value.

    A zero is a valid declared value. Empty cells do not make a nutrient available
    by themselves. Ordering follows ``NUTRIENT_CODES`` so the UI stays stable.
    """
    if items.empty:
        return []

    available: list[str] = []
    for code in NUTRIENT_CODES:
        if code not in items.columns:
            continue
        values = numeric_series(items[code])
        if values.notna().any():
            available.append(code)
    return available


def synchronize_constraints(
    constraints: pd.DataFrame | None,
    items: pd.DataFrame,
) -> pd.DataFrame:
    """Synchronize the constraint grid with nutrients available in selected items.

    Every available nutrient gets exactly one row. Existing minimum/maximum values
    are preserved. A previously active restriction is also preserved when a nutrient
    becomes unavailable, so the user sees a validation error instead of silently
    losing a requirement.
    """
    current = constraints.copy() if isinstance(constraints, pd.DataFrame) else pd.DataFrame()
    if current.empty:
        current = pd.DataFrame(columns=["nutriente", "minimo", "maximo"])

    for column in ("nutriente", "minimo", "maximo"):
        if column not in current.columns:
            current[column] = None

    existing: dict[str, dict[str, object]] = {}
    for _, row in current.iterrows():
        code = str(row.get("nutriente") or "").strip()
        if code and code not in existing:
            existing[code] = row.to_dict()

    available = available_nutrient_codes(items)
    codes: list[str] = list(available)

    # Preserve an active restriction even if the composition is no longer
    # available after changing ingredients. Validation will explain the issue.
    for code, row in existing.items():
        if code in codes or code not in NUTRIENT_CODES:
            continue
        if as_float(row.get("minimo")) is not None or as_float(row.get("maximo")) is not None:
            codes.append(code)

    # Keep canonical registry order for known nutrients.
    order = {code: index for index, code in enumerate(NUTRIENT_CODES)}
    codes.sort(key=lambda code: order.get(code, len(order)))

    rows: list[dict[str, object]] = []
    for code in codes:
        old = existing.get(code, {})
        rows.append(
            {
                "nutriente": code,
                "minimo": as_float(old.get("minimo")),
                "maximo": as_float(old.get("maximo")),
            }
        )
    return pd.DataFrame(rows, columns=["nutriente", "minimo", "maximo"])


def constraint_codes(constraints: pd.DataFrame) -> list[str]:
    if constraints.empty or "nutriente" not in constraints.columns:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for value in constraints["nutriente"].tolist():
        code = str(value or "").strip()
        if code and code not in seen:
            seen.add(code)
            result.append(code)
    return result
