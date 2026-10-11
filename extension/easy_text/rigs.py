"""Scene rigs around a text object: a camera orbit, a camera fit and a light rig.

Shared by the add-on (operators) and the demo build (`easytext_build.rigs` loads this file). No imports from the
build package, so the add-on stays self-contained.

The light rig is the node group ET Light Rig on an Empty, fed with three light objects that live in a hidden
collection. The camera orbit is plain Blender: a curve path, a Follow Path constraint with a keyframed offset and
a Track To constraint, so it works everywhere without the node assets."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

__all__ = (
    "LIGHTS",
    "LIGHT_RIG_GROUP",
    "SOCKET_MAP_KEY",
    "set_modifier_input",
    "get_modifier_input",
    "input_slot",
    "socket_identifier",
    "world_bounds",
    "add_light_rig",
    "add_camera_orbit",
    "fit_camera",
)

SOCKET_MAP_KEY = "et_sockets"  # ID property on every built group: input name -> socket identifier
LIGHTS = {  # name: (type, energy, size)
    "Key": ("AREA", 400.0, 3.0),
    "Fill": ("AREA", 120.0, 4.0),
    "Rim": ("AREA", 300.0, 2.0),
}
LIGHT_RIG_GROUP = "ET Light Rig"
SOURCES_COLLECTION = "Easy Text Light Sources"


def socket_identifier(tree: bpy.types.NodeTree, name: str) -> str:
    """Identifier of an interface input by name; panel toggles are renamed by Blender, the map resolves them."""
    identifier = (tree.get(SOCKET_MAP_KEY) or {}).get(name)
    if identifier is None:
        for item in tree.interface.items_tree:
            if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name == name:
                return item.identifier
        raise KeyError(f"{tree.name} has no input {name!r}")
    return identifier


def input_slot(mod: bpy.types.Modifier, name: str):
    """The RNA property group of one modifier input: `.value` is typed (floats with units, menus as enums with the
    option names as identifiers, ID pointers), so it can be read, written and drawn with layout.prop."""
    return getattr(mod.properties.inputs, socket_identifier(mod.node_group, name))


def set_modifier_input(mod: bpy.types.Modifier, name: str, value) -> None:
    """Set an input of a Geometry Nodes modifier by its interface name (panel toggles included); menu inputs
    take the option name ("Center")."""
    input_slot(mod, name).value = value
    mod.id_data.update_tag()


def get_modifier_input(mod: bpy.types.Modifier, name: str):
    """Value of an input by interface name; menu inputs come back as the option name."""
    return input_slot(mod, name).value


def world_bounds(ob: bpy.types.Object) -> tuple[Vector, Vector]:
    """Centre and size of the evaluated object in world space."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    corners = [ob.matrix_world @ Vector(c) for c in ob.evaluated_get(depsgraph).bound_box]
    lo = Vector(min(c[i] for c in corners) for i in range(3))
    hi = Vector(max(c[i] for c in corners) for i in range(3))
    return (lo + hi) * 0.5, hi - lo


def world_corners(ob: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    return [ob.matrix_world @ Vector(c) for c in ob.evaluated_get(depsgraph).bound_box]


def _sources_collection(scene: bpy.types.Scene) -> bpy.types.Collection:
    coll = bpy.data.collections.get(SOURCES_COLLECTION)
    if coll is None:
        coll = bpy.data.collections.new(SOURCES_COLLECTION)
        coll.hide_render = True
        coll.hide_viewport = True
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    return coll


def add_light_rig(scene: bpy.types.Scene, target: bpy.types.Object, *, name: str = "Light Rig") -> bpy.types.Object:
    """An Empty with the ET Light Rig modifier and three light objects in a hidden collection."""
    sources = _sources_collection(scene)
    lights = {}
    for light_name, (light_type, energy, size) in LIGHTS.items():
        data = bpy.data.lights.new(f"{name} {light_name}", light_type)
        data.energy = energy
        if light_type == "AREA":
            data.size = size
        ob = bpy.data.objects.new(f"{name} {light_name}", data)
        sources.objects.link(ob)
        lights[light_name] = ob

    rig = bpy.data.objects.new(name, None)
    rig.empty_display_type = "SPHERE"
    rig.empty_display_size = 0.5
    scene.collection.objects.link(rig)
    mod = rig.modifiers.new(name, "NODES")
    mod.node_group = bpy.data.node_groups[LIGHT_RIG_GROUP]
    set_modifier_input(mod, "Target", target)
    for light_name, ob in lights.items():
        set_modifier_input(mod, f"{light_name} Light", ob)
    return rig


def add_camera_orbit(
    scene: bpy.types.Scene,
    target: bpy.types.Object,
    *,
    name: str = "Camera",
    lens: float = 35.0,
    start_angle: float = math.radians(-30.0),
    sweep: float = math.radians(60.0),
    radius: float | None = None,
    height: float | None = None,
    frame_start: int | None = None,
    frame_end: int | None = None,
    points: int = 64,
) -> tuple[bpy.types.Object, bpy.types.Object]:
    """A camera that travels along an arc around the target and keeps looking at it.

    Angle 0 is in front of the target (-Y), positive angles go clockwise seen from above. Radius and height
    default to values that frame the target with the given lens."""
    centre, size = world_bounds(target)
    extent = max(size.x, size.z, 0.5)
    if radius is None:
        radius = max(extent * 36.0 / lens * 1.15, 3.0)  # horizontal fit for the lens plus a small margin
    if height is None:
        height = centre.z + extent * 0.15
    frame_start = scene.frame_start if frame_start is None else frame_start
    frame_end = scene.frame_end if frame_end is None else frame_end

    curve = bpy.data.curves.new(f"{name} Path", "CURVE")
    curve.dimensions = "3D"
    curve.use_path = True
    curve.path_duration = max(frame_end - frame_start, 1)
    spline = curve.splines.new("POLY")
    spline.points.add(points - 1)
    for i, point in enumerate(spline.points):
        angle = start_angle + sweep * i / (points - 1)
        point.co = (centre.x + radius * math.sin(angle), centre.y - radius * math.cos(angle), height, 1.0)
    path = bpy.data.objects.new(f"{name} Path", curve)
    scene.collection.objects.link(path)

    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    camera = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    follow = camera.constraints.new("FOLLOW_PATH")
    follow.name = "Orbit"
    follow.target = path
    follow.use_fixed_location = True
    follow.use_curve_follow = False
    follow.offset_factor = 0.0
    camera.keyframe_insert('constraints["Orbit"].offset_factor', frame=frame_start)
    follow.offset_factor = 1.0
    camera.keyframe_insert('constraints["Orbit"].offset_factor', frame=frame_end)

    track = camera.constraints.new("TRACK_TO")
    track.name = "Look at Text"
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return camera, path


def fit_camera(camera: bpy.types.Object, target: bpy.types.Object, *, margin: float = 1.1) -> None:
    """Move the camera (keeping its rotation) so the target's bounds fill the frame, with a margin."""
    centre, _size = world_bounds(target)
    coords = [v for corner in world_corners(target) for v in corner]
    for _pass in range(2):  # a Track To constraint changes the orientation with the location: settle it
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        location, scale = camera.camera_fit_coords(depsgraph, coords)
        if camera.data.type == "ORTHO":
            camera.data.ortho_scale = scale * margin
            camera.location = location
        else:
            camera.location = centre + (Vector(location) - centre) * margin
        bpy.context.view_layer.update()
