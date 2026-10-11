"""Exercise the add-on in a real Blender window and photograph the sidebar (run under Xvfb).

Registers the add-on from extension/easy_text, creates a text, applies presets, adds the rigs, then captures the
sidebar into docs/screenshots/sidebar.png. Every operator result and any draw error ends up on the console.

Run from the repository root (python -m easytext_build.package first, so the asset file is in the add-on):
    xvfb-run -a -s "-screen 0 1920x1080x24 +extension GLX" blender --factory-startup --python tools/sidebar_check.py
"""

from __future__ import annotations

import pathlib
import sys
import traceback

import bpy

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "extension"))
sys.path.insert(0, str(ROOT / "src"))

import easy_text  # noqa: E402
from easy_text import rigs, ui  # noqa: E402

from easytext_build import demo_ui  # noqa: E402

SCREENSHOT = ROOT / "docs" / "screenshots" / "sidebar.png"


def log(message: str) -> None:
    print(f"[sidebar] {message}", flush=True)


def steps():
    # The sidebar's active tab cannot be set from Python; draw in the tab a factory file opens with.
    for cls in ui.CLASSES:
        if hasattr(cls, "bl_category"):
            cls.bl_category = "Item"
    easy_text.register()
    window = bpy.context.window_manager.windows[0]
    area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    with demo_ui._override(window, area):
        log(f"create_text: {bpy.ops.easytext.create_text(text='Easy Text')}")
        text = bpy.data.objects["Easy Text"]
        mod = text.modifiers[0]
        rigs.set_modifier_input(mod, "Line 2", "Sidebar")
        log(f"preset SIGN: {bpy.ops.easytext.preset(preset='SIGN')} -> Plate={rigs.get_modifier_input(mod, 'Plate')}")
        log(
            f"preset REVEAL: {bpy.ops.easytext.preset(preset='REVEAL')} -> "
            f"Direction={rigs.get_modifier_input(mod, 'Direction')}, Order={rigs.get_modifier_input(mod, 'Order')}"
        )
        rigs.set_modifier_input(mod, "Align X", "Right")
        log(f"menu by name: Align X -> {rigs.get_modifier_input(mod, 'Align X')}")
        log(f"light rig: {bpy.ops.easytext.add_light_rig()}")
        log(f"camera orbit: {bpy.ops.easytext.add_camera_orbit()}")
        log(f"mesh copy: {bpy.ops.easytext.apply_mesh()}")
        bpy.context.view_layer.objects.active = text
        text.select_set(True)
        area.spaces.active.show_region_ui = True
        bpy.ops.view3d.view_camera()
    log("objects: " + ", ".join(o.name for o in bpy.data.objects))
    yield
    yield
    region = next(r for r in area.regions if r.type == "UI")
    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    demo_ui._capture(window, SCREENSHOT, region)
    log(f"screenshot {SCREENSHOT.relative_to(ROOT)} ({region.width}x{region.height})")


def main() -> None:
    job = steps()

    def tick():
        try:
            next(job)
            return 0.5
        except StopIteration:
            log("done")
        except Exception:
            traceback.print_exc()
            log("FAILED")
        with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]):
            bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(tick, first_interval=1.0, persistent=True)


main()
