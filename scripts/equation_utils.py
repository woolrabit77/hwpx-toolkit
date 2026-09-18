from __future__ import annotations

import re


_QUOTED_TEXT = re.compile(r'("(?:[^"\\]|\\.)*")')
_MULTI_OPERATORS = re.compile(r"(<->|->|<=|>=|!=|==|\+-)")
_SINGLE_OPERATORS = re.compile(r"(?<![<>=!+\-])([+=<>\-*/])(?![<>=+\-])")


def normalize_equation_script(script: str) -> str:
    """Normalize token boundaries without changing quoted text.

    HWP equation commands are whitespace-insensitive in the places handled
    here. Braces remain attached to commands, while operators, numeric/letter
    boundaries, and a closing brace followed by an operand are separated.
    """

    parts = _QUOTED_TEXT.split(script)
    normalized: list[str] = []
    for index, part in enumerate(parts):
        if index % 2:
            normalized.append(part)
            continue

        text = re.sub(r"\s+", " ", part)
        text = re.sub(r"([_^])\s*(-?\d+)", r"\1rm{\2}", text)
        text = _MULTI_OPERATORS.sub(r" \1 ", text)
        text = _SINGLE_OPERATORS.sub(r" \1 ", text)
        text = re.sub(r"(?<=\d)(?=[A-Za-z가-힣])", " ", text)
        text = re.sub(r"(?<=[A-Za-z가-힣}])(?=\d)", " ", text)
        text = re.sub(r"(?<=})(?=[A-Za-z가-힣])", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        normalized.append(text)

    return "".join(normalized).strip()


def has_normalized_spacing(script: str) -> bool:
    return normalize_equation_script(script) == script.strip()
