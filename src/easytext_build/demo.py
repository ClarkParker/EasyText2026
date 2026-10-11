"""Demo scene: one object with ET Text Mesh, a camera and lights, so the file shows text right after opening."""

from __future__ import annotations

import math

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

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 35
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (0.0, -10.0, 1.0)
    cam.rotation_euler = (math.radians(85), 0.0, 0.0)
    scene.collection.objects.link(cam)
    scene.camera = cam

    key = bpy.data.lights.new("Key", "AREA")
    key.energy = 400.0
    key.size = 3.0
    key_ob = bpy.data.objects.new("Key", key)
    key_ob.location = (-2.5, -3.0, 3.5)
    key_ob.rotation_euler = (math.radians(50), 0.0, math.radians(-35))
    scene.collection.objects.link(key_ob)

    fill = bpy.data.lights.new("Fill", "AREA")
    fill.energy = 120.0
    fill.size = 4.0
    fill_ob = bpy.data.objects.new("Fill", fill)
    fill_ob.location = (3.0, -3.0, 1.5)
    fill_ob.rotation_euler = (math.radians(70), 0.0, math.radians(40))
    scene.collection.objects.link(fill_ob)

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    world.color = (0.05, 0.05, 0.06)
    scene.world = world
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080

    # On opening: text object active and the properties editor on the modifier tab. The window layout itself
    # (workspace "Easy Text": 3D viewport on top, node editor with the control panel below) needs a real Blender
    # window and is applied by demo_ui.py; headless Blender does not persist workspace or area changes.
    bpy.context.view_layer.objects.active = text_ob
    text_ob.select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "PROPERTIES":
                area.spaces[0].context = "MODIFIER"
