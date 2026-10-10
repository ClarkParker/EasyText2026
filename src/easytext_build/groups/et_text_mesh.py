"""ET Text Mesh: text -> clean, export-ready mesh with UVs (core of Easy Text v3, no animation yet).

Six stages, left to right, each one a frame with a single sub-group node: Text Source, Outline Clean, Solid,
Bevel, Text UV and Finish. `build_pipeline` wires the stages and is shared with the Easy Text control panel,
which feeds the same pipeline from value nodes instead of the group interface.
"""

from .. import catalog, materials
from ..core import GroupBuilder, SocketRef, builtin_font
from . import et_bevel, et_finish, et_outline, et_solid, et_text_source, et_uv

NAME = "ET Text Mesh"


def _wire(gi: dict, names) -> dict:
    """Only the inputs the provider has; a provider may leave some out (the panel has no Line 2-4)."""
    return {n: gi[n] for n in names if n in gi}


def build_pipeline(g: GroupBuilder, provide) -> SocketRef:
    """The six stages. `provide(stage, *names)` returns {name: SocketRef} for the inputs a stage needs: local
    Group Input copies in ET Text Mesh, value nodes (controls) in the Easy Text panel. Returns the final mesh."""
    with g.frame("Text"):
        names = et_text_source.LINE_INPUTS + et_text_source.TYPOGRAPHY_INPUTS
        gi = provide("Text", *names)
        curves = g.group(et_text_source.NAME, inputs=_wire(gi, names))["Curves"]

    with g.frame("Outline"):
        gi = provide("Outline", "Resolution", "Simplify")
        outline = g.group(et_outline.NAME, inputs={"Curves": curves, **_wire(gi, ("Resolution", "Simplify"))})["Curves"]

    with g.frame("Solid"):
        # Depth last: in the panel it sits closest to the bus that carries it on to Bevel and UV.
        gi = provide("Solid", "Fill Mode", "Fill Rule", "Front Material", "Depth")
        solid = g.group(
            et_solid.NAME,
            inputs={"Curves": outline, **_wire(gi, ("Fill Mode", "Fill Rule", "Front Material", "Depth"))},
        )["Mesh"]

    with g.frame("Bevel"):
        gi = provide("Bevel", "Bevel", "Bevel Width", "Segments", "Profile", "Depth")
        bevel = g.group(
            et_bevel.NAME,
            inputs={
                "Mesh": solid,
                "Bevel": gi["Bevel"],
                "Width": gi["Bevel Width"],
                "Segments": gi["Segments"],
                "Profile": gi["Profile"],
                "Depth": gi["Depth"],
            },
        )

    with g.frame("UV"):
        gi = provide("UV", "UV", "Normalize to Text", "UV Scale", "Depth")
        mesh = g.group(
            et_uv.NAME,
            inputs={
                "Mesh": bevel["Mesh"],
                "UV": gi["UV"],
                "Depth": gi["Depth"],
                "Radius": bevel["Radius"],
                "Normalize to Text": gi["Normalize to Text"],
                "Scale": gi["UV Scale"],
            },
        )["Mesh"]

    with g.frame("Finish"):
        gi = provide("Finish", "Side Material", "Bevel Material", "Smooth Angle", "Keep Helper Attributes")
        final = g.group(
            et_finish.NAME,
            inputs={
                "Mesh": mesh,
                **_wire(gi, ("Side Material", "Bevel Material", "Smooth Angle", "Keep Helper Attributes")),
            },
        )["Mesh"]
    return final


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

    # ------------------------------------------------------------------ Stages: local Group Input copies
    final = build_pipeline(g, lambda stage, *names: g.inputs(*names, label=stage))
    g.set_output("Geometry", final)
    return g.finish()
