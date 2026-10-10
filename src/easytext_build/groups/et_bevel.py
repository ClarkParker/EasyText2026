"""Bevel der Vorder- und Rückkanten mit Mesh Bevel; liefert den wirksamen Radius für die UVs."""

from ..core import GroupBuilder
from .et_solid import FACE_BEVEL

NAME = ".ET Bevel"


def build():
    g = GroupBuilder(
        NAME, description="Mesh Bevel auf den Grenzkanten der Flächengruppen; neue Flächen werden Gruppe 3 (Bevel)."
    )
    g.input("Mesh", "geometry")
    g.input("Bevel", "bool", False)
    g.input("Breite", "float", 0.01, min=0.0, max=1.0, subtype="DISTANCE")
    g.input("Segmente", "int", 3, min=1, max=16)
    g.input("Profil", "float", 0.5, min=0.0, max=1.0, subtype="FACTOR")
    g.input("Tiefe", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE")
    g.output("Mesh", "geometry")
    g.output("Radius", "float", description="Wirksamer Bevel-Radius (0 wenn aus).")
    g.output("Begrenzt", "bool", description="True, wenn die Breite auf die halbe Tiefe begrenzt wurde.")

    with g.frame("Radius"):
        gi = g.inputs("Bevel", "Breite", "Tiefe")
        r_max = g.math(
            "SUBTRACT", g.math("MULTIPLY", gi["Tiefe"], 0.5, name="Half Depth")[0], 0.0001, name="Max Radius"
        )[0]
        r_clamped = g.math(
            "MAXIMUM", g.math("MINIMUM", gi["Breite"], r_max, name="Clamp Max")[0], 0.0, name="Clamp Min"
        )[0]
        radius = g.switch("FLOAT", gi["Bevel"], 0.0, r_clamped, name="Radius")[0]
        limited = g.boolean(
            "AND", gi["Bevel"], g.compare("GREATER_THAN", gi["Breite"], r_max, name="Too Wide")[0], name="Limited"
        )[0]

    with g.frame("Kanten"):
        face_group = g.named("et_face_group", "INT", name="Face Group")["Attribute"]
        boundary = g.node("GeometryNodeMeshFaceSetBoundaries", "Cap Edges", inputs={"Face Set": face_group})[
            "Boundary Edges"
        ]

    with g.frame("Mesh Bevel"):
        gi = g.inputs("Mesh", "Bevel", "Segmente", "Profil")
        bevel = g.node(
            "GeometryNodeMeshBevel",
            "Mesh Bevel",
            # Die vier Enden-Offsets haben Default 0.1 und überstimmen "Offset": alle auf den Radius setzen.
            inputs={
                "Mesh": gi["Mesh"],
                "Selection": boundary,
                "Offset": r_clamped,
                "Segments": gi["Segmente"],
                "Shape": gi["Profil"],
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
    g.set_output("Mesh", body)
    g.set_output("Radius", radius)
    g.set_output("Begrenzt", limited)
    return g.finish()
