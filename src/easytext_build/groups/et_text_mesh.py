"""ET Text Mesh: text -> clean, export-ready mesh with UVs, as one node group for the properties editor.

Its inputs are the modifier panels; inside, the same three nodes as the Easy Text control panel do the work:
Lines Join, Text Source ("Text Settings") and Mesh Generation.
"""

from .. import catalog, materials
from ..core import GroupBuilder, builtin_font
from . import et_lines_join, et_mesh_generation, et_text_source

NAME = "ET Text Mesh"
LINE_INPUTS = ("Text", "Line 2", "Line 3", "Line 4")


def build():
    mats = materials.ensure_all()
    g = GroupBuilder(
        NAME,
        description="Text as a clean mesh with extrusion, bevel, materials and export-ready UVs.",
        is_modifier=True,
        catalog=catalog.TEXT,
        color_tag="GEOMETRY",
        default_width=240,
    )

    # ------------------------------------------------------------------ Interface (order defines identifiers)
    with g.panel("Text", description="Up to four lines; empty lines are skipped."):
        g.input("Text", "string", "Easy Text", description="First line.")
        for i in (2, 3, 4):
            g.input(f"Line {i}", "string", "", description=f"Line {i}, optional.")
    with g.panel("Typography"):
        g.input("Font", "font", builtin_font(), description="Font data-block.")
        g.input("Size", "float", 1.0, min=0.001, max=100.0, subtype="DISTANCE", description="Font size.")
        g.input("Align X", "menu", description="Horizontal alignment of the lines.")
        g.input("Align Y", "menu", description="Vertical alignment of the text block.")
        g.input("Pivot", "menu", description="Origin of the text block.")
        g.input("Character Spacing", "float", 1.0, min=0.0, max=10.0, description="Spacing factor between characters.")
        g.input("Word Spacing", "float", 1.0, min=0.0, max=10.0, description="Spacing factor between words.")
        g.input("Line Spacing", "float", 1.0, min=0.0, max=10.0, description="Spacing factor between lines.")
        with g.panel("Text Box", description="Wrapping and overflow.", default_closed=True):
            g.input("Box Width", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = no wrapping.")
            g.input("Box Height", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = unlimited.")
            g.input("Overflow", "menu", description="What happens when the text does not fit the box.")
    with g.panel("Outline", description="Quality of the glyph outlines."):
        g.input("Resolution", "int", 12, min=1, max=64, description="Points per curve segment.")
        g.input(
            "Simplify",
            "float",
            0.5,
            min=0.0,
            max=10.0,
            description="Remove points whose direction changes less than this angle (degrees). 0 = off.",
        )
        g.input("Fill Mode", "menu", description="N-gons or triangles on the caps.")
        g.input("Fill Rule", "menu", description="Even-Odd or Non-Zero for overlapping outlines.")
    with g.panel("Shape"):
        g.input("Depth", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE", description="Extrusion depth.")
        with g.panel("Bevel", description="Rounded front and back edges."):
            g.input("Bevel", "bool", False, panel_toggle=True)
            g.input(
                "Bevel Width",
                "float",
                0.01,
                min=0.0,
                max=1.0,
                subtype="DISTANCE",
                description="Bevel width, at most half the depth.",
            )
            g.input("Segments", "int", 3, min=1, max=16, description="Bevel subdivisions.")
            g.input("Profile", "float", 0.5, min=0.0, max=1.0, subtype="FACTOR", description="0.5 = round.")
        g.input(
            "Smooth Angle",
            "float",
            30.0,
            min=0.0,
            max=180.0,
            description="Edges above this angle (degrees) stay sharp.",
        )
    with g.panel("Material"):
        g.input("Front Material", "material", mats["ET Front"], description="Also used for the back face.")
        g.input("Side Material", "material", mats["ET Side"])
        g.input("Bevel Material", "material", mats["ET Bevel"])
    with g.panel("UV", description="UV map 'UVMap': planar caps, sides and bevel along the outline."):
        g.input("UV", "bool", True, panel_toggle=True)
        g.input(
            "Normalize to Text",
            "bool",
            True,
            description="Scale the caps into 0..1; off = Blender units (tileable).",
        )
        g.input("UV Scale", "float", 1.0, min=0.0001, max=1000.0, description="Additional UV factor.")
    with g.panel("Output", default_closed=True):
        g.input(
            "Keep Helper Attributes",
            "bool",
            False,
            description="Keep the et_* attributes (character index, contour length, face group) on the mesh.",
        )
    g.output("Geometry", "geometry")
    for name, value in (
        ("Align X", "Center"),
        ("Align Y", "Middle"),
        ("Pivot", "Midpoint"),
        ("Overflow", "Overflow"),
        ("Fill Mode", "N-gons"),
        ("Fill Rule", "Even-Odd"),
    ):
        g.menu_default(name, value)

    # ------------------------------------------------------------------ Text: lines -> glyph curves
    with g.frame("Text"):
        gi = g.inputs(*LINE_INPUTS, label="Lines")
        joined = g.group(
            et_lines_join.NAME,
            "Lines Join",
            inputs={f"Line {i}": gi[name] for i, name in enumerate(LINE_INPUTS, start=1)},
        )["String"]
        gi = g.inputs(*et_text_source.TYPOGRAPHY_INPUTS, label="Typography")
        curves = g.group(
            et_text_source.NAME,
            "Text Source",
            inputs={"Text": joined, **{name: gi[name] for name in et_text_source.TYPOGRAPHY_INPUTS}},
        )["Curves"]

    # ------------------------------------------------------------------ Mesh: curves -> finished mesh
    with g.frame("Mesh"):
        gi = g.inputs(*et_mesh_generation.MESH_INPUTS, label="Mesh")
        mesh = g.group(
            et_mesh_generation.NAME,
            "Mesh Generation",
            inputs={"Curves": curves, **{name: gi[name] for name in et_mesh_generation.MESH_INPUTS}},
        )["Mesh"]
    g.set_output("Geometry", mesh)
    return g.finish()
