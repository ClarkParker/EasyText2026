"""Easy Text: the control panel, the v3 of the v2.1 GUI.

Built from the user's point of view, in reading order: 1. type the text, 2. choose font and size, 3. shape the
mesh, then the result. The group nodes themselves are the panels: every control is an input widget on one of
three nodes, grouped by what the user does, not by how the mesh is computed.

Style elements, all drawn by Blender 5.2 itself (frames, nodes, reroutes, wires):
  - one outer frame with the title and an accent rule under it,
  - numbered section frames in the dark teal of v2.1, with a purple tip box each,
  - the Text Lines node tinted red like the v2.1 string nodes,
  - labelled reroutes on the three wires as markers (text, glyphs, mesh) that also keep the wires straight,
  - an export note and a small footer.

Use ET Text Mesh as the modifier instead when you prefer the properties editor: same nodes, inputs as panels."""

from __future__ import annotations

import bpy

from .. import catalog, materials
from ..core import GroupBuilder, NodeRef, builtin_font, group_socket, heading
from . import et_lines_join, et_mesh_generation, et_text_source

NAME = "Easy Text"

NODE_W = 300  # panel node width; text fields and sliders need the room
COLUMN = 460  # x pitch between the three panel nodes
TIP_H = 96  # tip box height (two short lines at text size 14)
BOX_TEXT_SIZE = 14  # frame text follows the label size
TITLE = "Easy Text Geometry Node 3"

# v2.1 palette: dark teal frames, red text nodes, purple notes
OUTER_COLOR = (0.050, 0.150, 0.150)
SECTION_COLOR = (0.085, 0.250, 0.250)
RESULT_COLOR = (0.070, 0.200, 0.170)
ACCENT_COLOR = (0.180, 0.620, 0.580)
TIP_COLOR = (0.190, 0.085, 0.210)
TEXT_NODE_COLOR = (0.400, 0.130, 0.170)
FONT_NODE_COLOR = (0.100, 0.195, 0.205)
MESH_NODE_COLOR = (0.105, 0.200, 0.150)

TIP_TEXT = "Up to four lines; empty lines are skipped.\nNew line = new row of text."
TIP_FONT = "Size is in metres. Text Box: Box Width > 0 wraps the lines."
TIP_MESH = "Bevel Width is capped at half the Depth.\nUV: planar caps, one seamless band around the sides."
NOTE = "Export: apply the modifier (modifier tab > Apply).\nThe mesh keeps its UVMap and material slots."
FOOTER = "Easy Text 2026  ·  Blender 5.2 LTS  ·  node assets CC0"


def _box(g: GroupBuilder, name: str, text: str, size: tuple, location: tuple, *, color=TIP_COLOR, label=""):
    """A note frame: fixed size, frame text as content, optional label; parented to the current frame."""
    node = g.tree.nodes.new("NodeFrame")
    node.name = f"[{name}]"
    node.label = label
    node.label_size = BOX_TEXT_SIZE
    node.shrink = False
    node.width, node.height = size
    node.use_custom_color = True
    node.color = color
    note = bpy.data.texts.new(f"{g.tree.name} – {name}")
    note.write(text)
    node.text = note
    node.parent = g._frames[-1] if g._frames else None
    node.location_absolute = location
    return node


def _rule(g: GroupBuilder, name: str, width: float, location: tuple, *, color=ACCENT_COLOR, height: float = 6):
    """A thin coloured frame used as a divider line."""
    node = g.tree.nodes.new("NodeFrame")
    node.name = f"[{name}]"
    node.label = ""
    node.shrink = False
    node.width, node.height = width, height
    node.use_custom_color = True
    node.color = color
    node.parent = g._frames[-1] if g._frames else None
    node.location_absolute = location
    return node


def _marker(g: GroupBuilder, name: str, source, x: float, y: float) -> NodeRef:
    """A labelled reroute on a wire: a marker between two sections that also keeps the wire straight."""
    rr = g.node("NodeReroute", name, label=name, inputs={0: source})
    g.place(rr, x, y)
    return rr


