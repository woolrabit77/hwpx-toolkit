from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile, ZipInfo


MIMETYPE_NAME = "mimetype"
MIMETYPE_VALUE = b"application/hwp+zip"
REQUIRED_ENTRIES = {
    MIMETYPE_NAME,
    "Contents/header.xml",
    "Contents/section0.xml",
    "Contents/content.hpf",
    "META-INF/container.xml",
    "Preview/PrvText.txt",
}


def safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and "\\" not in name and not path.is_absolute() and ".." not in path.parts


def write_package(parts: dict[str, bytes], output: Path) -> None:
    missing = REQUIRED_ENTRIES - ({MIMETYPE_NAME} | set(parts))
    if missing:
        raise ValueError(f"Required package entries are missing: {', '.join(sorted(missing))}")
    if any(not safe_name(name) for name in parts):
        raise ValueError("The package contains an unsafe entry path.")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    try:
        with ZipFile(temporary, "w", allowZip64=True) as archive:
            mime = ZipInfo(MIMETYPE_NAME)
            mime.compress_type = ZIP_STORED
            archive.writestr(mime, MIMETYPE_VALUE)
            for name in sorted(parts, key=_package_sort_key):
                info = ZipInfo(name)
                info.compress_type = ZIP_DEFLATED
                archive.writestr(info, parts[name])
        with ZipFile(temporary) as archive:
            infos = archive.infolist()
            if not infos or infos[0].filename != MIMETYPE_NAME or infos[0].compress_type != ZIP_STORED:
                raise BadZipFile("The mimetype entry order or compression method is invalid.")
            if archive.read(MIMETYPE_NAME) != MIMETYPE_VALUE:
                raise BadZipFile("The mimetype value is invalid.")
            bad = archive.testzip()
            if bad:
                raise BadZipFile(f"CRC verification failed: {bad}")
        os.replace(temporary, output)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass


def _package_sort_key(name: str) -> tuple[int, str]:
    order = {
        "META-INF/container.xml": 0,
        "Contents/content.hpf": 1,
        "Contents/header.xml": 2,
        "Contents/section0.xml": 3,
        "Preview/PrvText.txt": 4,
    }
    return order.get(name, 10), name
