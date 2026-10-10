"""Materials, shading and cleanup of helper attributes."""

from .. import materials
from ..core import GroupBuilder
from .et_solid import FACE_BEVEL, FACE_SIDE

NAME = ".ET Finish"


def build():
    g = GroupBuilder(NAME, description="Side and bevel material, smooth shading by angle, drop et_* attributes.")
    g.input("Mesh", "geometry")
    g.input("Side Material", "material", materials.ensure("ET Side"))
    g.input("Bevel Material", "material", materials.ensure("ET Bevel"))
    g.input("Smooth Angle", "float", 30.0, min=0.0, max=180.0)
    g.input("Keep Helper Attributes", "bool", False)
    g.output("Mesh", "geometry")

    with g.frame("Materials"):
        gi = g.inputs("Mesh", "Side Material", "Bevel Material")
        mat_side = g.fallback("MATERIAL", gi["Side Material"], materials.ensure("ET Side"), name="Side Material")
        mat_bevel = g.fallback("MATERIAL", gi["Bevel Material"], materials.ensure("ET Bevel"), name="Bevel Material")
        face_group = g.named("et_face_group", "INT", name="Face Group")["Attribute"]
        is_side = g.compare("EQUAL", face_group, FACE_SIDE, data_type="INT", name="Is Side")[0]
        is_bevel = g.compare("EQUAL", face_group, FACE_BEVEL, data_type="INT", name="Is Bevel")[0]
        mesh = g.node(
            "GeometryNodeSetMaterial",
            "Set Side Material",
            inputs={"Geometry": gi["Mesh"], "Selection": is_side, "Material": mat_side},
        )[0]
        mesh = g.node(
            "GeometryNodeSetMaterial",
            "Set Bevel Material",
            inputs={"Geometry": mesh, "Selection": is_bevel, "Material": mat_bevel},
        )[0]

    with g.frame("Shading"):
        gi = g.inputs("Smooth Angle")
        mesh = g.node(
            "GeometryNodeSetShadeSmooth",
            "Smooth Faces",
            inputs={"Geometry": mesh, "Shade Smooth": True},
            props={"domain": "FACE"},
        )[0]
        edge_angle = g.node("GeometryNodeInputMeshEdgeAngle", "Edge Angle")["Unsigned Angle"]
        threshold = g.math("RADIANS", gi["Smooth Angle"], name="Angle (rad)")[0]
        is_sharp = g.compare("GREATER_THAN", edge_angle, threshold, name="Is Sharp")[0]
        mesh = g.node(
            "GeometryNodeSetShadeSmooth",
            "Sharp Edges",
            inputs={"Geometry": mesh, "Shade Smooth": g.boolean("NOT", is_sharp, name="Not Sharp")[0]},
            props={"domain": "EDGE"},
        )[0]

    with g.frame("Cleanup"):
        gi = g.inputs("Keep Helper Attributes")
        stripped = g.node(
            "GeometryNodeRemoveAttribute",
            "Remove et_*",
            inputs={"Geometry": mesh, "Pattern Mode": "Wildcard", "Name": "et_*"},
        )[0]
        final = g.switch("GEOMETRY", gi["Keep Helper Attributes"], stripped, mesh, name="Keep Attributes")[0]
    g.set_output("Mesh", final)
    return g.finish()
