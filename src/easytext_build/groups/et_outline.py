"""Outline cleanup: resolution, polyline, drop collinear and duplicate points, store outline parameters."""

from ..core import GroupBuilder

NAME = ".ET Outline Clean"


def build():
    g = GroupBuilder(
        NAME, description="Glyph outlines as clean polylines with contour length (et_u) and loop length (et_loop_len)."
    )
    g.input("Curves", "geometry")
    g.input("Resolution", "int", 12, min=1, max=64, description="Points per curve segment.")
    g.input(
        "Simplify",
        "float",
        0.5,
        min=0.0,
        max=10.0,
        description="Remove points whose direction changes less than this angle (degrees). 0 = off.",
    )
    g.output("Curves", "geometry")

    with g.frame("Resolution"):
        gi = g.inputs("Curves", "Resolution")
        with_res = g.node(
            "GeometryNodeSetSplineResolution",
            "Set Resolution",
            inputs={"Geometry": gi["Curves"], "Resolution": gi["Resolution"]},
        )[0]
        poly = g.node("GeometryNodeResampleCurve", "To Polyline", inputs={"Curve": with_res, "Mode": "Evaluated"})[0]

    with g.frame("Simplify"):
        gi = g.inputs("Simplify")
        index = g.node("GeometryNodeInputIndex", "Index")[0]
        position = g.node("GeometryNodeInputPosition", "Position")[0]
        prev_pt = g.node(
            "GeometryNodeOffsetPointInCurve", "Previous Point", inputs={"Point Index": index, "Offset": -1}
        )
        next_pt = g.node("GeometryNodeOffsetPointInCurve", "Next Point", inputs={"Point Index": index, "Offset": 1})
        p_prev = g.sample_index(
            poly, position, prev_pt["Point Index"], data_type="FLOAT_VECTOR", name="Previous Position"
        )[0]
        p_next = g.sample_index(poly, position, next_pt["Point Index"], data_type="FLOAT_VECTOR", name="Next Position")[
            0
        ]
        d_in = g.vmath("SUBTRACT", position, p_prev, name="Direction In")[0]
        d_out = g.vmath("SUBTRACT", p_next, position, name="Direction Out")[0]
        dot = g.vmath(
            "DOT_PRODUCT",
            g.vmath("NORMALIZE", d_in, name="Normalize In")[0],
            g.vmath("NORMALIZE", d_out, name="Normalize Out")[0],
            name="Dot",
        )["Value"]
        dot_c = g.math("MINIMUM", g.math("MAXIMUM", dot, -1.0, name="Clamp Low")[0], 1.0, name="Clamp High")[0]
        angle_deg = g.math("DEGREES", g.math("ARCCOSINE", dot_c, name="Arccos")[0], name="Turn Angle")[0]
        is_straight = g.compare("LESS_THAN", angle_deg, gi["Simplify"], name="Is Straight")[0]
        is_dup = g.compare(
            "LESS_THAN", g.vmath("LENGTH", d_in, name="Edge Length")["Value"], 0.000001, name="Is Duplicate"
        )[0]
        valid = g.boolean("AND", prev_pt["Is Valid Offset"], next_pt["Is Valid Offset"], name="Has Neighbours")[0]
        remove = g.boolean(
            "AND", g.boolean("OR", is_straight, is_dup, name="Straight or Duplicate")[0], valid, name="Remove Point"
        )[0]
        clean = g.node(
            "GeometryNodeDeleteGeometry",
            "Delete Points",
            inputs={"Geometry": poly, "Selection": remove},
            props={"domain": "POINT"},
        )[0]

    with g.frame("Outline Parameters"):
        spline_param = g.node("GeometryNodeSplineParameter", "Spline Parameter")
        spline_len = g.node("GeometryNodeSplineLength", "Spline Length")
        outline = g.store(clean, "et_u", spline_param["Length"], name="Store et_u")[0]
        outline = g.store(outline, "et_loop_len", spline_len["Length"], name="Store et_loop_len")[0]
    g.set_output("Curves", outline)
    return g.finish()
