from __future__ import annotations

import re
from statistics import fmean

from .errors import SpecError


_TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z]+\d+)|([A-Za-z]+)|([()+\-*/, :]))")
_CELL = re.compile(r"^([A-Z]+)(\d+)$")
_FUNCTIONS = {"SUM", "AVERAGE", "PRODUCT", "MIN", "MAX"}


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


class _FormulaParser:
    """Small, strict formula parser; intentionally never evaluates code."""

    def __init__(self, formula: str, rows: list[list[object]], resolving: set[tuple[int, int]] | None = None):
        self.formula = formula.strip()
        self.rows = rows
        self.resolving = resolving if resolving is not None else set()
        self.tokens = self._tokenize(formula)
        self.index = 0

    @staticmethod
    def _tokenize(formula: str) -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = []
        position = 0
        formula = formula.strip()
        while position < len(formula):
            match = _TOKEN.match(formula, position)
            if not match:
                raise SpecError(f"Unsupported table formula: {formula}")
            position = match.end()
            groups = match.groups()
            kind = "number" if groups[0] else "cell" if groups[1] else "name" if groups[2] else "symbol"
            tokens.append((kind, next(value for value in groups if value is not None)))
        tokens.append(("eof", ""))
        return tokens

    def peek(self, value: str | None = None) -> tuple[str, str] | bool:
        token = self.tokens[self.index]
        return token == ("symbol", value) if value is not None else token

    def take(self, kind: str | None = None, value: str | None = None) -> str:
        token_kind, token_value = self.tokens[self.index]
        if (kind is not None and token_kind != kind) or (value is not None and token_value != value):
            raise SpecError(f"Unsupported table formula: {self.formula}")
        self.index += 1
        return token_value

    def parse(self) -> float:
        result = self.expression()
        if self.tokens[self.index][0] != "eof":
            raise SpecError(f"Unsupported table formula: {self.formula}")
        return result

    def expression(self) -> float:
        result = self.term()
        while self.peek("+") or self.peek("-"):
            operator = self.take("symbol")
            rhs = self.term()
            result = result + rhs if operator == "+" else result - rhs
        return result

    def term(self) -> float:
        result = self.factor()
        while self.peek("*") or self.peek("/"):
            operator = self.take("symbol")
            rhs = self.factor()
            if operator == "/":
                if rhs == 0:
                    raise SpecError("Table formula division by zero.")
                result /= rhs
            else:
                result *= rhs
        return result

    def factor(self) -> float:
        if self.peek("+") or self.peek("-"):
            operator = self.take("symbol")
            value = self.factor()
            return value if operator == "+" else -value
        if self.peek("("):
            self.take("symbol", "(")
            value = self.expression()
            self.take("symbol", ")")
            return value
        kind, value = self.tokens[self.index]
        if kind == "number":
            self.index += 1
            return float(value)
        if kind == "name":
            name = self.take("name").upper()
            if name not in _FUNCTIONS:
                raise SpecError(f"Unsupported table formula function: {name}")
            self.take("symbol", "(")
            values: list[float] = []
            while True:
                values.extend(self.argument_values())
                if self.peek(","):
                    self.take("symbol", ",")
                    continue
                break
            self.take("symbol", ")")
            if not values:
                return 0.0
            if name == "SUM":
                return sum(values)
            if name == "AVERAGE":
                return fmean(values)
            if name == "PRODUCT":
                product = 1.0
                for item in values:
                    product *= item
                return product
            return min(values) if name == "MIN" else max(values)
        if kind == "cell":
            self.index += 1
            return self.cell_value(value)
        raise SpecError(f"Unsupported table formula: {self.formula}")

    def argument_values(self) -> list[float]:
        kind, value = self.tokens[self.index]
        if kind == "cell":
            self.index += 1
            start = parse_cell(value)
            if self.peek(":"):
                self.take("symbol", ":")
                end = self.take("cell")
                return self.range_values(start, parse_cell(end))
            return [self.cell_value(value)]
        return [self.expression()]

    def range_values(self, start: tuple[int, int], end: tuple[int, int]) -> list[float]:
        r1, c1 = start
        r2, c2 = end
        if r1 > r2 or c1 > c2:
            raise SpecError("Reverse cell ranges are not supported.")
        values: list[float] = []
        for row_index in range(r1, r2 + 1):
            for col_index in range(c1, c2 + 1):
                raw = self.raw_cell(row_index, col_index)
                if raw in (None, ""):
                    continue
                values.append(self.coerce(raw, f"{row_index + 1},{col_index + 1}"))
        return values

    def raw_cell(self, row_index: int, col_index: int) -> object:
        try:
            raw = self.rows[row_index][col_index]
        except IndexError as exc:
            raise SpecError("Table formula range points outside the data.") from exc
        if isinstance(raw, dict) and raw.get("covered"):
            raise SpecError("Table formula cannot reference a covered cell of a merged span.")
        if isinstance(raw, dict) and raw.get("formula"):
            key = (row_index, col_index)
            if key in self.resolving:
                raise SpecError("Table formula contains a circular reference.")
            self.resolving.add(key)
            try:
                value = evaluate_formula(str(raw["formula"]), self.rows, _resolving=self.resolving)
            finally:
                self.resolving.remove(key)
            raw["value"] = value
            return value
        if isinstance(raw, dict):
            raw = raw.get("value", "")
        return raw

    def cell_value(self, address: str) -> float:
        row_index, col_index = parse_cell(address)
        raw = self.raw_cell(row_index, col_index)
        if raw in (None, ""):
            raise SpecError(f"Cannot calculate an empty cell: {address}")
        return self.coerce(raw, address)

    @staticmethod
    def coerce(raw: object, address: str) -> float:
        try:
            return float(str(raw).replace(",", ""))
        except (TypeError, ValueError) as exc:
            raise SpecError(f"Cannot calculate a non-numeric cell at {address}: {raw!r}") from exc


def evaluate_formula(
    formula: str,
    rows: list[list[object]],
    *,
    _resolving: set[tuple[int, int]] | None = None,
) -> float:
    if not isinstance(formula, str) or not formula.strip():
        raise SpecError("Table formula must be a non-empty string.")
    return _FormulaParser(formula, rows, _resolving).parse()
