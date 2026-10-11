"""Easy Text: typography and text animation with Geometry Nodes, as a sidebar tab in the 3D viewport.

The node assets (ET Text Mesh, the Easy Text control panel, ET Light Rig) ship inside the add-on and are appended
into the file on first use. Everything the sidebar shows comes from the node group interface, so the add-on and
the node assets never disagree."""

import bpy

from . import ops, ui


def register() -> None:
    for cls in (*ops.CLASSES, *ui.CLASSES):
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed((*ops.CLASSES, *ui.CLASSES)):
        bpy.utils.unregister_class(cls)
