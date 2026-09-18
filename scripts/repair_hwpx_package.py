from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import BadZipFile

from check_hwpx_package import validate
from hwpx_package import repack_hwpx


def repair(source: Path, output: Path, *, overwrite: bool = False) -> list[str]:
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists; use --overwrite to replace it: {output}")
    repack_hwpx(source, output)
    return validate(output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Repair ZIP ordering/compression and write atomically. This does not invent "
            "missing XML or repair malformed document structures."
        )
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        errors = repair(args.source, args.output, overwrite=args.overwrite)
    except (OSError, ValueError, BadZipFile) as exc:
        print(f"Repair failed: {exc}")
        return 1

    if errors:
        print(f"Repacked HWPX, but structural validation still fails: {args.output}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Repaired and validated HWPX package: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
