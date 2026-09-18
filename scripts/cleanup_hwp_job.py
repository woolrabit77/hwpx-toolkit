from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


MARKER = ".hwp-workdir.json"
MARKER_KIND = "hwp-hwpx-workdir"


def init_workdir(root: Path) -> None:
    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Work directory must be empty before initialization: {root}")
    root.mkdir(parents=True, exist_ok=True)
    marker = {"kind": MARKER_KIND, "version": 1}
    (root / MARKER).write_text(json.dumps(marker, indent=2), encoding="utf-8")
    print(f"Initialized HWP work directory: {root}")


def _validated_root(root: Path) -> Path:
    root = root.resolve()
    cwd = Path.cwd().resolve()
    if root == root.anchor or root == cwd or root == cwd.parent or root == Path.home().resolve():
        raise ValueError(f"Refusing broad cleanup target: {root}")
    marker_path = root / MARKER
    if not marker_path.is_file():
        raise ValueError(f"Missing cleanup marker: {marker_path}")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("kind") != MARKER_KIND:
        raise ValueError(f"Invalid cleanup marker: {marker_path}")
    return root


def cleanup(root: Path, *, apply: bool) -> None:
    root = _validated_root(root)
    targets = sorted(
        (path for path in root.iterdir() if path.name != MARKER),
        key=lambda path: path.name.lower(),
    )
    if not targets:
        print("No intermediate files found.")
        return

    print("Intermediate cleanup targets:")
    for target in targets:
        print(f"- {target}")

    if not apply:
        print("Dry run only. Re-run with --apply after explicit user approval.")
        return

    for target in targets:
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
    print(f"Removed {len(targets)} intermediate target(s); marker retained in {root}.")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("root", type=Path)

    clean_parser = subparsers.add_parser("clean")
    clean_parser.add_argument("root", type=Path)
    clean_parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    if args.command == "init":
        init_workdir(args.root)
    else:
        cleanup(args.root, apply=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
