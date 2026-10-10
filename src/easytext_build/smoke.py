"""Smoke-Test: gebaute Datei laden, Gruppen prüfen, Test-Gruppe als Modifier evaluieren."""

from __future__ import annotations

import sys

from . import paths
from .groups import registry


def main() -> int:
    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(paths.BLEND_FILE))
    errors: list[str] = []

    for name in registry.names():
        tree = bpy.data.node_groups.get(name)
        if tree is None:
            errors.append(f"Gruppe fehlt: {name}")
            continue
        for node in tree.nodes:
            if node.bl_idname == "NodeUndefined":
                errors.append(f"{name}: undefinierter Node {node.name!r}")
        if tree.asset_data is None:
            errors.append(f"{name}: nicht als Asset markiert")

    mesh = bpy.data.meshes.new("smoke")
    obj = bpy.data.objects.new("smoke", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new("EasyText", "NODES")
    mod.node_group = bpy.data.node_groups["ET Smoke Test"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    evaluated = obj.evaluated_get(depsgraph)
    verts = len(evaluated.data.vertices)
    faces = len(evaluated.data.polygons)
    warnings = [(w.type, w.message) for w in getattr(mod, "node_warnings", [])]
    print(f"[smoke] ET Smoke Test: {verts} Vertices, {faces} Faces, Warnungen: {warnings or 'keine'}")
    if verts == 0:
        errors.append("ET Smoke Test erzeugt keine Geometrie")
    if any(w[0] == "ERROR" for w in warnings):
        errors.append(f"Modifier meldet Fehler: {warnings}")

    if errors:
        print("[smoke] FEHLER:\n  " + "\n  ".join(errors))
        return 1
    print("[smoke] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
