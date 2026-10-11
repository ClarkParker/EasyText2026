"""Mesh generation ("Mesh Generation" on the control panel): glyph curves -> clean, export-ready mesh.

Five stages, left to right, each a frame with one sub-group node: Outline Clean, Solid, Bevel, Text UV, Finish.
The inputs are organised in panels so the node itself reads like a settings panel."""

from .. import materials
from ..core import GroupBuilder, heading, subheading
from . import et_bevel, et_finish, et_outline, et_solid, et_uv

NAME = ".ET Mesh Generation"
MESH_INPUTS = (
    "Resolution",
    "Simplify",
    "Fill Mode",
    "Fill Rule",
    "Depth",
    "Bevel",
    "Bevel Width",
    "Segments",
    "Profile",
    "Smooth Angle",
    "Front Material",
    "Side Material",
    "Bevel Material",
    "UV",
    "Normalize to Text",
    "UV Scale",
    "Keep Helper Attributes",
)


def build():
    mats = materials.ensure_all()
    g = GroupBuilder(
        NAME,
        description="Glyph curves to a clean mesh: outline, extrusion, bevel, materials, export-ready UVs.",
        default_width=320,
    )

    # ------------------------------------------------------------------ Interface (order defines identifiers)
    g.input("Curves", "geometry", description="Glyph outlines from Text Settings.")
    with g.panel(heading("Outline"), description="Quality of the glyph outlines."):
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
    with g.panel(heading("Shape")):
        g.input("Depth", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE", description="Extrusion depth.")
        with g.panel(subheading("Bevel"), description="Rounded front and back edges."):
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
    with g.panel(heading("Material")):
        g.input("Front Material", "material", mats["ET Front"], description="Also used for the back face.")
        g.input("Side Material", "material", mats["ET Side"])
        g.input("Bevel Material", "material", mats["ET Bevel"])
    with g.panel(heading("UV"), description="UV map 'UVMap': planar caps, sides and bevel along the outline."):
        g.input("UV", "bool", True, panel_toggle=True)
        g.input(
            "Normalize to Text",
            "bool",
            True,
            description="Scale the caps into 0..1; off = Blender units (tileable).",
        )
        g.input("UV Scale", "float", 1.0, min=0.0001, max=1000.0, description="Additional UV factor.")
    with g.panel(heading("Output"), default_closed=True):
        g.input(
            "Keep Helper Attributes",
            "bool",
            False,
            description="Keep the et_* attributes (character index, contour length, face group) on the mesh.",
        )
    g.output("Mesh", "geometry")
    for name, value in (("Fill Mode", "N-gons"), ("Fill Rule", "Even-Odd")):
        g.menu_default(name, value)

    # ------------------------------------------------------------------ Stages
    with g.frame("Outline"):
        gi = g.inputs("Curves", "Resolution", "Simplify", label="Outline")
        outline = g.group(
            et_outline.NAME,
            inputs={"Curves": gi["Curves"], "Resolution": gi["Resolution"], "Simplify": gi["Simplify"]},
        )["Curves"]

    with g.frame("Solid"):
        gi = g.inputs("Fill Mode", "Fill Rule", "Front Material", "Depth", label="Solid")
        solid = g.group(
            et_solid.NAME,
            inputs={
                "Curves": outline,
                "Fill Mode": gi["Fill Mode"],
                "Fill Rule": gi["Fill Rule"],
                "Front Material": gi["Front Material"],
                "Depth": gi["Depth"],
            },
        )["Mesh"]

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

    with g.frame("UV"):
        gi = g.inputs("UV", "Normalize to Text", "UV Scale", "Depth", label="UV")
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
        gi = g.inputs("Side Material", "Bevel Material", "Smooth Angle", "Keep Helper Attributes", label="Finish")
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
    g.set_output("Mesh", final)
    return g.finish()
