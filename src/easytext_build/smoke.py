"""Smoke test: load the built file, check the groups, evaluate the main group as a modifier."""

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
            errors.append(f"missing group: {name}")
            continue
        for node in tree.nodes:
            if node.bl_idname == "NodeUndefined":
                errors.append(f"{name}: undefined node {node.name!r}")
        if tree.asset_data is None and not name.startswith("."):
            errors.append(f"{name}: not marked as asset")

    mesh = bpy.data.meshes.new("smoke")
    obj = bpy.data.objects.new("smoke", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new("EasyText", "NODES")
    mod.node_group = bpy.data.node_groups[registry.MAIN]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    evaluated = obj.evaluated_get(depsgraph)
    verts = len(evaluated.data.vertices)
    faces = len(evaluated.data.polygons)
    warnings = [(w.type, w.message) for w in getattr(mod, "node_warnings", [])]
    attrs = [a.name for a in evaluated.data.attributes if not a.name.startswith(".")]
    print(
        f"[smoke] {registry.MAIN}: {verts} Vertices, {faces} Faces, attributes {attrs}, warnings: {warnings or 'none'}"
    )
    if verts == 0:
        errors.append(f"{registry.MAIN} produces no geometry")
    if "UVMap" not in attrs:
        errors.append("UVMap missing")
    if any(w[0] == "ERROR" for w in warnings):
        errors.append(f"modifier reports errors: {warnings}")

    if errors:
        print("[smoke] FAILED:\n  " + "\n  ".join(errors))
        return 1
    print("[smoke] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
