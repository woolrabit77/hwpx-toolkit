from __future__ import annotations

import re
from statistics import fmean

from .errors import SpecError


_FORMULA = re.compile(r"^\s*(SUM|AVERAGE|PRODUCT|MIN|MAX)\(([^)]+)\)\s*$", re.IGNORECASE)
_CELL = re.compile(r"^([A-Z]+)(\d+)$")


def column_index(letters: str) -> int:
    value = 0
    for char in letters.upper():
        if not "A" <= char <= "Z":
            raise SpecError(f"Invalid table column name: {letters}")
        value = value * 26 + ord(char) - 64
    return value - 1


def parse_cell(address: str) -> tuple[int, int]:
    match = _CELL.match(address.strip().upper())
    if not match:
        raise SpecError(f"Invalid cell address: {address}")
    return int(match.group(2)) - 1, column_index(match.group(1))


def evaluate_formula(formula: str, rows: list[list[object]]) -> float:
    match = _FORMULA.match(formula)
    if not match:
        raise SpecError(f"Unsupported table formula: {formula}")
    function = match.group(1).upper()
    range_text = match.group(2).strip()
    if ":" in range_text:
        start_text, end_text = range_text.split(":", 1)
    else:
        start_text = end_text = range_text
    r1, c1 = parse_cell(start_text)
    r2, c2 = parse_cell(end_text)
    if r1 > r2 or c1 > c2:
        raise SpecError(f"Reverse cell ranges are not supported: {range_text}")
    values: list[float] = []
    for row_index in range(r1, r2 + 1):
        for col_index_ in range(c1, c2 + 1):
            try:
                raw = rows[row_index][col_index_]
            except IndexError as exc:
                raise SpecError(f"Table range points outside the data: {range_text}") from exc
            if isinstance(raw, dict):
                raw = raw.get("value", "")
            if raw in (None, ""):
                continue
            try:
                values.append(float(str(raw).replace(",", "")))
            except ValueError as exc:
                raise SpecError(f"Cannot calculate a non-numeric cell: {raw!r}") from exc
    if not values:
        return 0.0
    if function == "SUM":
        return sum(values)
    if function == "AVERAGE":
        return fmean(values)
    if function == "PRODUCT":
        product = 1.0
        for value in values:
            product *= value
        return product
    if function == "MIN":
        return min(values)
    return max(values)
