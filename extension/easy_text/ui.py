"""The Easy Text tab in the 3D viewport sidebar (N panel).

The main panel draws the inputs of the ET Text Mesh modifier straight from its node group interface, so every
input and panel of the node group appears here automatically, in the same order and grouping, with panel
toggles in the headers. Each input is the RNA slot `mod.properties.inputs.<identifier>` whose `value` is typed
(units, enums for menus, ID pointers), so `layout.prop` draws the right widget. On top of that: a font picker
for system fonts, presets, scene rigs and export."""

from __future__ import annotations

import bpy

from . import assets, ops

CATEGORY = "Easy Text"


def _top_level(tree: bpy.types.NodeTree) -> list:
    """Interface items without a parent panel (the root panel has an empty name)."""
    return [item for item in tree.interface.items_tree if item.parent is None or not item.parent.name]


def _draw_socket(layout, inputs, item, *, text=None):
    slot = getattr(inputs, item.identifier, None)
    if slot is None:
        return
    layout.prop(slot, "value", text=item.name if text is None else text)


def _draw_items(layout, inputs, items, prefix: str) -> None:
    for item in items:
        if item.item_type == "PANEL":
            children = list(item.interface_items)
            toggle = next((c for c in children if c.item_type == "SOCKET" and c.is_panel_toggle), None)
            header, body = layout.panel(f"{prefix}{item.name}", default_closed=item.default_closed)
            if toggle is not None:
                _draw_socket(header, inputs, toggle, text=item.name)
            else:
                header.label(text=item.name)
            if body is not None:
                _draw_items(
                    body.column(align=True), inputs, [c for c in children if c is not toggle], f"{prefix}{item.name}/"
                )
        elif item.in_out == "INPUT" and not item.hide_in_modifier and not item.is_panel_toggle:
            _draw_socket(layout, inputs, item)


def draw_modifier_inputs(layout, mod: bpy.types.NodesModifier) -> None:
    tree = mod.node_group
    _draw_items(layout, mod.properties.inputs, _top_level(tree), f"easytext/{tree.name}/")


class EASYTEXT_PT_text(bpy.types.Panel):
    bl_label = "Easy Text"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = CATEGORY
    bl_icon = "OUTLINER_OB_FONT"  # 5.2: icon of the sidebar tab

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        mod = assets.text_modifier(ob)
        if mod is None:
            col = layout.column()
            col.scale_y = 1.4
            col.operator(ops.EASYTEXT_OT_create_text.bl_idname, icon="OUTLINER_OB_FONT")
            layout.label(text="Or select an Easy Text object.", icon="INFO")
            return
        layout.label(text=ob.name, icon="OUTLINER_OB_FONT")
        if mod.node_group.name == assets.PANEL_GROUP:
            layout.label(text="Controls are in the node editor.", icon="NODETREE")
            layout.operator(ops.EASYTEXT_OT_create_text.bl_idname, text="New Text with Sidebar Controls")
            return
        font = None
        try:
            from . import rigs

            font = rigs.get_modifier_input(mod, "Font")
        except KeyError:
            pass
        row = layout.row(align=True)
        row.operator(ops.EASYTEXT_OT_set_font.bl_idname, text=font.name if font else "System Font", icon="FONT_DATA")
        row.operator(ops.EASYTEXT_OT_load_font.bl_idname, text="", icon="FILEBROWSER")
        draw_modifier_inputs(layout, mod)


class EASYTEXT_PT_presets(bpy.types.Panel):
    bl_label = "Presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = CATEGORY
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return assets.text_modifier(context.active_object) is not None

    def draw(self, context):
        col = self.layout.column(align=True)
        for key, (label, _description, _values) in ops.PRESETS.items():
            col.operator(ops.EASYTEXT_OT_preset.bl_idname, text=label).preset = key


class EASYTEXT_PT_scene(bpy.types.Panel):
    bl_label = "Camera and Light"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = CATEGORY
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(ops.EASYTEXT_OT_add_light_rig.bl_idname, icon="LIGHT_AREA")
        col.operator(ops.EASYTEXT_OT_add_camera_orbit.bl_idname, icon="CON_FOLLOWPATH")
        col.operator(ops.EASYTEXT_OT_fit_camera.bl_idname, icon="VIEW_CAMERA")
        scene = context.scene
        row = self.layout.row(align=True)
        row.prop(scene, "frame_start", text="Start")
        row.prop(scene, "frame_end", text="End")


class EASYTEXT_PT_export(bpy.types.Panel):
    bl_label = "Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = CATEGORY
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.operator(ops.EASYTEXT_OT_apply_mesh.bl_idname, icon="MESH_DATA")
        layout.label(text="Then File > Export (glTF, FBX, OBJ).", icon="EXPORT")


CLASSES = (EASYTEXT_PT_text, EASYTEXT_PT_presets, EASYTEXT_PT_scene, EASYTEXT_PT_export)
