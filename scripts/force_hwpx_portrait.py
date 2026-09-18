from __future__ import annotations

import argparse
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from check_hwpx_package import validate
from hwpx_package import repack_hwpx


PAGE_PR_RE = re.compile(r"(<(?:\w+:)?pagePr\b[^>]*)(/?>)", re.IGNORECASE)


def set_attr(tag_start: str, name: str, value: str) -> str:
    pattern = re.compile(rf'\b{name}="[^"]*"')
    replacement = f'{name}="{value}"'
    if pattern.search(tag_start):
        return pattern.sub(replacement, tag_start, count=1)
    return f"{tag_start} {replacement}"


def force_section_portrait(xml_text: str, clear_layout_cache: bool = True) -> str:
    def replace_page_pr(match: re.Match[str]) -> str:
        tag_start, tag_end = match.groups()
        tag_start = set_attr(tag_start, "landscape", "WIDELY")
        tag_start = set_attr(tag_start, "width", "59528")
        tag_start = set_attr(tag_start, "height", "84186")
        return tag_start + tag_end

    xml_text = PAGE_PR_RE.sub(replace_page_pr, xml_text)
    if clear_layout_cache:
        xml_text = re.sub(
            r"<(?:\w+:)?linesegarray\b[^>]*>.*?</(?:\w+:)?linesegarray>",
            "",
            xml_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        xml_text = re.sub(
            r"<(?:\w+:)?linesegarray\b[^>]*/>",
            "",
            xml_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return xml_text


def force_portrait(source: Path, output: Path, clear_layout_cache: bool = True) -> None:
    replacements: dict[str, bytes] = {}
    with ZipFile(source) as src:
        for info in src.infolist():
            if info.filename.startswith("Contents/section") and info.filename.endswith(".xml"):
                text = src.read(info.filename).decode("utf-8-sig")
                text = force_section_portrait(text, clear_layout_cache=clear_layout_cache)
                ET.fromstring(text)
                replacements[info.filename] = text.encode("utf-8")
    repack_hwpx(source, output, replacements=replacements)
    errors = validate(output)
    if errors:
        raise ValueError("Portrait output failed validation: " + "; ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--keep-layout-cache",
        action="store_true",
        help="Keep hp:linesegarray layout cache instead of removing it.",
    )
    args = parser.parse_args()

    force_portrait(
        args.source,
        args.output,
        clear_layout_cache=not args.keep_layout_cache,
    )
    print(f"Wrote portrait HWPX: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
