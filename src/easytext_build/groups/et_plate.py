"""Plate: a rounded base plate behind the text (the "Beveled Plate" of v2.1, rebuilt).

Rounded rectangle sized from the text (or by hand) with thickness, a bevelled top rim and an optional relief:
the plate top rises around the letters (Geometry Proximity on a subdivided top, bounded cost). The plate carries
face group 4 and character index -1, so the animation leaves it alone; it has its own planar UVMap and material."""

from .. import materials
from ..core import GroupBuilder, heading, subheading

NAME = ".ET Plate"
FACE_PLATE = 4
PLATE_INPUTS = (
    "Plate",
    "Fit to Text",
    "Margin X",
    "Margin Y",
    "Plate Width",
    "Plate Height",
    "Corner Radius",
    "Thickness",
    "Edge Bevel",
    "Gap",
    "Relief",
    "Relief Height",
    "Relief Width",
    "Relief Detail",
    "Plate Material",
)


def declare_inputs(g: GroupBuilder, *, decorated: bool) -> None:
    """The plate inputs as a panel; shared by this group (decorated) and ET Text Mesh / Mesh Generation."""
    h = heading if decorated else (lambda name: name)
    sub = subheading if decorated else (lambda name: name)
    with g.panel(h("Plate"), description="A rounded base plate behind the text.", default_closed=True):
        g.input("Plate", "bool", False, panel_toggle=True)
        g.input("Fit to Text", "bool", True, description="Size the plate from the text bounds plus the margins.")
        g.input("Margin X", "float", 0.5, min=0.0, max=100.0, subtype="DISTANCE", description="Left and right.")
        g.input("Margin Y", "float", 0.3, min=0.0, max=100.0, subtype="DISTANCE", description="Top and bottom.")
        g.input("Plate Width", "float", 6.0, min=0.01, max=1000.0, subtype="DISTANCE", description="When not fitted.")
        g.input("Plate Height", "float", 3.0, min=0.01, max=1000.0, subtype="DISTANCE", description="When not fitted.")
        g.input("Corner Radius", "float", 0.3, min=0.0, max=100.0, subtype="DISTANCE")
        g.input("Thickness", "float", 0.2, min=0.001, max=100.0, subtype="DISTANCE")
        g.input("Edge Bevel", "float", 0.05, min=0.0, max=10.0, subtype="DISTANCE", description="Top rim; 0 = off.")
        g.input(
            "Gap",
            "float",
            0.0,
            min=-10.0,
            max=10.0,
            subtype="DISTANCE",
            description="Space between plate and text back; negative sinks the text into the plate.",
        )
        with g.panel(sub("Relief"), description="The plate top rises around the letters.", default_closed=True):
            g.input("Relief", "bool", False, panel_toggle=True)
            g.input("Relief Height", "float", 0.05, min=0.0, max=10.0, subtype="DISTANCE")
            g.input("Relief Width", "float", 0.3, min=0.001, max=100.0, subtype="DISTANCE", description="Reach.")
            g.input("Relief Detail", "int", 3, min=1, max=6, description="Subdivision levels of the plate top.")
        g.input("Plate Material", "material", materials.ensure("ET Plate"))


