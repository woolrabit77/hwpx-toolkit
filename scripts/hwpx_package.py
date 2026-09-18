from __future__ import annotations

import os
import tempfile
from copy import copy
from pathlib import Path, PurePosixPath
from typing import Mapping
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile, ZipInfo


MIMETYPE_NAME = "mimetype"
MIMETYPE_VALUE = b"application/hwp+zip"
REQUIRED_ENTRIES = (
    MIMETYPE_NAME,
    "Contents/header.xml",
    "Contents/section0.xml",
    "Contents/content.hpf",
    "META-INF/container.xml",
    "Preview/PrvText.txt",
)


def is_safe_member_name(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/"):
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def _copy_info(info: ZipInfo, *, compress_type: int) -> ZipInfo:
    cloned = copy(info)
    cloned.compress_type = compress_type
    cloned.flag_bits &= 0x800  # preserve only the UTF-8 filename flag
    return cloned


def repack_hwpx(
    source: Path,
    output: Path,
    *,
    replacements: Mapping[str, bytes] | None = None,
) -> None:
    """Atomically repack an HWPX while preserving all non-replaced members.

    The source is never modified. The output is replaced only after a complete
    temporary ZIP has been written and reopened successfully.
    """

    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("Refusing to overwrite the source HWPX; choose a separate output path.")
    if not source.is_file():
        raise FileNotFoundError(source)

    replacements = dict(replacements or {})
    for name in replacements:
        if name == MIMETYPE_NAME:
            raise ValueError("mimetype is managed by repack_hwpx and cannot be replaced.")
        if not is_safe_member_name(name):
            raise ValueError(f"Unsafe replacement member name: {name!r}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with ZipFile(source) as src:
            bad_member = src.testzip()
            if bad_member:
                raise BadZipFile(f"CRC check failed for {bad_member}")

            infos = src.infolist()
            names = [info.filename for info in infos]
            duplicates = sorted({name for name in names if names.count(name) > 1})
            if duplicates:
                raise BadZipFile(f"Duplicate ZIP entries: {', '.join(duplicates)}")
            unsafe = [name for name in names if not is_safe_member_name(name)]
            if unsafe:
                raise BadZipFile(f"Unsafe ZIP member names: {', '.join(unsafe)}")
            encrypted = [info.filename for info in infos if info.flag_bits & 0x1]
            if encrypted:
                raise BadZipFile(f"Encrypted ZIP members are unsupported: {', '.join(encrypted)}")

            fd, temp_name = tempfile.mkstemp(
                prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
            )
            os.close(fd)
            with ZipFile(temp_name, "w", allowZip64=True) as dst:
                mime_info = ZipInfo(MIMETYPE_NAME)
                mime_info.compress_type = ZIP_STORED
                dst.writestr(mime_info, MIMETYPE_VALUE)

                written: set[str] = {MIMETYPE_NAME}
                for info in infos:
                    name = info.filename
                    if name == MIMETYPE_NAME:
                        continue
                    data = replacements.pop(name, src.read(name))
                    compress_type = ZIP_STORED if info.is_dir() else ZIP_DEFLATED
                    dst.writestr(_copy_info(info, compress_type=compress_type), data)
                    written.add(name)

                for name, data in replacements.items():
                    info = ZipInfo(name)
                    info.compress_type = ZIP_DEFLATED
                    dst.writestr(info, data)
                    written.add(name)

        with ZipFile(temp_name) as check:
            infos = check.infolist()
            if not infos or infos[0].filename != MIMETYPE_NAME:
                raise BadZipFile("Temporary output does not start with mimetype.")
            if infos[0].compress_type != ZIP_STORED:
                raise BadZipFile("Temporary output compressed the mimetype entry.")
            if check.read(MIMETYPE_NAME) != MIMETYPE_VALUE:
                raise BadZipFile("Temporary output has an invalid mimetype payload.")
            bad_member = check.testzip()
            if bad_member:
                raise BadZipFile(f"Temporary output CRC check failed for {bad_member}")

        os.replace(temp_name, output)
        temp_name = None
    finally:
        if temp_name:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass
