"""Central repository paths."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "assets"
BLEND_FILE = ASSET_DIR / "easytext_v3.blend"
DEMO_FILE = ASSET_DIR / "easytext_v3_demo.blend"
CATALOG_FILE = ASSET_DIR / "blender_assets.cats.txt"
SNAPSHOT_DIR = ASSET_DIR / "snapshots"
