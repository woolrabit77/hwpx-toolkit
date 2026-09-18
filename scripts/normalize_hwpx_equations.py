from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, unescape

from equation_utils import normalize_equation_script
from hwpx_package import repack_hwpx


EQUATION_RE = re.compile(
    r"<(?P<prefix>[A-Za-z_][\w.-]*):equation\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)</(?P=prefix):equation>",
    re.DOTALL,
)


def _set_attr(tag: str, name: str, value: str) -> str:
    pattern = re.compile(rf'\b{re.escape(name)}="[^"]*"')
    replacement = f'{name}="{value}"'
    if pattern.search(tag):
        return pattern.sub(replacement, tag, count=1)
    return tag[:-1] + f" {replacement}>"


def _update_empty_tag(body: str, prefix: str, tag_name: str, attrs: dict[str, str]) -> tuple[str, bool]:
    pattern = re.compile(rf"<({re.escape(prefix)}:{tag_name})\b[^>]*/>", re.DOTALL)
    match = pattern.search(body)
    if not match:
        return body, False
    tag = match.group(0)
    for name, value in attrs.items():
        tag = _set_attr(tag, name, value)
    return body[: match.start()] + tag + body[match.end() :], True


def normalize_section(
    xml_text: str,
    *,
    auto_size: bool,
    normalize_spacing: bool,
) -> tuple[str, int, int, list[str]]:
    equation_count = 0
    changed_count = 0
    warnings: list[str] = []

    def replace_equation(match: re.Match[str]) -> str:
        nonlocal equation_count, changed_count
        equation_count += 1
        prefix = match.group("prefix")
        opening = match.group(0)[: match.group(0).find(">") + 1]
        body = match.group("body")
        original = match.group(0)

        opening = _set_attr(opening, "lineMode", "CHAR")
        if not re.search(r'\bbaseLine="[^"]*"', opening):
            opening = _set_attr(opening, "baseLine", "85")
        if not re.search(r'\bbaseUnit="[^"]*"', opening):
            opening = _set_attr(opening, "baseUnit", "1000")

        if auto_size:
            body, found = _update_empty_tag(
                body,
                prefix,
                "sz",
                {
                    "width": "0",
                    "widthRelTo": "ABSOLUTE",
                    "height": "0",
                    "heightRelTo": "ABSOLUTE",
                    "protect": "0",
                },
            )
            if not found:
                warnings.append(f"equation #{equation_count}: missing {prefix}:sz; size was not reset")

        body, found = _update_empty_tag(
            body,
            prefix,
            "pos",
            {
                "treatAsChar": "1",
                "affectLSpacing": "0",
                "flowWithText": "1",
                "allowOverlap": "0",
                "vertRelTo": "PARA",
                "horzRelTo": "PARA",
            },
        )
        if not found:
            warnings.append(f"equation #{equation_count}: missing {prefix}:pos")

        body, _ = _update_empty_tag(
            body,
            prefix,
            "outMargin",
            {"top": "0", "bottom": "0"},
        )

        if normalize_spacing:
            script_re = re.compile(
                rf"<({re.escape(prefix)}:script)\b(?P<attrs>[^>]*)>"
                rf"(?P<text>.*?)</{re.escape(prefix)}:script>",
                re.DOTALL,
            )
            script_match = script_re.search(body)
            if script_match:
                raw_text = unescape(script_match.group("text"))
                normalized = normalize_equation_script(raw_text)
                escaped = escape(normalized)
                replacement = (
                    f"<{script_match.group(1)}{script_match.group('attrs')}>"
                    f"{escaped}</{prefix}:script>"
                )
                body = body[: script_match.start()] + replacement + body[script_match.end() :]
            else:
                warnings.append(f"equation #{equation_count}: missing {prefix}:script")

        updated = opening + body + f"</{prefix}:equation>"
        if updated != original:
            changed_count += 1
        return updated

    updated = EQUATION_RE.sub(replace_equation, xml_text)
    ET.fromstring(updated)
    return updated, equation_count, changed_count, warnings


def normalize_hwpx(source: Path, output: Path, *, auto_size: bool, normalize_spacing: bool) -> tuple[int, int, list[str]]:
    from zipfile import ZipFile

    replacements: dict[str, bytes] = {}
    total = 0
    changed = 0
    warnings: list[str] = []
    with ZipFile(source) as zf:
        section_names = [
            name
            for name in zf.namelist()
            if name.startswith("Contents/section") and name.endswith(".xml")
        ]
        for name in section_names:
            text = zf.read(name).decode("utf-8-sig")
            updated, count, changed_count, section_warnings = normalize_section(
                text,
                auto_size=auto_size,
                normalize_spacing=normalize_spacing,
            )
            total += count
            changed += changed_count
            warnings.extend(f"{name}: {warning}" for warning in section_warnings)
            if updated != text:
                replacements[name] = updated.encode("utf-8")

    repack_hwpx(source, output, replacements=replacements)
    return total, changed, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--keep-fixed-size", action="store_true")
    parser.add_argument("--keep-script-spacing", action="store_true")
    args = parser.parse_args()

    total, changed, warnings = normalize_hwpx(
        args.source,
        args.output,
        auto_size=not args.keep_fixed_size,
        normalize_spacing=not args.keep_script_spacing,
    )
    print(f"Normalized {changed} of {total} equation objects: {args.output}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
