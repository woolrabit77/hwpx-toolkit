from __future__ import annotations

import argparse
from pathlib import Path

from hwpkit.validate import validate_hwpx


def validate(path: Path) -> list[str]:
    """Run the same strict validator used by the public HWPX tool."""

    return validate_hwpx(path, full=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hwpx", type=Path)
    args = parser.parse_args()

    errors = validate(args.hwpx)
    if errors:
        print("HWPX package validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("HWPX package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
