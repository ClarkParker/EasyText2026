"""Operators of the Easy Text sidebar."""

from __future__ import annotations

import math

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from . import assets, fonts, rigs

PRESETS = {
    # identifier: (label, description, {input name: value})
    "HEADLINE": (
        "Headline",
        "Big, flat, clean: no bevel, no plate, no animation",
        {"Size": 1.0, "Depth": 0.1, "Bevel": False, "Plate": False, "Animate": False},
    ),
    "SIGN": (
        "Sign",
        "Bevelled letters on a rounded plate with relief",
        {
            "Depth": 0.12,
            "Bevel": True,
            "Bevel Width": 0.02,
            "Segments": 4,
            "Plate": True,
            "Relief": True,
            "Margin X": 0.5,
            "Margin Y": 0.35,
            "Corner Radius": 0.3,
            "Thickness": 0.2,
            "Animate": False,
        },
    ),
    "REVEAL": (
        "Reveal",
        "Letters rise and turn into place one after the other",
        {
            "Animate": True,
            "Direction": "In",
            "Order": "Left to Right",
            "Basis": "Letters",
            "Easing": "Ease Out",
            "Loop": "Once",
            "Start": 1,
            "Duration": 24,
            "Stagger": 2.0,
            "Offset": (0.0, -1.0, 0.0),
            "Rotation": (0.0, 0.0, math.radians(90.0)),
            "Scale": (1.0, 1.0, 1.0),
            "Hide Before Start": True,
            "Bounce": False,
        },
    ),
    "TYPEWRITER": (
        "Typewriter",
        "Letters appear one by one without moving",
        {
            "Animate": True,
            "Direction": "In",
            "Order": "Left to Right",
            "Basis": "Letters",
            "Loop": "Once",
            "Duration": 1,
            "Stagger": 3.0,
            "Offset": (0.0, 0.0, 0.0),
            "Rotation": (0.0, 0.0, 0.0),
            "Scale": (1.0, 1.0, 1.0),
            "Hide Before Start": True,
            "Bounce": False,
        },
    ),
    "BOUNCE": (
        "Bounce",
        "A continuous wobble per letter",
        {
            "Animate": True,
            "Offset": (0.0, 0.0, 0.0),
            "Rotation": (0.0, 0.0, 0.0),
            "Scale": (1.0, 1.0, 1.0),
            "Hide Before Start": False,
            "Bounce": True,
            "Bounce Strength": (0.0, 0.08, 0.0),
            "Bounce Speed": 1.5,
            "Bounce Phase": 0.12,
        },
    ),
}


def _active_text(context) -> tuple[bpy.types.Object | None, bpy.types.NodesModifier | None]:
    ob = context.active_object
    return ob, assets.text_modifier(ob)


