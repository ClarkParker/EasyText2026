"""Finish the demo file with a real Blender window (run under Xvfb): workspace layout, editors, view framing,
and screenshots of every node group for layout review.

Blender applies a workspace switch and redraws only from its event loop, so the work is a generator that is
driven by an app timer: every ``yield`` hands control back to the event loop for one tick.

Run (from the repository root, with a display or under xvfb-run):
    xvfb-run -a -s "-screen 0 1920x1080x24 +extension GLX" blender --python-expr \
        "import sys; sys.path.insert(0, 'src'); import easytext_build.demo_ui as d; d.main()"
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import traceback

from . import paths
from .groups import registry

SCREENSHOT_DIR = paths.ROOT / "docs" / "screenshots"
WORKSPACE = "Easy Text"
TICK = 0.3  # seconds between steps; one redraw happens in between


def _log(msg: str) -> None:
    print(f"[demo_ui] {msg}", flush=True)


def _window():
    import bpy

    return bpy.context.window_manager.windows[0]


def _area(screen, area_type):
    return next((a for a in screen.areas if a.type == area_type), None)


def _override(window, area):
    import bpy

    region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
    return bpy.context.temp_override(window=window, screen=window.screen, area=area, region=region)


def _set_type(window, area, area_type):
    import bpy

    with _override(window, area):
        bpy.ops.screen.space_type_set_or_cycle(space_type=area_type)


def _join(window, keep, remove) -> bool:
    """Join two neighbouring areas; `keep` grows over `remove`. Returns False when Blender refuses."""
    import bpy

    props = bpy.ops.screen.area_join.get_rna_type().properties.keys()
    inside = lambda a: (a.x + a.width // 2, a.y + a.height // 2)  # noqa: E731
    try:
        with _override(window, keep):
            if "source_xy" in props:
                result = bpy.ops.screen.area_join(source_xy=inside(keep), target_xy=inside(remove))
            else:  # older signature: the cursor sits on the shared edge
                edge_x = remove.x if remove.x > keep.x else keep.x
                result = bpy.ops.screen.area_join(cursor=(edge_x, keep.y + keep.height // 2))
    except RuntimeError as exc:
        print(f"[demo_ui] area join failed: {exc}")
        return False
    return "FINISHED" in result


def _capture(window, path: pathlib.Path, area=None) -> None:
    """Save a picture of the window (or of one area). Blender's own screenshot operator reads the GL front
    buffer, which stays black on a virtual display, so the X server is asked instead when ImageMagick exists."""
    import bpy

    display = os.environ.get("DISPLAY")
    if shutil.which("import") and shutil.which("convert") and display:
        subprocess.run(["import", "-display", display, "-window", "root", str(path)], check=True)
        if area is not None:  # Blender's y runs bottom-up, the image's top-down; the window sits at (0, 0)
            top = window.height - (area.y + area.height)
            crop = f"{area.width}x{area.height}+{area.x + window.x}+{top + window.y}"
            subprocess.run(["convert", str(path), "-crop", crop, "+repage", str(path)], check=True)
        return
    with _override(window, area or window.screen.areas[0]):
        if area is None:
            bpy.ops.screen.screenshot(filepath=str(path))
        else:
            bpy.ops.screen.screenshot_area(filepath=str(path))


def _screenshot_name(tree_name: str) -> str:
    return tree_name.strip(".").replace(" ", "_") + ".png"


def steps():
    """The whole job as one generator; every `yield` lets the event loop run."""
    import bpy

    if pathlib.Path(bpy.data.filepath) != paths.DEMO_FILE:
        _log("opening the demo file")
        bpy.ops.wm.open_mainfile(filepath=str(paths.DEMO_FILE))
    window = _window()
    workspace = bpy.data.workspaces.get(WORKSPACE) or bpy.data.workspaces.get("Geometry Nodes")
    if workspace is None:
        raise RuntimeError("no 'Geometry Nodes' workspace in the demo file")
    workspace.name = WORKSPACE
    window.workspace = workspace  # applied by the event loop
    yield
    window = _window()
    screen = window.screen
    if window.workspace.name != WORKSPACE:
        raise RuntimeError(f"workspace switch did not happen (still {window.workspace.name})")
    _log(f"workspace '{WORKSPACE}' active, screen '{screen.name}'")

    # ---- top row: one wide 3D viewport (join the spreadsheet into the viewport) ------------------------------
    spreadsheet = _area(screen, "SPREADSHEET")
    viewport = _area(screen, "VIEW_3D")
    if spreadsheet is not None and viewport is not None and _join(window, viewport, spreadsheet):
        _log("joined spreadsheet into the viewport")
        yield
        screen = window.screen
    elif spreadsheet is not None:  # fallback: a second viewport that looks through the camera
        _set_type(window, spreadsheet, "VIEW_3D")
        yield
        with _override(window, spreadsheet):
            bpy.ops.view3d.view_camera()
    for area in screen.areas:
        if area.type == "PROPERTIES":
            area.spaces.active.context = "MODIFIER"
        elif area.type == "NODE_EDITOR":
            area.spaces.active.show_region_ui = False  # the control panel needs the width

    # ---- framing of the big viewport -------------------------------------------------------------------------
    viewport = max((a for a in screen.areas if a.type == "VIEW_3D"), key=lambda a: a.width * a.height, default=None)
    if viewport is not None:
        with _override(window, viewport):
            bpy.ops.view3d.view_camera()  # the demo camera frames the text
    yield

    # ---- screenshots: node editor maximised, one image per group -----------------------------------------------
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    node_area = _area(screen, "NODE_EDITOR")
    if node_area is None:
        raise RuntimeError("no node editor in the workspace")
    with _override(window, node_area):
        bpy.ops.screen.screen_full_area()
    _log("node editor maximised for screenshots")
    yield
    node_area = _area(window.screen, "NODE_EDITOR")
    space = node_area.spaces.active
    space.pin = True
    for name in registry.names():
        tree = bpy.data.node_groups.get(name)
        if tree is None:
            continue
        space.node_tree = tree
        yield  # draw once so the node bounds exist
        with _override(window, node_area):
            bpy.ops.node.view_all()
        yield
        _capture(window, SCREENSHOT_DIR / _screenshot_name(name), node_area)
        _log(f"screenshot {name}")
    space.pin = False
    space.node_tree = None  # back to "follow the active modifier"
    with _override(window, node_area):
        bpy.ops.screen.back_to_previous()
    yield

    # ---- final node editor view + a picture of the whole workspace ----------------------------------------------
    screen = window.screen
    node_area = _area(screen, "NODE_EDITOR")
    yield  # redraw with the modifier tree
    with _override(window, node_area):
        bpy.ops.node.view_all()
    yield
    _capture(window, SCREENSHOT_DIR / "workspace.png")

    # ---- save ------------------------------------------------------------------------------------------------
    for area in screen.areas:  # material preview is what the user should see; set last so Xvfb never draws it
        if area.type == "VIEW_3D":
            area.spaces.active.shading.type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=str(paths.DEMO_FILE), compress=True)
    _log(
        f"saved {paths.DEMO_FILE.relative_to(paths.ROOT)} with workspace '{WORKSPACE}'; "
        f"screenshots in {SCREENSHOT_DIR.relative_to(paths.ROOT)}"
    )


def main() -> int:
    import bpy

    if bpy.app.background:
        _log("no window: run with a display (xvfb-run)")
        return 1
    job = steps()
    _log("timer registered")

    def tick():
        try:
            next(job)
            return TICK
        except StopIteration:
            _log("done")
        except Exception:
            traceback.print_exc()
            _log("FAILED")
        with bpy.context.temp_override(window=_window()):
            bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(tick, first_interval=TICK, persistent=True)  # must survive the file load
    return 0


if __name__ == "__main__":
    sys.exit(main())
