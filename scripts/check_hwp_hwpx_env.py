from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None


MODULES = ["PIL", "lxml", "win32com", "olefile", "yaml"]


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def has_hwp_com_registration() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"HWPFrame.HwpObject\CLSID"):
            return True
    except OSError:
        return False


def test_image_pipeline() -> tuple[bool, str]:
    if not has_module("PIL"):
        return False, "Pillow(PIL) is not available."

    from PIL import Image, ImageDraw

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        image_path = root / "sample.png"
        package_path = root / "sample.hwpx"

        image = Image.new("RGB", (320, 180), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 300, 160), outline="black", width=3)
        draw.text((42, 78), "HWPX image test", fill="black")
        image.save(image_path)

        with Image.open(image_path) as opened:
            opened.verify()

        with Image.open(image_path) as opened:
            if opened.format != "PNG" or opened.size != (320, 180):
                return False, "Generated PNG did not round-trip with expected metadata."

        with ZipFile(package_path, "w") as zf:
            zf.writestr("mimetype", "application/hwp+zip", compress_type=ZIP_STORED)
            zf.writestr(
                "Contents/section0.xml",
                '<section><image href="BinData/sample.png"/></section>',
                compress_type=ZIP_DEFLATED,
            )
            zf.write(image_path, "BinData/sample.png")

        with ZipFile(package_path) as zf:
            names = set(zf.namelist())
            if "BinData/sample.png" not in names:
                return False, "Image was not packaged under BinData/."
            if zf.infolist()[0].filename != "mimetype":
                return False, "mimetype is not the first package entry."
            if zf.getinfo("mimetype").compress_type != ZIP_STORED:
                return False, "mimetype is compressed."
            if zf.getinfo("BinData/sample.png").file_size <= 0:
                return False, "Packaged image is empty."

    return True, "Pillow image verification and BinData packaging test passed."


def main() -> int:
    print("Python module availability:")
    for module in MODULES:
        print(f"- {module}: {has_module(module)}")
    print(f"Hancom COM ProgID registered: {has_hwp_com_registration()}")

    ok, message = test_image_pipeline()
    print(f"Image pipeline: {ok} - {message}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