class EASYTEXT_OT_create_text(bpy.types.Operator):
    """Add a new Easy Text object: a mesh with the ET Text Mesh modifier, upright and ready to type"""

    bl_idname = "easytext.create_text"
    bl_label = "Create Text"
    bl_options = {"REGISTER", "UNDO"}

    text: StringProperty(name="Text", default="Easy Text", description="First line; more lines in the sidebar")
    upright: BoolProperty(name="Upright", default=True, description="Stand the text up (readable from the front)")
    control_panel: BoolProperty(
        name="Control panel in the node editor",
        default=False,
        description="Use the Easy Text node-editor panel instead of the modifier inputs",
    )

    def execute(self, context):
        try:
            tree = assets.ensure_group(assets.PANEL_GROUP if self.control_panel else assets.TEXT_GROUP)
        except (FileNotFoundError, KeyError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        mesh = bpy.data.meshes.new("Easy Text")
        ob = bpy.data.objects.new("Easy Text", mesh)
        context.collection.objects.link(ob)
        ob.location = context.scene.cursor.location
        if self.upright:
            ob.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        mod = ob.modifiers.new("Easy Text", "NODES")
        mod.node_group = tree
        if not self.control_panel:
            lines = self.text.splitlines() or [""]
            for i, name in enumerate(("Text", "Line 2", "Line 3", "Line 4")):
                rigs.set_modifier_input(mod, name, lines[i] if i < len(lines) else "")
        for other in context.selected_objects:
            other.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob
        return {"FINISHED"}


class EASYTEXT_OT_set_font(bpy.types.Operator):
    """Pick one of the fonts installed on this computer"""

    bl_idname = "easytext.set_font"
    bl_label = "System Font"
    bl_options = {"REGISTER", "UNDO"}
    bl_property = "font"

    font: EnumProperty(name="Font", items=fonts.enum_items)

    def invoke(self, context, _event):
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        _ob, mod = _active_text(context)
        if mod is None or not self.font:
            return {"CANCELLED"}
        try:
            rigs.set_modifier_input(mod, "Font", fonts.load_font(self.font))
        except (RuntimeError, KeyError) as exc:
            self.report({"ERROR"}, f"Could not load the font: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}


class EASYTEXT_OT_load_font(bpy.types.Operator, ImportHelper):
    """Load a font file (.ttf, .otf, .ttc) and use it for the active text"""

    bl_idname = "easytext.load_font"
    bl_label = "Load Font File"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".ttf"
    filter_glob: StringProperty(default="*.ttf;*.otf;*.ttc;*.woff;*.woff2", options={"HIDDEN"})

    def execute(self, context):
        _ob, mod = _active_text(context)
        if mod is None:
            return {"CANCELLED"}
        try:
            rigs.set_modifier_input(mod, "Font", fonts.load_font(self.filepath))
        except (RuntimeError, KeyError) as exc:
            self.report({"ERROR"}, f"Could not load the font: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}


class EASYTEXT_OT_preset(bpy.types.Operator):
    """Apply a preset to the active text (text and font stay as they are)"""

    bl_idname = "easytext.preset"
    bl_label = "Preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(
        name="Preset", items=[(key, label, description) for key, (label, description, _values) in PRESETS.items()]
    )

    def execute(self, context):
        _ob, mod = _active_text(context)
        if mod is None:
            return {"CANCELLED"}
        for name, value in PRESETS[self.preset][2].items():
            try:
                rigs.set_modifier_input(mod, name, value)
            except KeyError:
                pass  # the control-panel tree has no inputs
        return {"FINISHED"}


class EASYTEXT_OT_add_light_rig(bpy.types.Operator):
    """Add a three-point light rig (key, fill, rim) around the active text"""

    bl_idname = "easytext.add_light_rig"
    bl_label = "Add Light Rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob, _mod = _active_text(context)
        if ob is None:
            self.report({"ERROR"}, "Select a text object first")
            return {"CANCELLED"}
        try:
            assets.ensure_group(assets.LIGHT_RIG_GROUP)
        except (FileNotFoundError, KeyError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        rigs.add_light_rig(context.scene, ob)
        return {"FINISHED"}


class EASYTEXT_OT_add_camera_orbit(bpy.types.Operator):
    """Add a camera that travels around the active text over the scene's frame range and keeps looking at it"""

    bl_idname = "easytext.add_camera_orbit"
    bl_label = "Add Camera Orbit"
    bl_options = {"REGISTER", "UNDO"}

    lens: FloatProperty(name="Lens", default=35.0, min=5.0, max=300.0, subtype="DISTANCE_CAMERA")
    start_angle: FloatProperty(name="Start Angle", default=math.radians(-30.0), subtype="ANGLE")
    sweep: FloatProperty(name="Sweep", default=math.radians(60.0), subtype="ANGLE")

    def execute(self, context):
        ob, _mod = _active_text(context)
        if ob is None:
            self.report({"ERROR"}, "Select a text object first")
            return {"CANCELLED"}
        rigs.add_camera_orbit(context.scene, ob, lens=self.lens, start_angle=self.start_angle, sweep=self.sweep)
        return {"FINISHED"}


class EASYTEXT_OT_fit_camera(bpy.types.Operator):
    """Move the scene camera so the active text fills the frame"""

    bl_idname = "easytext.fit_camera"
    bl_label = "Fit Camera to Text"
    bl_options = {"REGISTER", "UNDO"}

    margin: FloatProperty(name="Margin", default=1.1, min=1.0, max=3.0)

    def execute(self, context):
        ob, _mod = _active_text(context)
        camera = context.scene.camera
        if ob is None or camera is None:
            self.report({"ERROR"}, "Needs a text object and a scene camera")
            return {"CANCELLED"}
        if any(c.type == "FOLLOW_PATH" for c in camera.constraints):
            self.report({"WARNING"}, "The camera follows a path; remove the Orbit constraint to fit it")
            return {"CANCELLED"}
        rigs.fit_camera(camera, ob, margin=self.margin)
        return {"FINISHED"}


class EASYTEXT_OT_apply_mesh(bpy.types.Operator):
    """Turn the active text into a plain mesh (a copy; the live text stays) for export"""

    bl_idname = "easytext.apply_mesh"
    bl_label = "Mesh Copy for Export"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob, mod = _active_text(context)
        if ob is None or mod is None:
            self.report({"ERROR"}, "Select a text object first")
            return {"CANCELLED"}
        depsgraph = context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(depsgraph), depsgraph=depsgraph)
        mesh.name = f"{ob.name} Mesh"
        copy = bpy.data.objects.new(f"{ob.name} Mesh", mesh)
        copy.matrix_world = ob.matrix_world.copy()
        context.collection.objects.link(copy)
        for other in context.selected_objects:
            other.select_set(False)
        copy.select_set(True)
        context.view_layer.objects.active = copy
        self.report({"INFO"}, f"{len(mesh.vertices)} vertices, UVMap and material slots included")
        return {"FINISHED"}


CLASSES = (
    EASYTEXT_OT_create_text,
    EASYTEXT_OT_set_font,
    EASYTEXT_OT_load_font,
    EASYTEXT_OT_preset,
    EASYTEXT_OT_add_light_rig,
    EASYTEXT_OT_add_camera_orbit,
    EASYTEXT_OT_fit_camera,
    EASYTEXT_OT_apply_mesh,
)
