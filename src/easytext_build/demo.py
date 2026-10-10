"""Demo-Szene: ein Objekt mit ET Text Mesh, Kamera und Licht, damit die Datei beim Öffnen sofort Text zeigt."""

from __future__ import annotations

import math

from .groups import registry


def populate_scene(scene) -> None:
    import bpy

    tree = bpy.data.node_groups[registry.MAIN]
    mesh = bpy.data.meshes.new("Easy Text")
    text_ob = bpy.data.objects.new("Easy Text", mesh)
    scene.collection.objects.link(text_ob)
    mod = text_ob.modifiers.new("Easy Text", "NODES")
    mod.node_group = tree
    ids = {}
    for item in tree.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT":
            ids.setdefault(item.name, item.identifier)
    mod.properties.inputs[ids["Bevel"]]["value"] = 1
    mod.properties.inputs[ids["Zeile 2"]]["value"] = "Geometry Node v3"

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (0.0, -7.5, 1.2)
    cam.rotation_euler = (math.radians(81), 0.0, 0.0)
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
