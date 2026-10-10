"""ET Text Mesh: text -> clean, export-ready mesh with UVs (core of Easy Text v3, no animation yet).

Main group with six frames; the work happens in the sub-groups Text Source, Outline Clean, Solid, Bevel,
Text UV and Finish.
"""

from .. import catalog, materials
from ..core import GroupBuilder, builtin_font
from . import et_bevel, et_finish, et_outline, et_solid, et_text_source, et_uv

NAME = "ET Text Mesh"


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

    # ------------------------------------------------------------------ Text
    with g.frame("Text"):
        names = et_text_source.LINE_INPUTS + et_text_source.TYPOGRAPHY_INPUTS
        gi = g.inputs(*names, label="Text")
        source = g.group(et_text_source.NAME, inputs={n: gi[n] for n in names})
        curves, char_count = source["Curves"], source["Character Count"]
        # Warn where the problem arises; the pass-through switch only forces evaluation of the warning.
        no_text = g.compare("EQUAL", char_count, 0, data_type="INT", name="No Text")[0]
        warn_empty = g.node(
            "GeometryNodeWarning",
            "Warn Empty",
            inputs={"Show": no_text, "Message": "No text."},
            props={"warning_type": "WARNING"},
        )["Show"]
        curves = g.switch("GEOMETRY", warn_empty, curves, curves, name="Curves")[0]

    # ------------------------------------------------------------------ Outline
    with g.frame("Outline"):
        gi = g.inputs("Resolution", "Simplify")
        outline = g.group(
            et_outline.NAME, inputs={"Curves": curves, "Resolution": gi["Resolution"], "Simplify": gi["Simplify"]}
        )["Curves"]

    # ------------------------------------------------------------------ Solid
    with g.frame("Solid"):
        gi = g.inputs("Depth", "Fill Mode", "Fill Rule", "Front Material")
        solid = g.group(
            et_solid.NAME,
            inputs={
                "Curves": outline,
                "Depth": gi["Depth"],
                "Fill Mode": gi["Fill Mode"],
                "Fill Rule": gi["Fill Rule"],
                "Front Material": gi["Front Material"],
            },
        )["Mesh"]

    # ------------------------------------------------------------------ Bevel
    with g.frame("Bevel"):
        gi = g.inputs("Bevel", "Bevel Width", "Segments", "Profile", "Depth", label="Bevel")
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
        warn_bevel = g.node(
            "GeometryNodeWarning",
            "Warn Bevel",
            inputs={"Show": bevel["Limited"], "Message": "Bevel width limited to half the depth."},
            props={"warning_type": "INFO"},
        )["Show"]
        bevel_mesh = g.switch("GEOMETRY", warn_bevel, bevel["Mesh"], bevel["Mesh"], name="Mesh")[0]

    # ------------------------------------------------------------------ UV
    with g.frame("UV"):
        gi = g.inputs("UV", "Normalize to Text", "UV Scale", "Depth", label="UV")
        with_uv = g.group(
            et_uv.NAME,
            inputs={
                "Mesh": bevel_mesh,
                "Depth": gi["Depth"],
                "Radius": bevel["Radius"],
                "Normalize to Text": gi["Normalize to Text"],
                "Scale": gi["UV Scale"],
            },
        )["Mesh"]
        mesh = g.switch("GEOMETRY", gi["UV"], bevel_mesh, with_uv, name="Use UV")[0]

    # ------------------------------------------------------------------ Output
    with g.frame("Output"):
        gi = g.inputs("Side Material", "Bevel Material", "Smooth Angle", "Keep Helper Attributes", label="Output")
        final = g.group(
            et_finish.NAME,
            inputs={
                "Mesh": mesh,
                "Side Material": gi["Side Material"],
                "Bevel Material": gi["Bevel Material"],
                "Smooth Angle": gi["Smooth Angle"],
                "Keep Helper Attributes": gi["Keep Helper Attributes"],
            },
        )["Mesh"]
    g.set_output("Geometry", final)
    return g.finish()
