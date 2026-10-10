"""ET Text Mesh: Text -> sauberes, exportfähiges Mesh mit UVs (Kern von Easy Text v3, ohne Animation).

Pipeline: Zeilen joinen -> String to Curves -> Kontur bereinigen -> Fill -> Rückseite + Extrusion ->
Mesh Bevel (optional) -> UVs (Deckflächen planar, Seiten/Bevel über Konturlänge) -> Materialien -> Shading.
"""

import math

from .. import catalog, materials
from ..core import GroupBuilder, builtin_font
from . import et_lines_join

NAME = "ET Text Mesh"
FACE_SIDE, FACE_FRONT, FACE_BACK, FACE_BEVEL = 0, 1, 2, 3


def build():
    mats = materials.ensure_all()
    g = GroupBuilder(
        NAME,
        description="Text als sauberes Mesh mit Extrusion, Bevel, Materialien und exportfähigen UVs.",
        is_modifier=True,
        catalog=catalog.TEXT,
        color_tag="GEOMETRY",
        default_width=220,
    )

    # ------------------------------------------------------------------ Interface
    with g.panel("Text", description="Bis zu vier Zeilen; leere Zeilen werden übersprungen."):
        lines = [g.input("Text", "string", "Easy Text", description="Erste Zeile.")]
        lines += [g.input(f"Zeile {i}", "string", "", description=f"Zeile {i}, optional.") for i in (2, 3, 4)]
    with g.panel("Typografie"):
        font = g.input("Font", "font", builtin_font(), description="Schriftart (Font-Datablock).")
        size = g.input("Größe", "float", 1.0, min=0.001, max=100.0, subtype="DISTANCE", description="Schriftgröße.")
        align_x = g.input("Ausrichtung X", "menu", description="Horizontale Ausrichtung der Zeilen.")
        align_y = g.input("Ausrichtung Y", "menu", description="Vertikale Ausrichtung des Textblocks.")
        pivot = g.input("Pivot", "menu", description="Ursprung des Textblocks.")
        char_sp = g.input(
            "Zeichenabstand", "float", 1.0, min=0.0, max=10.0, description="Faktor für den Abstand der Zeichen."
        )
        word_sp = g.input(
            "Wortabstand", "float", 1.0, min=0.0, max=10.0, description="Faktor für den Abstand der Wörter."
        )
        line_sp = g.input("Zeilenabstand", "float", 1.0, min=0.0, max=10.0, description="Faktor für den Zeilenabstand.")
        with g.panel("Textbox", description="Umbruch und Überlauf.", default_closed=True):
            box_w = g.input(
                "Breite", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = kein Umbruch."
            )
            box_h = g.input(
                "Höhe", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = unbegrenzt."
            )
            overflow = g.input("Überlauf", "menu", description="Verhalten, wenn der Text nicht in die Box passt.")
    with g.panel("Kontur", description="Qualität der Buchstabenkonturen."):
        resolution = g.input("Auflösung", "int", 12, min=1, max=64, description="Punkte pro Kurvensegment.")
        simplify = g.input(
            "Vereinfachen",
            "float",
            0.5,
            min=0.0,
            max=10.0,
            description="Punkte entfernen, deren Richtungsänderung unter diesem Winkel (Grad) liegt. 0 = aus.",
        )
        fill_mode = g.input("Füllung", "menu", description="N-Gons oder Dreiecke auf den Deckflächen.")
        fill_rule = g.input("Füllregel", "menu", description="Even-Odd oder Non-Zero für überlappende Konturen.")
    with g.panel("Form"):
        depth = g.input("Tiefe", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE", description="Extrusionstiefe.")
        with g.panel("Bevel", description="Kantenrundung an Vorder- und Rückseite."):
            bevel_on = g.input("Bevel", "bool", False, panel_toggle=True)
            bevel_w = g.input(
                "Breite",
                "float",
                0.01,
                min=0.0,
                max=1.0,
                subtype="DISTANCE",
                description="Bevel-Breite, maximal halbe Tiefe.",
            )
            bevel_seg = g.input("Segmente", "int", 3, min=1, max=16, description="Unterteilungen des Bevels.")
            bevel_shape = g.input("Profil", "float", 0.5, min=0.0, max=1.0, subtype="FACTOR", description="0.5 = rund.")
        smooth_angle = g.input(
            "Glättungswinkel",
            "float",
            30.0,
            min=0.0,
            max=180.0,
            description="Kanten über diesem Winkel (Grad) bleiben hart.",
        )
    with g.panel("Material"):
        mat_front = g.input("Vorderseite", "material", mats["ET Front"], description="Auch für die Rückseite.")
        mat_side = g.input("Seite", "material", mats["ET Side"])
        mat_bevel = g.input("Bevelfläche", "material", mats["ET Bevel"])
    with g.panel("UV", description="UV-Map 'UVMap': Deckflächen planar, Seiten und Bevel entlang der Kontur."):
        uv_on = g.input("UV", "bool", True, panel_toggle=True)
        uv_normalize = g.input(
            "Auf Text normieren",
            "bool",
            True,
            description="Deckflächen in 0..1 skalieren; aus = Blender-Einheiten (kachelbar).",
        )
        uv_scale = g.input("Maßstab", "float", 1.0, min=0.0001, max=1000.0, description="Zusätzlicher UV-Faktor.")
    with g.panel("Ausgabe", default_closed=True):
        keep_attrs = g.input(
            "Hilfsattribute behalten",
            "bool",
            False,
            description="et_*-Attribute (Zeichenindex, Konturlänge, Flächengruppe) am Mesh lassen.",
        )
    g.output("Geometry", "geometry")
    for name, value in (
        ("Ausrichtung X", "Center"),
        ("Ausrichtung Y", "Middle"),
        ("Pivot", "Midpoint"),
        ("Überlauf", "Overflow"),
        ("Füllung", "N-gons"),
        ("Füllregel", "Even-Odd"),
    ):
        g.menu_default(name, value)

    # ------------------------------------------------------------------ 1. Text -> Kurven-Instanzen
    joined = g.group(et_lines_join.NAME, "Lines", inputs={f"Line {i}": line for i, line in enumerate(lines, start=1)})[
        "String"
    ]
    text_len = g.node("FunctionNodeStringLength", "Text Length", inputs={"String": joined})["Length"]
    curves_inst = g.node(
        "GeometryNodeStringToCurves",
        "String to Curves",
        inputs={
            "String": joined,
            "Size": size,
            "Font": font,
            "Align X": align_x,
            "Align Y": align_y,
            "Pivot Point": pivot,
            "Character Spacing": char_sp,
            "Word Spacing": word_sp,
            "Line Spacing": line_sp,
            "Overflow": overflow,
            "Text Box Width": box_w,
            "Text Box Height": box_h,
        },
    )
    index = g.node("GeometryNodeInputIndex", "Index")[0]
    with_char = g.store(
        curves_inst["Curve Instances"],
        "et_char_index",
        index,
        domain="INSTANCE",
        data_type="INT",
        name="Store Char Index",
    )
    curves = g.node("GeometryNodeRealizeInstances", "Realize Glyphs", inputs={"Geometry": with_char[0]})[0]

    # ------------------------------------------------------------------ 2. Kontur bereinigen
    with_res = g.node(
        "GeometryNodeSetSplineResolution", "Set Resolution", inputs={"Geometry": curves, "Resolution": resolution}
    )[0]
    poly = g.node("GeometryNodeResampleCurve", "To Polyline", inputs={"Curve": with_res, "Mode": "Evaluated"})[0]
    position = g.node("GeometryNodeInputPosition", "Position")[0]
    prev_pt = g.node("GeometryNodeOffsetPointInCurve", "Prev Point", inputs={"Point Index": index, "Offset": -1})
    next_pt = g.node("GeometryNodeOffsetPointInCurve", "Next Point", inputs={"Point Index": index, "Offset": 1})
    p_prev = g.sample_index(poly, position, prev_pt["Point Index"], data_type="FLOAT_VECTOR", name="Prev Position")[0]
    p_next = g.sample_index(poly, position, next_pt["Point Index"], data_type="FLOAT_VECTOR", name="Next Position")[0]
    d_in = g.vmath("SUBTRACT", position, p_prev, name="Dir In")[0]
    d_out = g.vmath("SUBTRACT", p_next, position, name="Dir Out")[0]
    dot = g.vmath("DOT_PRODUCT", g.vmath("NORMALIZE", d_in)[0], g.vmath("NORMALIZE", d_out)[0], name="Dot")["Value"]
    dot_c = g.math("MINIMUM", g.math("MAXIMUM", dot, -1.0)[0], 1.0)[0]
    angle_deg = g.math("DEGREES", g.math("ARCCOSINE", dot_c)[0], name="Turn Angle")[0]
    is_straight = g.compare("LESS_THAN", angle_deg, simplify, name="Is Straight")[0]
    is_dup = g.compare("LESS_THAN", g.vmath("LENGTH", d_in)["Value"], 0.000001, name="Is Duplicate")[0]
    valid = g.boolean("AND", prev_pt["Is Valid Offset"], next_pt["Is Valid Offset"])[0]
    remove = g.boolean("AND", g.boolean("OR", is_straight, is_dup)[0], valid, name="Remove Point")[0]
    clean = g.node(
        "GeometryNodeDeleteGeometry",
        "Simplify Outline",
        inputs={"Geometry": poly, "Selection": remove},
        props={"domain": "POINT"},
    )[0]

    # Konturparameter pro Punkt (für Seiten-UVs)
    spline_param = g.node("GeometryNodeSplineParameter", "Spline Parameter")
    spline_len = g.node("GeometryNodeSplineLength", "Spline Length")
    outline = g.store(clean, "et_u", spline_param["Length"], name="Store U")[0]
    outline = g.store(outline, "et_loop_len", spline_len["Length"], name="Store Loop Length")[0]

    # ------------------------------------------------------------------ 3. Fill + Attribut-Transport
    fill = g.node(
        "GeometryNodeFillCurve", "Fill", inputs={"Curve": outline, "Mode": fill_mode, "Fill Rule": fill_rule}
    )["Mesh"]
    normal_z = g.separate_xyz(g.node("GeometryNodeInputNormal", "Normal")["Normal"], name="Normal XYZ")["Z"]
    fill_up = g.node(
        "GeometryNodeFlipFaces", "Face +Z", inputs={"Mesh": fill, "Selection": g.compare("LESS_THAN", normal_z, 0.0)[0]}
    )[0]
    fill_up = g.node("GeometryNodeSetMaterial", "Material Front", inputs={"Geometry": fill_up, "Material": mat_front})[
        0
    ]
    points = g.node(
        "GeometryNodeCurveToPoints", "Outline Points", inputs={"Curve": outline}, props={"mode": "EVALUATED"}
    )["Points"]
    nearest = g.node(
        "GeometryNodeSampleNearest",
        "Nearest Outline Point",
        inputs={"Geometry": points, "Sample Position": position},
        props={"domain": "POINT"},
    )["Index"]

    def transport(geometry, attr, data_type):
        value = g.sample_index(
            points, g.named(attr, data_type)["Attribute"], nearest, data_type=data_type, name=f"Fetch {attr}"
        )[0]
        return g.store(geometry, attr, value, data_type=data_type, name=f"Store {attr}")[0]

    cap = transport(fill_up, "et_u", "FLOAT")
    cap = transport(cap, "et_loop_len", "FLOAT")
    cap = transport(cap, "et_char_index", "INT")

    # ------------------------------------------------------------------ 4. Volumenkörper
    back = g.store(cap, "et_face_group", FACE_BACK, domain="FACE", data_type="INT", name="Group Back")[0]
    back_flipped = g.node("GeometryNodeFlipFaces", "Flip Back", inputs={"Mesh": back})[0]
    extrude = g.node(
        "GeometryNodeExtrudeMesh",
        "Extrude",
        inputs={"Mesh": back, "Offset Scale": depth, "Individual": False},
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
        front, "et_face_group", FACE_SIDE, domain="FACE", data_type="INT", selection=extrude["Side"], name="Group Side"
    )[0]
    solid = g.node("GeometryNodeJoinGeometry", "Join Solid", inputs={"Geometry": [sides, back_flipped]})[0]
    solid = g.node("GeometryNodeMergeByDistance", "Close Solid", inputs={"Geometry": solid, "Distance": 0.00001})[0]

    # ------------------------------------------------------------------ 5. Bevel
    r_max = g.math("SUBTRACT", g.math("MULTIPLY", depth, 0.5)[0], 0.0001, name="Max Bevel")[0]
    r_clamped = g.math("MAXIMUM", g.math("MINIMUM", bevel_w, r_max)[0], 0.0, name="Bevel Width Clamped")[0]
    r = g.switch("FLOAT", bevel_on, 0.0, r_clamped, name="Bevel Radius")[0]
    face_group = g.named("et_face_group", "INT", name="Face Group")["Attribute"]
    boundary = g.node("GeometryNodeMeshFaceSetBoundaries", "Cap Edges", inputs={"Face Set": face_group})[
        "Boundary Edges"
    ]
    bevel = g.node(
        "GeometryNodeMeshBevel",
        "Bevel",
        # Die vier Enden-Offsets haben Default 0.1 und überstimmen "Offset"; alle auf den Radius setzen.
        inputs={
            "Mesh": solid,
            "Selection": boundary,
            "Offset": r_clamped,
            "Segments": bevel_seg,
            "Shape": bevel_shape,
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
    body = g.switch("GEOMETRY", bevel_on, solid, ring, name="Use Bevel")[0]

    # ------------------------------------------------------------------ 6. UVs
    bbox = g.node("GeometryNodeBoundBox", "Text Bounds", inputs={"Geometry": solid})
    bmin = g.separate_xyz(bbox["Min"], name="Bounds Min")
    bmax = g.separate_xyz(bbox["Max"], name="Bounds Max")
    extent = g.math(
        "MAXIMUM",
        g.math("SUBTRACT", bmax["X"], bmin["X"])[0],
        g.math("SUBTRACT", bmax["Y"], bmin["Y"])[0],
        name="Text Extent",
    )[0]
    norm_scale = g.math("DIVIDE", 1.0, g.math("MAXIMUM", extent, 0.000001)[0])[0]
    uv_factor = g.math("MULTIPLY", g.switch("FLOAT", uv_normalize, 1.0, norm_scale)[0], uv_scale, name="UV Factor")[0]

    pos_xyz = g.separate_xyz(position, name="Position XYZ")
    cap_uv = g.combine_xyz(
        g.math("MULTIPLY", g.math("SUBTRACT", pos_xyz["X"], bmin["X"])[0], uv_factor)[0],
        g.math("MULTIPLY", g.math("SUBTRACT", pos_xyz["Y"], bmin["Y"])[0], uv_factor)[0],
        0.0,
        name="Cap UV",
    )[0]

    # Band-V(z): Rück-Bevel -> Seite -> Front-Bevel, Bogenlänge exakt für runde Profile
    z = pos_xyz["Z"]
    r_safe = g.math("MAXIMUM", r, 0.000001)[0]
    quarter = g.math("MULTIPLY", r, math.pi / 2, name="Quarter Arc")[0]
    back_t = g.math(
        "ARCSINE",
        g.math("MINIMUM", g.math("MAXIMUM", g.math("DIVIDE", g.math("SUBTRACT", r, z)[0], r_safe)[0], 0.0)[0], 1.0)[0],
    )[0]
    v_back = g.math("MULTIPLY", r, g.math("SUBTRACT", math.pi / 2, back_t)[0], name="V Back Bevel")[0]
    v_side = g.math("ADD", quarter, g.math("SUBTRACT", z, r)[0], name="V Side")[0]
    front_t = g.math(
        "ARCSINE",
        g.math(
            "MINIMUM",
            g.math(
                "MAXIMUM", g.math("DIVIDE", g.math("SUBTRACT", z, g.math("SUBTRACT", depth, r)[0])[0], r_safe)[0], 0.0
            )[0],
            1.0,
        )[0],
    )[0]
    v_front = g.math(
        "ADD",
        g.math("ADD", quarter, g.math("SUBTRACT", depth, g.math("MULTIPLY", r, 2.0)[0])[0])[0],
        g.math("MULTIPLY", r, front_t)[0],
        name="V Front Bevel",
    )[0]
    in_back = g.compare("LESS_THAN", z, r)[0]
    in_front = g.compare("GREATER_THAN", z, g.math("SUBTRACT", depth, r)[0])[0]
    v = g.switch("FLOAT", in_front, g.switch("FLOAT", in_back, v_side, v_back)[0], v_front, name="Band V")[0]

    # U entlang der Kontur, Nahtquad am Konturende aufgeklappt
    u = g.named("et_u", name="U")["Attribute"]
    loop_len = g.named("et_loop_len", name="Loop Length")["Attribute"]
    corner_face = g.node("GeometryNodeFaceOfCorner", "Face of Corner", inputs={"Corner Index": index})["Face Index"]
    corner_us = []
    for k in range(4):
        ck = g.node("GeometryNodeCornersOfFace", f"Corner {k}", inputs={"Face Index": corner_face, "Sort Index": k})[
            "Corner Index"
        ]
        corner_us.append(g.sample_index(body, u, ck, domain="CORNER", name=f"U of Corner {k}")[0])
    u_min = corner_us[0]
    u_max = corner_us[0]
    for cu in corner_us[1:]:
        u_min = g.math("MINIMUM", u_min, cu)[0]
        u_max = g.math("MAXIMUM", u_max, cu)[0]
    half = g.math("MULTIPLY", loop_len, 0.5)[0]
    wraps = g.compare("GREATER_THAN", g.math("SUBTRACT", u_max, u_min)[0], half, name="Face Wraps")[0]
    low_side = g.compare("LESS_THAN", u, half)[0]
    u_fixed = g.switch(
        "FLOAT", g.boolean("AND", wraps, low_side)[0], u, g.math("ADD", u, loop_len)[0], name="U Unwrapped"
    )[0]
    band_uv = g.combine_xyz(
        g.math("MULTIPLY", u_fixed, uv_factor)[0], g.math("MULTIPLY", v, uv_factor)[0], 0.0, name="Band UV"
    )[0]

    is_front = g.compare("EQUAL", face_group, FACE_FRONT, data_type="INT")[0]
    is_back = g.compare("EQUAL", face_group, FACE_BACK, data_type="INT")[0]
    is_cap = g.boolean("OR", is_front, is_back, name="Is Cap")[0]
    uv = g.switch("VECTOR", is_cap, band_uv, cap_uv, name="UV")[0]
    with_uv = g.store(body, "UVMap", uv, domain="CORNER", data_type="FLOAT2", name="Store UVMap")[0]
    mesh = g.switch("GEOMETRY", uv_on, body, with_uv, name="Use UV")[0]

    # ------------------------------------------------------------------ 7. Materialien und Shading
    is_side = g.compare("EQUAL", face_group, FACE_SIDE, data_type="INT")[0]
    mesh = g.node(
        "GeometryNodeSetMaterial",
        "Material Side",
        inputs={"Geometry": mesh, "Selection": is_side, "Material": mat_side},
    )[0]
    is_bevel = g.compare("EQUAL", face_group, FACE_BEVEL, data_type="INT")[0]
    mesh = g.node(
        "GeometryNodeSetMaterial",
        "Material Bevel",
        inputs={"Geometry": mesh, "Selection": is_bevel, "Material": mat_bevel},
    )[0]
    mesh = g.node(
        "GeometryNodeSetShadeSmooth",
        "Smooth Faces",
        inputs={"Geometry": mesh, "Shade Smooth": True},
        props={"domain": "FACE"},
    )[0]
    edge_angle = g.node("GeometryNodeInputMeshEdgeAngle", "Edge Angle")["Unsigned Angle"]
    is_sharp = g.compare("GREATER_THAN", edge_angle, g.math("RADIANS", smooth_angle)[0], name="Is Sharp")[0]
    mesh = g.node(
        "GeometryNodeSetShadeSmooth",
        "Sharp Edges",
        inputs={"Geometry": mesh, "Shade Smooth": g.boolean("NOT", is_sharp)[0]},
        props={"domain": "EDGE"},
    )[0]

    # ------------------------------------------------------------------ 8. Aufräumen und Warnungen
    stripped = g.node(
        "GeometryNodeRemoveAttribute",
        "Remove Helpers",
        inputs={"Geometry": mesh, "Pattern Mode": "Wildcard", "Name": "et_*"},
    )[0]
    final = g.switch("GEOMETRY", keep_attrs, stripped, mesh, name="Keep Attributes")[0]
    warn_empty = g.node(
        "GeometryNodeWarning",
        "Warn Empty",
        inputs={"Show": g.compare("EQUAL", text_len, 0, data_type="INT")[0], "Message": "Kein Text."},
        props={"warning_type": "WARNING"},
    )["Show"]
    too_wide = g.boolean("AND", bevel_on, g.compare("GREATER_THAN", bevel_w, r_max)[0])[0]
    warn_bevel = g.node(
        "GeometryNodeWarning",
        "Warn Bevel",
        inputs={"Show": too_wide, "Message": "Bevel-Breite auf halbe Tiefe begrenzt."},
        props={"warning_type": "INFO"},
    )["Show"]
    hook = g.boolean("OR", warn_empty, warn_bevel)[0]
    g.set_output("Geometry", g.switch("GEOMETRY", hook, final, final, name="Output")[0])
    return g.finish()
