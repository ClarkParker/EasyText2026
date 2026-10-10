"""Bevel the front and back edge loops with Mesh Bevel; outputs the effective radius for the UVs."""

from ..core import GroupBuilder
from .et_solid import FACE_BEVEL

NAME = ".ET Bevel"


def build():
    g = GroupBuilder(NAME, description="Mesh Bevel on the face-group boundary edges; new faces become group 3 (bevel).")
    g.input("Mesh", "geometry")
    g.input("Bevel", "bool", False)
    g.input("Width", "float", 0.01, min=0.0, max=1.0, subtype="DISTANCE")
    g.input("Segments", "int", 3, min=1, max=16)
    g.input("Profile", "float", 0.5, min=0.0, max=1.0, subtype="FACTOR")
    g.input("Depth", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE")
    g.output("Mesh", "geometry")
    g.output("Radius", "float", description="Effective bevel radius (0 when off).")
    g.output("Limited", "bool", description="True when the width was clamped to half the depth.")

    with g.frame("Radius"):
        gi = g.inputs("Bevel", "Width", "Depth")
        r_max = g.math(
            "SUBTRACT", g.math("MULTIPLY", gi["Depth"], 0.5, name="Half Depth")[0], 0.0001, name="Max Radius"
        )[0]
        r_clamped = g.math(
            "MAXIMUM", g.math("MINIMUM", gi["Width"], r_max, name="Clamp Max")[0], 0.0, name="Clamp Min"
        )[0]
        radius = g.switch("FLOAT", gi["Bevel"], 0.0, r_clamped, name="Radius")[0]
        too_wide = g.compare("GREATER_THAN", gi["Width"], r_max, name="Too Wide")[0]
        limited = g.boolean("AND", gi["Bevel"], too_wide, name="Limited")[0]

    with g.frame("Edges"):
        face_group = g.named("et_face_group", "INT", name="Face Group")["Attribute"]
        boundary = g.node("GeometryNodeMeshFaceSetBoundaries", "Cap Edges", inputs={"Face Set": face_group})[
            "Boundary Edges"
        ]

    with g.frame("Mesh Bevel"):
        gi = g.inputs("Mesh", "Bevel", "Segments", "Profile")
        bevel = g.node(
            "GeometryNodeMeshBevel",
            "Mesh Bevel",
            # The four end offsets default to 0.1 and override "Offset": set all of them to the radius.
            inputs={
                "Mesh": gi["Mesh"],
                "Selection": boundary,
                "Offset": r_clamped,
                "Segments": gi["Segments"],
                "Shape": gi["Profile"],
                "Start Left Offset": r_clamped,
                "Start Right Offset": r_clamped,
                "End Left Offset": r_clamped,
                "End Right Offset": r_clamped,
            },
        )
        new_faces = g.boolean("OR", bevel["Edge Face"], bevel["Vertex Face"], name="Bevel Faces")[0]
        ring = g.store(
            bevel["Mesh"],
            "et_face_group",
            FACE_BEVEL,
            domain="FACE",
            data_type="INT",
            selection=new_faces,
            name="Group Bevel",
        )[0]
        body = g.switch("GEOMETRY", gi["Bevel"], gi["Mesh"], ring, name="Use Bevel")[0]

    with g.frame("Warning"):
        shown = g.node(
            "GeometryNodeWarning",
            "Warn Bevel",
            inputs={"Show": limited, "Message": "Bevel width limited to half the depth."},
            props={"warning_type": "INFO"},
        )["Show"]
        body = g.switch("GEOMETRY", shown, body, body, name="Mesh")[0]
    g.set_output("Mesh", body)
    g.set_output("Radius", radius)
    g.set_output("Limited", limited)
    return g.finish()
