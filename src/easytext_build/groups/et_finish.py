"""Materialien, Shading und Aufräumen der Hilfsattribute."""

from .. import materials
from ..core import GroupBuilder
from .et_solid import FACE_BEVEL, FACE_SIDE

NAME = ".ET Finish"


def build():
    g = GroupBuilder(
        NAME, description="Seiten- und Bevel-Material, Shade Smooth mit Winkelgrenze, et_*-Attribute entfernen."
    )
    g.input("Mesh", "geometry")
    g.input("Seite", "material", materials.ensure("ET Side"))
    g.input("Bevelfläche", "material", materials.ensure("ET Bevel"))
    g.input("Glättungswinkel", "float", 30.0, min=0.0, max=180.0)
    g.input("Hilfsattribute behalten", "bool", False)
    g.output("Mesh", "geometry")

    with g.frame("Materialien"):
        gi = g.inputs("Mesh", "Seite", "Bevelfläche")
        mat_side = g.fallback("MATERIAL", gi["Seite"], materials.ensure("ET Side"), name="Side Material")
        mat_bevel = g.fallback("MATERIAL", gi["Bevelfläche"], materials.ensure("ET Bevel"), name="Bevel Material")
        face_group = g.named("et_face_group", "INT", name="Face Group")["Attribute"]
        mesh = g.node(
            "GeometryNodeSetMaterial",
            "Material Side",
            inputs={
                "Geometry": gi["Mesh"],
                "Selection": g.compare("EQUAL", face_group, FACE_SIDE, data_type="INT", name="Is Side")[0],
                "Material": mat_side,
            },
        )[0]
        mesh = g.node(
            "GeometryNodeSetMaterial",
            "Material Bevel",
            inputs={
                "Geometry": mesh,
                "Selection": g.compare("EQUAL", face_group, FACE_BEVEL, data_type="INT", name="Is Bevel")[0],
                "Material": mat_bevel,
            },
        )[0]

    with g.frame("Shading"):
        gi = g.inputs("Glättungswinkel")
        mesh = g.node(
            "GeometryNodeSetShadeSmooth",
            "Smooth Faces",
            inputs={"Geometry": mesh, "Shade Smooth": True},
            props={"domain": "FACE"},
        )[0]
        edge_angle = g.node("GeometryNodeInputMeshEdgeAngle", "Edge Angle")["Unsigned Angle"]
        is_sharp = g.compare(
            "GREATER_THAN", edge_angle, g.math("RADIANS", gi["Glättungswinkel"], name="Angle (rad)")[0], name="Is Sharp"
        )[0]
        mesh = g.node(
            "GeometryNodeSetShadeSmooth",
            "Sharp Edges",
            inputs={"Geometry": mesh, "Shade Smooth": g.boolean("NOT", is_sharp, name="Not Sharp")[0]},
            props={"domain": "EDGE"},
        )[0]

    with g.frame("Aufräumen"):
        gi = g.inputs("Hilfsattribute behalten")
        stripped = g.node(
            "GeometryNodeRemoveAttribute",
            "Remove et_*",
            inputs={"Geometry": mesh, "Pattern Mode": "Wildcard", "Name": "et_*"},
        )[0]
        final = g.switch("GEOMETRY", gi["Hilfsattribute behalten"], stripped, mesh, name="Keep Attributes")[0]
    g.set_output("Mesh", final)
    return g.finish()
