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

    panel = bpy.data.objects.new("panel", None)
    bpy.context.scene.collection.objects.link(panel)
    pmod = panel.modifiers.new("EasyText", "NODES")
    pmod.node_group = bpy.data.node_groups[registry.PANEL]
    depsgraph.update()
    pgeo = panel.evaluated_get(depsgraph).evaluated_geometry()  # keep the geometry set alive while reading it
    pverts = len(pgeo.mesh.vertices) if pgeo.mesh else 0
    pwarn = [(w.type, w.message) for w in pmod.node_warnings]
    print(f"[smoke] {registry.PANEL}: {pverts} vertices, warnings: {pwarn or 'none'}")
    if pverts == 0:
        errors.append(f"{registry.PANEL} produces no geometry")

    # animation: with Animate on, the letters must move between two frames and the helper attributes must exist
    from .core import group_socket

    anim = bpy.data.node_groups[registry.PANEL].nodes["Animation"]
    group_socket(anim, "Animate").default_value = True
    group_socket(anim, "Keep Helper Attributes").default_value = True
    pmod.node_group = pmod.node_group  # re-evaluate with the new defaults
    panel.update_tag()
    bounds = []
    for frame in (1, 20):
        bpy.context.scene.frame_set(frame)
        depsgraph.update()
        geo = panel.evaluated_get(depsgraph).evaluated_geometry()
        if geo.mesh is None:
            errors.append(f"animation: no mesh at frame {frame}")
            break
        xs = [v.co.y for v in geo.mesh.vertices]
        bounds.append((round(min(xs), 4), round(max(xs), 4)))
        anim_attrs = {a.name for a in geo.mesh.attributes}
    kept = sorted(a for a in anim_attrs if a.startswith("et_"))
    print(f"[smoke] animation: y-bounds at frame 1 and 20 {bounds}, helper attributes kept: {kept}")
    if len(bounds) == 2 and bounds[0] == bounds[1]:
        errors.append("animation: letters do not move between frame 1 and 20")
    for attr in ("et_char_index", "et_word_index", "et_line_index", "et_pivot", "et_weight"):
        if attr not in anim_attrs:
            errors.append(f"animation: attribute {attr} missing on the mesh")

    # light rig: three instances of the light objects around the text
    from . import rigs

    rig = rigs.add_light_rig(bpy.context.scene, obj)
    depsgraph.update()
    rig_geo = rig.evaluated_get(depsgraph).evaluated_geometry()
    rig_points = rig_geo.instances_pointcloud()
    rig_count = len(rig_points.points) if rig_points is not None else 0
    print(f"[smoke] light rig: {rig_count} light instances")
    if rig_count != 3:
        errors.append(f"light rig: expected 3 light instances, got {rig_count}")

    if errors:
        print("[smoke] FAILED:\n  " + "\n  ".join(errors))
        return 1
    print("[smoke] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