def build():
    mats = materials.ensure_all()
    g = GroupBuilder(
        NAME,
        description="Easy Text control panel: three settings nodes with all controls, in the style of v2.1.",
        is_modifier=True,
        catalog=catalog.ROOT,
        color_tag="GEOMETRY",
        default_width=NODE_W,
        compact=False,
        arrange=False,
    )
    g.output("Geometry", "geometry")

    with g.frame(TITLE, label_size=32, color=OUTER_COLOR):
        # ---------------------------------------------------------- 1. text
        with g.frame(heading("1. Text Input"), color=SECTION_COLOR):
            lines = g.group(et_lines_join.NAME, "Text Lines")
            lines.node.width = NODE_W
            lines.node.show_options = False  # no data-block selector on a panel node
            lines.node.use_custom_color = True
            lines.node.color = TEXT_NODE_COLOR
            lines.node.inputs["Line 1"].default_value = "Easy Text"
            lines.node.inputs["Line 2"].default_value = "Geometry Node 3"
            _box(g, "Tip Text", TIP_TEXT, (NODE_W, TIP_H), (0.0, -195.0))

        # ---------------------------------------------------------- 2. font
        with g.frame(heading("2. Font Settings"), color=SECTION_COLOR):
            text_marker = _marker(g, "text", lines["String"], COLUMN - 70.0, -63.0)
            text = g.group(et_text_source.NAME, "Text Settings", inputs={"Text": text_marker[0]})
            text.node.width = NODE_W
            text.node.show_options = False
            text.node.use_custom_color = True
            text.node.color = FONT_NODE_COLOR
            text.node.inputs["Font"].default_value = builtin_font()
            text.node.outputs["Character Count"].hide = True  # information for builders, not for the panel
            for name, value in (
                ("Align X", "Center"),
                ("Align Y", "Middle"),
                ("Pivot", "Midpoint"),
                ("Overflow", "Overflow"),
            ):
                text.node.inputs[name].default_value = value
            _box(g, "Tip Font", TIP_FONT, (NODE_W, TIP_H), (COLUMN, -375.0))

        # ---------------------------------------------------------- 3. mesh
        with g.frame(heading("3. Mesh Settings"), color=SECTION_COLOR):
            glyph_marker = _marker(g, "glyphs", text["Curves"], 2 * COLUMN - 70.0, -41.0)
            mesh = g.group(et_mesh_generation.NAME, "Mesh Generation", inputs={"Curves": glyph_marker[0]})
            mesh.node.width = NODE_W + 20
            mesh.node.show_options = False
            mesh.node.use_custom_color = True
            mesh.node.color = MESH_NODE_COLOR
            group_socket(mesh.node, "Bevel").default_value = True  # the good-looking default
            for name, value in (("Fill Mode", "N-gons"), ("Fill Rule", "Even-Odd")):
                mesh.node.inputs[name].default_value = value
            for name, mat in (
                ("Front Material", "ET Front"),
                ("Side Material", "ET Side"),
                ("Bevel Material", "ET Bevel"),
            ):
                mesh.node.inputs[name].default_value = mats[mat]
            _box(g, "Tip Mesh", TIP_MESH, (NODE_W + 20, TIP_H), (2 * COLUMN, -480.0))

        # ---------------------------------------------------------- result
        with g.frame(heading("Result"), color=RESULT_COLOR):
            mesh_marker = _marker(g, "mesh", mesh["Mesh"], 3 * COLUMN - 70.0, -41.0)
            g.group_out.parent = g._frames[-1]
            g.group_out.label = "Easy Text Mesh"
        g.set_output("Geometry", mesh_marker[0])

        # ---------------------------------------------------------- decoration: rule, note, footer
        right = 3 * COLUMN + 160.0
        _rule(g, "Title Rule", right + 60.0, (-30.0, 96.0))
        _box(g, "Note", NOTE, (NODE_W, 150.0), (0.0, -320.0), label="Note")
        _box(g, "Footer", FOOTER, (NODE_W + 160.0, 48.0), (2 * COLUMN, -660.0), color=OUTER_COLOR)

    # ---------------------------------------------------------------- positions (sockets of the three wires level)
    g.place(lines, 0.0, -18.0)  # String output meets the Text input of Text Settings
    g.place(text, COLUMN, 0.0)
    g.place(mesh, 2 * COLUMN, 4.0)  # Curves input meets the Curves output of Text Settings
    g.place(NodeRef(g.group_out), 3 * COLUMN, 4.0)
    return g.finish()
