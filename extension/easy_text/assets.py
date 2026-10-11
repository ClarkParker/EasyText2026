"""The bundled node assets: appended on demand from assets/easytext_v3.blend inside the add-on."""

from __future__ import annotations

import pathlib

import bpy

ASSET_FILE = pathlib.Path(__file__).parent / "assets" / "easytext_v3.blend"
TEXT_GROUP = "ET Text Mesh"  # inputs as modifier panels, for the sidebar
PANEL_GROUP = "Easy Text"  # the control panel inside the node editor
LIGHT_RIG_GROUP = "ET Light Rig"
TEXT_GROUPS = (TEXT_GROUP, PANEL_GROUP)


def ensure_group(name: str) -> bpy.types.NodeTree:
    """The node group by name, appended from the bundled file (with its sub-groups, materials and font) if missing."""
    tree = bpy.data.node_groups.get(name)
    if tree is not None:
        return tree
    if not ASSET_FILE.exists():
        raise FileNotFoundError(f"Easy Text asset file missing: {ASSET_FILE}")
    with bpy.data.libraries.load(str(ASSET_FILE), link=False) as (data_from, data_to):
        if name not in data_from.node_groups:
            raise KeyError(f"{name!r} is not in {ASSET_FILE.name}")
        data_to.node_groups = [name]
    tree = bpy.data.node_groups[name]
    tree.use_fake_user = True
    return tree


def text_modifier(ob: bpy.types.Object | None) -> bpy.types.NodesModifier | None:
    """The Easy Text modifier of an object, if it has one."""
    if ob is None:
        return None
    for mod in ob.modifiers:
        if mod.type == "NODES" and mod.node_group is not None and mod.node_group.name in TEXT_GROUPS:
            return mod
    return None
