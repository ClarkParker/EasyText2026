"""Demo scene: the text with the control panel, a camera orbit and a light rig, so the file shows text right away."""

from __future__ import annotations

import math

from . import rigs
from .core import group_socket
from .groups import registry


def populate_scene(scene) -> None:
    import bpy

    tree = bpy.data.node_groups[registry.PANEL]
    mesh = bpy.data.meshes.new("Easy Text")
    text_ob = bpy.data.objects.new("Easy Text", mesh)
    scene.collection.objects.link(text_ob)
    mod = text_ob.modifiers.new("Easy Text", "NODES")
    mod.node_group = tree
    text_ob.rotation_euler = (math.radians(90), 0.0, 0.0)  # upright, readable from the front (-Y)
    plate = tree.nodes["Mesh Generation"]
    group_socket(plate, "Plate").default_value = True  # the demo shows the base plate with relief
    group_socket(plate, "Relief").default_value = True
    scene.frame_start, scene.frame_end = 1, 120

    # camera orbit and three-point light rig around the text (rest pose: animation is switched on afterwards)
    rigs.add_camera_orbit(scene, text_ob, frame_start=1, frame_end=120)
    rigs.add_light_rig(scene, text_ob)

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    world.color = (0.05, 0.05, 0.06)
    scene.world = world
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    anim = tree.nodes["Animation"]
    group_socket(anim, "Animate").default_value = True  # the demo shows the letters arriving
    group_socket(anim, "Rotation").default_value = (0.0, 0.0, math.radians(90))
    scene.frame_current = 30  # half the letters are in place, the rest still travelling

    # On opening: text object active and the properties editor on the modifier tab. The window layout itself
    # (workspace "Easy Text": 3D viewport on top, node editor with the control panel below) needs a real Blender
    # window and is applied by demo_ui.py; headless Blender does not persist workspace or area changes.
    bpy.context.view_layer.objects.active = text_ob
    text_ob.select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "PROPERTIES":
                area.spaces[0].context = "MODIFIER"
