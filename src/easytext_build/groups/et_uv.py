"""UVMap: planar caps, sides and bevel as one continuous band (U = contour length, V = arc length)."""

import math

from ..core import GroupBuilder
from .et_solid import FACE_BACK, FACE_FRONT

NAME = ".ET Text UV"


def build():
    g = GroupBuilder(NAME, description="Writes the UV map 'UVMap' on face corners.")
    g.input("Mesh", "geometry")
    g.input("UV", "bool", True, description="Off: the mesh passes through unchanged.")
    g.input("Depth", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE")
    g.input("Radius", "float", 0.0, min=0.0, max=1.0, subtype="DISTANCE", description="Effective bevel radius.")
    g.input("Normalize to Text", "bool", True)
    g.input("Scale", "float", 1.0, min=0.0001, max=1000.0)
    g.output("Mesh", "geometry")

    with g.frame("Scale"):
        gi = g.inputs("Mesh", "Normalize to Text", "Scale")
        bbox = g.node("GeometryNodeBoundBox", "Text Bounds", inputs={"Geometry": gi["Mesh"]})
        bmin = g.separate_xyz(bbox["Min"], name="Bounds Min")
        bmax = g.separate_xyz(bbox["Max"], name="Bounds Max")
        extent = g.math(
            "MAXIMUM",
            g.math("SUBTRACT", bmax["X"], bmin["X"], name="Width")[0],
            g.math("SUBTRACT", bmax["Y"], bmin["Y"], name="Height")[0],
            name="Extent",
        )[0]
        norm_scale = g.math(
            "DIVIDE", 1.0, g.math("MAXIMUM", extent, 0.000001, name="Extent Safe")[0], name="1 / Extent"
        )[0]
        uv_factor = g.math(
            "MULTIPLY",
            g.switch("FLOAT", gi["Normalize to Text"], 1.0, norm_scale, name="Normalize")[0],
            gi["Scale"],
            name="UV Factor",
        )[0]

    with g.frame("Caps"):
        pos_xyz = g.separate_xyz(g.node("GeometryNodeInputPosition", "Position")[0], name="Position XYZ")
        cap_uv = g.combine_xyz(
            g.math("MULTIPLY", g.math("SUBTRACT", pos_xyz["X"], bmin["X"], name="X - Min")[0], uv_factor, name="Cap U")[
                0
            ],
            g.math("MULTIPLY", g.math("SUBTRACT", pos_xyz["Y"], bmin["Y"], name="Y - Min")[0], uv_factor, name="Cap V")[
                0
            ],
            0.0,
            name="Cap UV",
        )[0]

    with g.frame("Band V"):
        gi = g.inputs("Depth", "Radius")
        z = pos_xyz["Z"]
        r, depth = gi["Radius"], gi["Depth"]
        r_safe = g.math("MAXIMUM", r, 0.000001, name="Radius Safe")[0]
        quarter = g.math("MULTIPLY", r, math.pi / 2, name="Quarter Arc")[0]
        back_ratio = g.math("DIVIDE", g.math("SUBTRACT", r, z, name="r - z")[0], r_safe, name="Back Ratio")[0]
        back_clamped = g.math("MINIMUM", g.math("MAXIMUM", back_ratio, 0.0, name="Back ≥ 0")[0], 1.0, name="Back ≤ 1")[
            0
        ]
        back_t = g.math("ARCSINE", back_clamped, name="Back Angle")[0]
        v_back = g.math(
            "MULTIPLY", r, g.math("SUBTRACT", math.pi / 2, back_t, name="90° - Back")[0], name="V Back Bevel"
        )[0]
        v_side = g.math("ADD", quarter, g.math("SUBTRACT", z, r, name="z - r")[0], name="V Side")[0]
        front_start = g.math("SUBTRACT", depth, r, name="Depth - r")[0]
        front_ratio = g.math(
            "DIVIDE", g.math("SUBTRACT", z, front_start, name="z - (Depth - r)")[0], r_safe, name="Front Ratio"
        )[0]
        front_clamped = g.math(
            "MINIMUM", g.math("MAXIMUM", front_ratio, 0.0, name="Front ≥ 0")[0], 1.0, name="Front ≤ 1"
        )[0]
        front_t = g.math("ARCSINE", front_clamped, name="Front Angle")[0]
        side_len = g.math("SUBTRACT", depth, g.math("MULTIPLY", r, 2.0, name="2r")[0], name="Depth - 2r")[0]
        v_front = g.math(
            "ADD",
            g.math("ADD", quarter, side_len, name="Quarter + Side")[0],
            g.math("MULTIPLY", r, front_t, name="Front Arc")[0],
            name="V Front Bevel",
        )[0]
        in_back = g.compare("LESS_THAN", z, r, name="In Back Bevel")[0]
        in_front = g.compare("GREATER_THAN", z, front_start, name="In Front Bevel")[0]
        v = g.switch(
            "FLOAT",
            in_front,
            g.switch("FLOAT", in_back, v_side, v_back, name="Back or Side")[0],
            v_front,
            name="Band V",
        )[0]

    with g.frame("Band U (Seam)"):
        gi = g.inputs("Mesh")
        u = g.named("et_u", name="U")["Attribute"]
        loop_len = g.named("et_loop_len", name="Loop Length")["Attribute"]
        index = g.node("GeometryNodeInputIndex", "Corner Index")[0]
        corner_face = g.node("GeometryNodeFaceOfCorner", "Face of Corner", inputs={"Corner Index": index})["Face Index"]
        corner_us = []
        for k in range(4):
            ck = g.node(
                "GeometryNodeCornersOfFace", f"Corner {k}", inputs={"Face Index": corner_face, "Sort Index": k}
            )["Corner Index"]
            corner_us.append(g.sample_index(gi["Mesh"], u, ck, domain="CORNER", name=f"U of Corner {k}")[0])
        u_min, u_max = corner_us[0], corner_us[0]
        for i, cu in enumerate(corner_us[1:], start=1):
            u_min = g.math("MINIMUM", u_min, cu, name=f"Min {i}")[0]
            u_max = g.math("MAXIMUM", u_max, cu, name=f"Max {i}")[0]
        half = g.math("MULTIPLY", loop_len, 0.5, name="Half Loop")[0]
        wraps = g.compare(
            "GREATER_THAN", g.math("SUBTRACT", u_max, u_min, name="Face U Span")[0], half, name="Face Wraps"
        )[0]
        low_side = g.compare("LESS_THAN", u, half, name="Low Side")[0]
        shift = g.boolean("AND", wraps, low_side, name="Shift Corner")[0]
        u_fixed = g.switch("FLOAT", shift, u, g.math("ADD", u, loop_len, name="U + Loop")[0], name="U Unwrapped")[0]

    with g.frame("Store UV"):
        gi = g.inputs("Mesh")
        band_uv = g.combine_xyz(
            g.math("MULTIPLY", u_fixed, uv_factor, name="Band U Scaled")[0],
            g.math("MULTIPLY", v, uv_factor, name="Band V Scaled")[0],
            0.0,
            name="Band UV",
        )[0]
        face_group = g.named("et_face_group", "INT", name="Face Group")["Attribute"]
        is_front = g.compare("EQUAL", face_group, FACE_FRONT, data_type="INT", name="Is Front")[0]
        is_back = g.compare("EQUAL", face_group, FACE_BACK, data_type="INT", name="Is Back")[0]
        is_cap = g.boolean("OR", is_front, is_back, name="Is Cap")[0]
        uv = g.switch("VECTOR", is_cap, band_uv, cap_uv, name="UV")[0]
        with_uv = g.store(gi["Mesh"], "UVMap", uv, domain="CORNER", data_type="FLOAT2", name="Store UVMap")[0]

    with g.frame("Bypass"):
        gi = g.inputs("UV", "Mesh", label="Bypass")
        result = g.switch("GEOMETRY", gi["UV"], gi["Mesh"], with_uv, name="Use UV")[0]
    g.set_output("Mesh", result)
    return g.finish()
