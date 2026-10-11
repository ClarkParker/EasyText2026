"""Package the add-on: copy the built asset file into the extension folder and zip it for installation.

Run: python -m easytext_build.package            -> dist/easy_text-<version>.zip
The zip has blender_manifest.toml at its root, as Blender's extension installer expects. With a Blender binary
at hand, `blender --command extension build --source-dir extension/easy_text --output-dir dist` validates the
manifest as well (see docs/03-development.md)."""

from __future__ import annotations

import re
import shutil
import sys
import zipfile

from . import paths

EXTENSION_DIR = paths.ROOT / "extension" / "easy_text"
DIST_DIR = paths.ROOT / "dist"
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc", ".zip"}


def version() -> str:
    text = (EXTENSION_DIR / "blender_manifest.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if match is None:
        raise ValueError("no version in blender_manifest.toml")
    return match.group(1)


def copy_assets() -> None:
    target = EXTENSION_DIR / "assets"
    target.mkdir(exist_ok=True)
    shutil.copy2(paths.BLEND_FILE, target / paths.BLEND_FILE.name)
    shutil.copy2(paths.ASSET_DIR / "LICENSE", target / "LICENSE")


def build_zip() -> paths.Path:
    DIST_DIR.mkdir(exist_ok=True)
    out = DIST_DIR / f"easy_text-{version()}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(EXTENSION_DIR.rglob("*")):
            if not file.is_file():
                continue
            if EXCLUDE_DIRS & set(file.relative_to(EXTENSION_DIR).parts) or file.suffix in EXCLUDE_SUFFIXES:
                continue
            zf.write(file, file.relative_to(EXTENSION_DIR).as_posix())
    return out


def main() -> int:
    if not paths.BLEND_FILE.exists():
        print(f"[package] build the assets first: {paths.BLEND_FILE} is missing")
        return 1
    copy_assets()
    out = build_zip()
    size = out.stat().st_size / 1e6
    print(f"[package] {out.relative_to(paths.ROOT)} ({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
