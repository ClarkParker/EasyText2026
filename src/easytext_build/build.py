"""Baut assets/easytext_v3.blend, den Asset-Katalog und die JSON-Snapshots.

Aufruf: python -m easytext_build.build   (mit installiertem bpy-Wheel)
   oder: blender -b --python-expr \
         "import sys; sys.path.insert(0, 'src'); import easytext_build.build as b; b.main()"
"""

from __future__ import annotations

import json
import sys

from . import catalog, demo, paths, snapshot
from .groups import registry


def main() -> int:
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    trees = registry.build_all()

    paths.ASSET_DIR.mkdir(exist_ok=True)
    paths.SNAPSHOT_DIR.mkdir(exist_ok=True)
    catalog.write(paths.CATALOG_FILE)

    expected = {f"{t.name}.json" for t in trees}
    for stale in paths.SNAPSHOT_DIR.glob("*.json"):
        if stale.name not in expected:
            stale.unlink()
    for tree in trees:
        data = snapshot.tree_to_dict(tree)
        text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
        (paths.SNAPSHOT_DIR / f"{tree.name}.json").write_text(text, encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(paths.BLEND_FILE), compress=True)
    print(
        f"[build] {len(trees)} Gruppen -> {paths.BLEND_FILE.relative_to(paths.ROOT)} (Blender {bpy.app.version_string})"
    )
    demo.populate_scene(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=str(paths.DEMO_FILE), compress=True)
    print(f"[build] Demo-Szene -> {paths.DEMO_FILE.relative_to(paths.ROOT)}")
    for tree in trees:
        print(f"[build]   {tree.name}: {len(tree.nodes)} Nodes, {len(tree.links)} Links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
