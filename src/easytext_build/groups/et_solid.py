"""Geschlossener Körper: Fill, Attribute übernehmen, Rückseite + Extrusion, Flächengruppen."""

from .. import materials
from ..core import GroupBuilder

NAME = ".ET Solid"
FACE_SIDE, FACE_FRONT, FACE_BACK, FACE_BEVEL = 0, 1, 2, 3


def build():
    description = (
        "Konturen füllen und zu einem geschlossenen Mesh extrudieren; Flächengruppen 0 Seite, 1 Front, 2 Rück."
    )
    g = GroupBuilder(NAME, description=description)
    g.input("Curves", "geometry")
    g.input("Tiefe", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE")
    g.input("Füllung", "menu")
    g.input("Füllregel", "menu")
    g.input("Front Material", "material", materials.ensure("ET Front"))
    g.output("Mesh", "geometry")
    g.menu_default("Füllung", "N-gons")
    g.menu_default("Füllregel", "Even-Odd")

    with g.frame("Fill"):
        gi = g.inputs("Curves", "Füllung", "Füllregel", "Front Material")
        fill = g.node(
            "GeometryNodeFillCurve",
            "Fill",
            inputs={"Curve": gi["Curves"], "Mode": gi["Füllung"], "Fill Rule": gi["Füllregel"]},
        )["Mesh"]
        normal_z = g.separate_xyz(g.node("GeometryNodeInputNormal", "Normal")["Normal"], name="Normal XYZ")["Z"]
        fill_up = g.node(
            "GeometryNodeFlipFaces",
            "Face +Z",
            inputs={"Mesh": fill, "Selection": g.compare("LESS_THAN", normal_z, 0.0, name="Faces Down")[0]},
        )[0]
        mat_front = g.fallback("MATERIAL", gi["Front Material"], materials.ensure("ET Front"), name="Front Material")
        fill_up = g.node(
            "GeometryNodeSetMaterial", "Material Front", inputs={"Geometry": fill_up, "Material": mat_front}
        )[0]

    with g.frame("Attribute übernehmen"):
        gi = g.inputs("Curves")
        position = g.node("GeometryNodeInputPosition", "Position")[0]
        points = g.node(
            "GeometryNodeCurveToPoints", "Outline Points", inputs={"Curve": gi["Curves"]}, props={"mode": "EVALUATED"}
        )["Points"]
        nearest = g.node(
            "GeometryNodeSampleNearest",
            "Nearest Outline Point",
            inputs={"Geometry": points, "Sample Position": position},
            props={"domain": "POINT"},
        )["Index"]
        cap = fill_up
        for attr, data_type in (("et_u", "FLOAT"), ("et_loop_len", "FLOAT"), ("et_char_index", "INT")):
            value = g.sample_index(
                points,
                g.named(attr, data_type, name=f"{attr} (points)")["Attribute"],
                nearest,
                data_type=data_type,
                name=f"Fetch {attr}",
            )[0]
            cap = g.store(cap, attr, value, data_type=data_type, name=f"Store {attr}")[0]

    with g.frame("Rückseite + Extrusion"):
        gi = g.inputs("Tiefe")
        back = g.store(cap, "et_face_group", FACE_BACK, domain="FACE", data_type="INT", name="Group Back")[0]
        back_flipped = g.node("GeometryNodeFlipFaces", "Flip Back", inputs={"Mesh": back})[0]
        extrude = g.node(
            "GeometryNodeExtrudeMesh",
            "Extrude",
            inputs={"Mesh": back, "Offset Scale": gi["Tiefe"], "Individual": False},
            props={"mode": "FACES"},
        )
        front = g.store(
            extrude["Mesh"],
            "et_face_group",
            FACE_FRONT,
            domain="FACE",
            data_type="INT",
            selection=extrude["Top"],
            name="Group Front",
        )[0]
        sides = g.store(
            front,
            "et_face_group",
            FACE_SIDE,
            domain="FACE",
            data_type="INT",
            selection=extrude["Side"],
            name="Group Side",
        )[0]
        solid = g.node("GeometryNodeJoinGeometry", "Join Solid", inputs={"Geometry": [sides, back_flipped]})[0]
        solid = g.node("GeometryNodeMergeByDistance", "Close Solid", inputs={"Geometry": solid, "Distance": 0.00001})[0]
    g.set_output("Mesh", solid)
    return g.finish()
