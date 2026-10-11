"""System fonts for the font picker: scan the OS font folders, load a file as a VectorFont on demand."""

from __future__ import annotations

import os
import pathlib
import sys

import bpy

FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
_cache: list[tuple[str, str]] = []  # (path, display name); kept alive for the dynamic enum
_enum_items: list[tuple[str, str, str]] = []


def font_dirs() -> list[pathlib.Path]:
    home = pathlib.Path.home()
    if sys.platform.startswith("win"):
        dirs = [
            pathlib.Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
            home / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
        ]
    elif sys.platform == "darwin":
        dirs = [pathlib.Path("/System/Library/Fonts"), pathlib.Path("/Library/Fonts"), home / "Library" / "Fonts"]
    else:
        dirs = [
            pathlib.Path("/usr/share/fonts"),
            pathlib.Path("/usr/local/share/fonts"),
            home / ".fonts",
            home / ".local" / "share" / "fonts",
        ]
    dirs.append(pathlib.Path(bpy.utils.system_resource("DATAFILES", path="fonts")))  # Blender's own fonts
    return [d for d in dirs if d.is_dir()]


def display_name(path: pathlib.Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ")


def system_fonts(refresh: bool = False) -> list[tuple[str, str]]:
    """(path, display name) for every font file in the font folders, sorted by name."""
    if _cache and not refresh:
        return _cache
    found: dict[str, str] = {}
    for base in font_dirs():
        for root, _dirs, files in os.walk(base):
            if root[len(str(base)) :].count(os.sep) > 3:
                continue
            for file in files:
                if pathlib.Path(file).suffix.lower() in FONT_EXTENSIONS:
                    path = pathlib.Path(root) / file
                    found[str(path)] = display_name(path)
    _cache[:] = sorted(found.items(), key=lambda item: item[1].lower())
    return _cache


def enum_items(_self, _context) -> list[tuple[str, str, str]]:
    """Items for an EnumProperty; the list is cached because Blender keeps only a reference."""
    if not _enum_items:
        _enum_items[:] = [(path, name, path) for path, name in system_fonts()] or [("", "No fonts found", "")]
    return _enum_items


def load_font(path: str) -> bpy.types.VectorFont:
    font = bpy.data.fonts.load(path, check_existing=True)  # 5.2 names the data-block from the font's metadata
    font.use_fake_user = True
    return font
