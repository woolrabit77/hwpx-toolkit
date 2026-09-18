from __future__ import annotations

import re


_QUOTED = re.compile(r'("(?:[^"\\]|\\.)*")')
_TOKEN = re.compile(
    r"(<=|>=|!=|==|<->|->|\\[A-Za-z]+|[A-Za-z가-힣]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[^\s])"
)
_OPERATORS = {"+", "-", "*", "/", "=", "<", ">", "<=", ">=", "!=", "==", "->", "<->", "+-"}


def normalize_equation(script: str) -> str:
    """Normalize independent tokens without splitting decimals or identifiers."""

    pieces = _QUOTED.split(script.strip())
    output: list[str] = []
    for index, piece in enumerate(pieces):
        if index % 2:
            output.append(piece)
            continue
        tokens = _TOKEN.findall(piece)
        normalized: list[str] = []
        for token in tokens:
            if token in _OPERATORS:
                normalized.extend([" ", token, " "])
            else:
                if normalized and normalized[-1] not in {" ", "{", "(", "[", "_", "^"}:
                    previous = normalized[-1]
                    if (
                        (previous[-1:].isdigit() and token[:1].isalpha())
                        or (previous[-1:].isalpha() and token[:1].isdigit())
                    ):
                        normalized.append(" ")
                normalized.append(token)
        output.append("".join(normalized))
    return re.sub(r"\s+", " ", "".join(output)).strip()


def estimate_equation_box(script: str, base_unit: int = 1000) -> tuple[int, int, int]:
    """Return deterministic width, height, and baseline in HWP units."""

    text = normalize_equation(script)
    visible = re.sub(r"\\?[A-Za-z]+|[{}]", "", text)
    operators = sum(1 for char in visible if char in "+-=<>*/")
    depth = max(_max_group_depth(text), 1)
    fractions = len(re.findall(r"\b(?:over|frac)\b", text, flags=re.IGNORECASE))
    roots = len(re.findall(r"\b(?:sqrt|root)\b", text, flags=re.IGNORECASE))
    matrices = len(re.findall(r"\b(?:matrix|cases)\b", text, flags=re.IGNORECASE))
    width_units = max(len(visible) * 540 + operators * 120 + roots * 300, 1000)
    height_factor = 1.15 + 0.42 * fractions + 0.15 * max(depth - 1, 0) + 0.8 * matrices
    height_units = max(int(base_unit * height_factor), base_unit)
    baseline = min(92, max(65, int(82 - fractions * 4 - matrices * 8)))
    return width_units, height_units, baseline


def _max_group_depth(text: str) -> int:
    depth = maximum = 0
    for char in text:
        if char in "{([":
            depth += 1
            maximum = max(maximum, depth)
        elif char in "})]":
            depth = max(0, depth - 1)
    return maximum

