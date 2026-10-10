"""Kontur bereinigen: Auflösung, Polylinie, kollineare und doppelte Punkte löschen, Konturparameter speichern."""

from ..core import GroupBuilder

NAME = ".ET Outline Clean"


def build():
    g = GroupBuilder(
        NAME,
        description="Glyphenkonturen als saubere Polylinien mit Konturlänge (et_u) und Schleifenlänge (et_loop_len).",
    )
    g.input("Curves", "geometry")
    g.input("Auflösung", "int", 12, min=1, max=64, description="Punkte pro Kurvensegment.")
    g.input(
        "Vereinfachen",
        "float",
        0.5,
        min=0.0,
        max=10.0,
        description="Punkte unter diesem Richtungswinkel (Grad) entfernen. 0 = aus.",
    )
    g.output("Curves", "geometry")

    with g.frame("Auflösen"):
        gi = g.inputs("Curves", "Auflösung")
        with_res = g.node(
            "GeometryNodeSetSplineResolution",
            "Set Resolution",
            inputs={"Geometry": gi["Curves"], "Resolution": gi["Auflösung"]},
        )[0]
        poly = g.node("GeometryNodeResampleCurve", "To Polyline", inputs={"Curve": with_res, "Mode": "Evaluated"})[0]

    with g.frame("Vereinfachen"):
        gi = g.inputs("Vereinfachen")
        index = g.node("GeometryNodeInputIndex", "Index")[0]
        position = g.node("GeometryNodeInputPosition", "Position")[0]
        prev_pt = g.node("GeometryNodeOffsetPointInCurve", "Prev Point", inputs={"Point Index": index, "Offset": -1})
        next_pt = g.node("GeometryNodeOffsetPointInCurve", "Next Point", inputs={"Point Index": index, "Offset": 1})
        p_prev = g.sample_index(poly, position, prev_pt["Point Index"], data_type="FLOAT_VECTOR", name="Prev Position")[
            0
        ]
        p_next = g.sample_index(poly, position, next_pt["Point Index"], data_type="FLOAT_VECTOR", name="Next Position")[
            0
        ]
        d_in = g.vmath("SUBTRACT", position, p_prev, name="Dir In")[0]
        d_out = g.vmath("SUBTRACT", p_next, position, name="Dir Out")[0]
        dot = g.vmath(
            "DOT_PRODUCT",
            g.vmath("NORMALIZE", d_in, name="Norm In")[0],
            g.vmath("NORMALIZE", d_out, name="Norm Out")[0],
            name="Dot",
        )["Value"]
        dot_c = g.math("MINIMUM", g.math("MAXIMUM", dot, -1.0, name="Clamp Lo")[0], 1.0, name="Clamp Hi")[0]
        angle_deg = g.math("DEGREES", g.math("ARCCOSINE", dot_c, name="Arccos")[0], name="Turn Angle")[0]
        is_straight = g.compare("LESS_THAN", angle_deg, gi["Vereinfachen"], name="Is Straight")[0]
        is_dup = g.compare(
            "LESS_THAN", g.vmath("LENGTH", d_in, name="Edge Length")["Value"], 0.000001, name="Is Duplicate"
        )[0]
        valid = g.boolean("AND", prev_pt["Is Valid Offset"], next_pt["Is Valid Offset"], name="Has Neighbours")[0]
        remove = g.boolean(
            "AND", g.boolean("OR", is_straight, is_dup, name="Straight or Dup")[0], valid, name="Remove Point"
        )[0]
        clean = g.node(
            "GeometryNodeDeleteGeometry",
            "Delete Points",
            inputs={"Geometry": poly, "Selection": remove},
            props={"domain": "POINT"},
        )[0]

    with g.frame("Konturparameter"):
        spline_param = g.node("GeometryNodeSplineParameter", "Spline Parameter")
        spline_len = g.node("GeometryNodeSplineLength", "Spline Length")
        outline = g.store(clean, "et_u", spline_param["Length"], name="Store et_u")[0]
        outline = g.store(outline, "et_loop_len", spline_len["Length"], name="Store et_loop_len")[0]
    g.set_output("Curves", outline)
    return g.finish()
