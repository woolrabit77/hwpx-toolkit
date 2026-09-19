from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo


SKILL_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "hwp-hwpx-document-automation"
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp"}
FIXED_TIME = (2020, 1, 1, 0, 0, 0)


def export_skill(output: Path) -> dict[str, object]:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [path for path in sorted(SKILL_ROOT.rglob("*")) if _include(path, output)]
    if not any(path.name == "SKILL.md" for path in files):
        raise RuntimeError("SKILL.md is missing from the export set.")

    temporary = output.with_name(f".{output.name}.tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                relative = path.relative_to(SKILL_ROOT).as_posix()
                info = ZipInfo(f"{ARCHIVE_ROOT}/{relative}", date_time=FIXED_TIME)
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        with ZipFile(temporary) as archive:
            bad = archive.testzip()
            if bad:
                raise BadZipFile(f"CRC verification failed: {bad}")
            names = set(archive.namelist())
            required = {
                f"{ARCHIVE_ROOT}/SKILL.md",
                f"{ARCHIVE_ROOT}/scripts/hwpx_tool.py",
                f"{ARCHIVE_ROOT}/assets/templates/specs/official-letter.json",
            }
            missing = sorted(required - names)
            if missing:
                raise BadZipFile(f"Required export entries are missing: {', '.join(missing)}")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "output": str(output),
        "files": len(files),
        "bytes": output.stat().st_size,
        "sha256": digest,
        "validation": "passed",
    }


def _include(path: Path, output: Path) -> bool:
    if not path.is_file() or path.resolve() == output:
        return False
    relative = path.relative_to(SKILL_ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.suffix.lower() == ".zip":
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the standalone HWPX skill as a deterministic ZIP archive.")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_skill(args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
