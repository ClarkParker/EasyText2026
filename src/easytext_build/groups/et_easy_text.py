"""Easy Text: the control panel, the v3 of the v2.1 GUI.

The group nodes themselves are the panels: every control is an input widget on one of three nodes, grouped by
what the user does, not by how the mesh is computed:

    [ Text Input ]  Text Lines      four text fields
    [ Font Settings ]  Text Settings  font, alignment, spacing, text box (collapsible panels)
    [ Mesh Settings ]  Mesh Generation  outline, shape with bevel switch, material, UV switch, output

Three wires, four frames, one note. The pipeline lives inside the nodes (Tab to look). Use ET Text Mesh as the
modifier instead when you prefer the properties editor: same nodes, inputs as modifier panels."""

from .. import catalog, materials
from ..core import GroupBuilder, NodeRef, builtin_font, heading
from . import et_lines_join, et_mesh_generation, et_text_source

NAME = "Easy Text"

NODE_W = 300  # panel node width; text fields and sliders need the room
COLUMN = 440  # x pitch between the three panel nodes
OUTER_COLOR = (0.055, 0.165, 0.165)  # dark teal, as in v2.1
PANEL_COLOR = (0.085, 0.25, 0.25)
NOTE_COLOR = (0.21, 0.09, 0.23)
TITLE = "Easy Text Geometry Node 3"
NOTE = """Export: apply the modifier (modifier tab > Apply).
The mesh keeps its UVMap and material slots."""


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

    with g.frame(TITLE, label_size=28, color=OUTER_COLOR) as outer:
        with g.frame(heading("Text Input"), color=PANEL_COLOR):
            lines = g.group(et_lines_join.NAME, "Text Lines")
            lines.node.width = NODE_W
            lines.node.inputs["Line 1"].default_value = "Easy Text"
            lines.node.inputs["Line 2"].default_value = "Geometry Node 3"

        with g.frame(heading("Font Settings"), color=PANEL_COLOR):
            text = g.group(et_text_source.NAME, "Text Settings", inputs={"Text": lines["String"]})
            text.node.width = NODE_W
            text.node.inputs["Font"].default_value = builtin_font()
            for name, value in (
                ("Align X", "Center"),
                ("Align Y", "Middle"),
                ("Pivot", "Midpoint"),
                ("Overflow", "Overflow"),
            ):
                text.node.inputs[name].default_value = value

        with g.frame(heading("Mesh Settings"), color=PANEL_COLOR):
            mesh = g.group(et_mesh_generation.NAME, "Mesh Generation", inputs={"Curves": text["Curves"]})
            mesh.node.width = NODE_W + 20
            for name, value in (("Fill Mode", "N-gons"), ("Fill Rule", "Even-Odd")):
                mesh.node.inputs[name].default_value = value
            for name, mat in (
                ("Front Material", "ET Front"),
                ("Side Material", "ET Side"),
                ("Bevel Material", "ET Bevel"),
            ):
                mesh.node.inputs[name].default_value = mats[mat]

        with g.frame("Note", color=NOTE_COLOR, text=NOTE, size=(NODE_W + 60, 200)):  # text wraps to the width
            pass  # the text is the content

    g.set_output("Geometry", mesh["Mesh"])
    g.group_out.parent = outer

    # ---------------------------------------------------------------- layout by hand (v2.1: three panels, output right)
    # Text Lines sits lower so its String output meets the Text input of Text Settings on one level.
    g.place(lines, 0.0, -50.0)
    g.place(text, COLUMN, 0.0)
    g.place(mesh, 2 * COLUMN, 0.0)
    g.place(NodeRef(g.group_out), 3 * COLUMN, 0.0)
    note = next(f for f in g._frame_order if f.label == "Note")
    note.location_absolute = (-30.0, -300.0)  # below the Text Input frame
    return g.finish()