def build():
    g = GroupBuilder(
        NAME,
        description="Rounded base plate behind the text with bevelled rim, optional relief, own UVs and material.",
    )
    g.input("Mesh", "geometry", description="The finished text mesh.")
    declare_inputs(g, decorated=True)
    g.output("Mesh", "geometry", description="Text and plate joined.")

    # ------------------------------------------------------------------ size and centre
    with g.frame("Size"):
        gi = g.inputs("Mesh", "Fit to Text", "Margin X", "Margin Y", "Plate Width", "Plate Height", label="Size")
        bbox = g.node("GeometryNodeBoundBox", "Text Bounds", inputs={"Geometry": gi["Mesh"]})
        bmin = g.separate_xyz(bbox["Min"], name="Bounds Min")
        bmax = g.separate_xyz(bbox["Max"], name="Bounds Max")
        fit_w = g.math(
            "ADD",
            g.math("SUBTRACT", bmax["X"], bmin["X"], name="Text Width")[0],
            g.math("MULTIPLY", gi["Margin X"], 2.0, name="2 × Margin X")[0],
            name="Fitted Width",
        )[0]
        fit_h = g.math(
            "ADD",
            g.math("SUBTRACT", bmax["Y"], bmin["Y"], name="Text Height")[0],
            g.math("MULTIPLY", gi["Margin Y"], 2.0, name="2 × Margin Y")[0],
            name="Fitted Height",
        )[0]
        width = g.switch("FLOAT", gi["Fit to Text"], gi["Plate Width"], fit_w, name="Width")[0]
        height = g.switch("FLOAT", gi["Fit to Text"], gi["Plate Height"], fit_h, name="Height")[0]
        cx = g.switch(
            "FLOAT",
            gi["Fit to Text"],
            0.0,
            g.math("MULTIPLY", g.math("ADD", bmin["X"], bmax["X"], name="Min + Max X")[0], 0.5, name="Centre X fit")[0],
            name="Centre X",
        )[0]
        cy = g.switch(
            "FLOAT",
            gi["Fit to Text"],
            0.0,
            g.math("MULTIPLY", g.math("ADD", bmin["Y"], bmax["Y"], name="Min + Max Y")[0], 0.5, name="Centre Y fit")[0],
            name="Centre Y",
        )[0]

    # ------------------------------------------------------------------ rounded outline -> top face
    with g.frame("Outline"):
        gi = g.inputs("Corner Radius", "Gap", label="Outline")
        rect = g.node(
            "GeometryNodeCurvePrimitiveQuadrilateral",
            "Rectangle",
            props={"mode": "RECTANGLE"},
            inputs={"Width": width, "Height": height},
        )["Curve"]
        half_min = g.math(
            "SUBTRACT",
            g.math("MULTIPLY", g.math("MINIMUM", width, height, name="Smaller Side")[0], 0.5, name="Half Side")[0],
            0.001,
            name="Max Radius",
        )[0]
        radius = g.math("MINIMUM", gi["Corner Radius"], half_min, name="Radius")[0]
        rounded = g.node(
            "GeometryNodeFilletCurve",
            "Round Corners",
            inputs={"Curve": rect, "Radius": radius, "Limit Radius": True, "Mode": "Poly", "Count": 8},
        )["Curve"]
        cap = g.node("GeometryNodeFillCurve", "Fill Plate", inputs={"Curve": rounded, "Mode": "N-gons"})["Mesh"]
        normal_z = g.separate_xyz(g.node("GeometryNodeInputNormal", "Normal")[0], name="Normal XYZ")["Z"]
        faces_down = g.compare("LESS_THAN", normal_z, 0.0, name="Faces Down")[0]
        cap = g.node("GeometryNodeFlipFaces", "Face +Z", inputs={"Mesh": cap, "Selection": faces_down})[0]
        top_z = g.math("MULTIPLY", gi["Gap"], -1.0, name="Top Z")[0]
        top = g.node(
            "GeometryNodeTransform",
            "Place Plate",
            inputs={"Geometry": cap, "Translation": g.combine_xyz(cx, cy, top_z, name="Plate Centre")[0]},
        )[0]

    # ------------------------------------------------------------------ relief around the letters
    with g.frame("Relief"):
        gi = g.inputs("Mesh", "Relief", "Relief Height", "Relief Width", "Relief Detail", label="Relief")
        fine = g.node("GeometryNodeTriangulate", "Triangulate", inputs={"Mesh": top})[0]
        fine = g.node(
            "GeometryNodeSubdivideMesh", "Subdivide Top", inputs={"Mesh": fine, "Level": gi["Relief Detail"]}
        )[0]
        distance = g.node(
            "GeometryNodeProximity",
            "Distance to Text",
            props={"target_element": "FACES"},
            inputs={"Geometry": gi["Mesh"]},
        )["Distance"]
        bump = g.node(
            "ShaderNodeMapRange",
            "Bump",
            props={"interpolation_type": "SMOOTHSTEP"},
            inputs={
                "Value": distance,
                "From Min": 0.0,
                "From Max": gi["Relief Width"],
                "To Min": gi["Relief Height"],
                "To Max": 0.0,
            },
        )["Result"]
        raised = g.node(
            "GeometryNodeSetPosition",
            "Raise Top",
            inputs={"Geometry": fine, "Offset": g.combine_xyz(0.0, 0.0, bump, name="Bump Offset")[0]},
        )[0]
        top = g.switch("GEOMETRY", gi["Relief"], top, raised, name="Relief?")[0]

    # ------------------------------------------------------------------ body: bottom copy, sides, groups
    with g.frame("Body"):
        gi = g.inputs("Thickness", label="Body")
        top = g.store(top, "plate_part", 1, domain="FACE", data_type="INT", name="Top Faces")[0]
        bottom = g.node("GeometryNodeFlipFaces", "Flip Bottom", inputs={"Mesh": top})[0]
        bottom = g.store(bottom, "plate_part", 0, domain="FACE", data_type="INT", name="Bottom Faces")[0]
        extruded = g.node(
            "GeometryNodeExtrudeMesh",
            "Extrude Down",
            props={"mode": "FACES"},
            inputs={
                "Mesh": bottom,
                "Offset": g.combine_xyz(0.0, 0.0, g.math("MULTIPLY", gi["Thickness"], -1.0, name="-Thickness")[0])[0],
                "Offset Scale": 1.0,
                "Individual": False,
            },
        )
        body = g.node("GeometryNodeJoinGeometry", "Join Plate", inputs={"Geometry": [top, extruded["Mesh"]]})[0]
        body = g.node("GeometryNodeMergeByDistance", "Close Plate", inputs={"Geometry": body, "Distance": 0.00001})[0]
        body = g.store(body, "et_face_group", FACE_PLATE, domain="FACE", data_type="INT", name="Group Plate")[0]
        body = g.store(body, "et_char_index", -1, domain="POINT", data_type="INT", name="No Character")[0]

    # ------------------------------------------------------------------ bevelled top rim
    with g.frame("Rim"):
        gi = g.inputs("Edge Bevel", "Thickness", label="Rim")
        part = g.named("plate_part", "INT", name="Plate Part")["Attribute"]
        rim = g.node("GeometryNodeMeshFaceSetBoundaries", "Rim Edges", inputs={"Face Set": part})["Boundary Edges"]
        r = g.math(
            "MINIMUM", gi["Edge Bevel"], g.math("MULTIPLY", gi["Thickness"], 0.45, name="Max Rim")[0], name="Rim"
        )[0]
        bevelled = g.node(
            "GeometryNodeMeshBevel",
            "Bevel Rim",
            inputs={
                "Mesh": body,
                "Selection": rim,
                "Offset": r,
                "Segments": 3,
                "Shape": 0.5,
                "Start Left Offset": r,
                "Start Right Offset": r,
                "End Left Offset": r,
                "End Right Offset": r,
            },
        )["Mesh"]
        use_bevel = g.compare("GREATER_THAN", gi["Edge Bevel"], 0.0, name="Bevel?")[0]
        body = g.switch("GEOMETRY", use_bevel, body, bevelled, name="Rim Bevel")[0]
        body = g.node(
            "GeometryNodeRemoveAttribute",
            "Drop plate_part",
            inputs={"Geometry": body, "Pattern Mode": "Exact", "Name": "plate_part"},
        )[0]

    # ------------------------------------------------------------------ UVs and material
    with g.frame("UV + Material"):
        gi = g.inputs("Plate Material", label="Material")
        pos = g.separate_xyz(g.node("GeometryNodeInputPosition", "Position")[0], name="Position XYZ")
        left = g.math("SUBTRACT", cx, g.math("MULTIPLY", width, 0.5, name="Half Width")[0], name="Left")[0]
        low = g.math("SUBTRACT", cy, g.math("MULTIPLY", height, 0.5, name="Half Height")[0], name="Bottom")[0]
        u = g.math("DIVIDE", g.math("SUBTRACT", pos["X"], left, name="X - Left")[0], width, name="Plate U")[0]
        v = g.math("DIVIDE", g.math("SUBTRACT", pos["Y"], low, name="Y - Bottom")[0], height, name="Plate V")[0]
        body = g.store(
            body,
            "UVMap",
            g.combine_xyz(u, v, 0.0, name="Plate UV")[0],
            domain="CORNER",
            data_type="FLOAT2",
            name="Store UVMap",
        )[0]
        mat = g.fallback("MATERIAL", gi["Plate Material"], materials.ensure("ET Plate"), name="Plate Material")
        body = g.node("GeometryNodeSetMaterial", "Set Plate Material", inputs={"Geometry": body, "Material": mat})[0]
        body = g.node(
            "GeometryNodeSetShadeSmooth",
            "Smooth Plate",
            inputs={"Geometry": body, "Shade Smooth": True},
            props={"domain": "FACE"},
        )[0]

    # ------------------------------------------------------------------ join with the text
    with g.frame("Join"):
        gi = g.inputs("Mesh", "Plate", label="Join")
        joined = g.node("GeometryNodeJoinGeometry", "Text + Plate", inputs={"Geometry": [gi["Mesh"], body]})[0]
        result = g.switch("GEOMETRY", gi["Plate"], gi["Mesh"], joined, name="Plate?")[0]
    g.set_output("Mesh", result)
    return g.finish()
