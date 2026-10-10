"""Platzhalter-Gruppe für den Build-Smoke-Test. Wird in Phase 1 durch die echten Gruppen ersetzt."""

from .. import catalog
from ..core import GroupBuilder

NAME = "ET Smoke Test"


def build():
    g = GroupBuilder(
        NAME,
        description="Minimaler Text-zu-Mesh-Pfad, nur zum Prüfen der Build-Kette.",
        is_modifier=True,
        catalog=catalog.UTILS,
    )
    with g.panel("Text", description="Textinhalt und Größe."):
        text = g.input("Text", "string", "Easy Text", description="Der anzuzeigende Text.")
        size = g.input("Size", "float", 1.0, min=0.0, max=100.0, subtype="DISTANCE", description="Schriftgröße.")
    with g.panel("Form", description="Extrusion der Buchstaben.", default_closed=True):
        depth = g.input("Extrude", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE", description="Tiefe.")
    g.output("Geometry", "geometry")

    curves = g.node("GeometryNodeStringToCurves", "String to Curves", inputs={"String": text, "Size": size})
    realized = g.node(
        "GeometryNodeRealizeInstances", "Realize Instances", inputs={"Geometry": curves["Curve Instances"]}
    )
    filled = g.node("GeometryNodeFillCurve", "Fill Curve", inputs={"Curve": realized[0]})
    extruded = g.node(
        "GeometryNodeExtrudeMesh",
        "Extrude Mesh",
        inputs={"Mesh": filled["Mesh"], "Offset Scale": depth},
        props={"mode": "FACES"},
    )
    g.set_output("Geometry", extruded["Mesh"])
    return g.finish()
