"""Animation ("Animation" on the control panel): per-letter, per-word or per-line animation of the finished mesh.

Every element gets its own local time from Start, Duration, Stagger and Order; an easing turns it into a weight
and the element travels from its start state (Offset, Rotation, Scale) into place (direction In) or away (Out).
Bounce adds a continuous wobble. The stage is the last one, so it also removes the et_* helper attributes.

Works on the mesh with the attributes from .ET Text Source: et_char_index, et_word_index, et_line_index and
et_pivot (the typographic pivot of each glyph), carried through .ET Solid."""

import math

from ..core import GroupBuilder, heading, subheading

NAME = ".ET Animation"
ANIMATION_INPUTS = (
    "Animate",
    "Start",
    "Duration",
    "Stagger",
    "Order",
    "Basis",
    "Easing",
    "Loop",
    "Direction",
    "Seed",
    "Offset",
    "Rotation",
    "Center",
    "Scale",
    "Hide Before Start",
    "Bounce",
    "Bounce Strength",
    "Bounce Speed",
    "Bounce Phase",
)
MENU_DEFAULTS = (
    ("Order", "Left to Right"),
    ("Basis", "Letters"),
    ("Easing", "Ease Out"),
    ("Loop", "Once"),
    ("Direction", "In"),
    ("Center", "Letter"),
)


def declare_inputs(g: GroupBuilder, *, decorated: bool) -> None:
    """The animation inputs as panels; shared by this group (decorated headings) and ET Text Mesh (plain)."""
    h = heading if decorated else (lambda name: name)
    sub = subheading if decorated else (lambda name: name)
    with g.panel(h("Animate"), description="Per-letter animation driven by the scene frame."):
        g.input("Animate", "bool", False, panel_toggle=True)
        with g.panel(sub("Timing")):
            g.input("Start", "int", 1, min=-10000, max=100000, description="Frame at which the first element starts.")
            g.input("Duration", "int", 24, min=1, max=10000, description="Frames one element needs.")
            g.input("Stagger", "float", 2.0, min=0.0, max=1000.0, description="Frames between two elements.")
            g.input("Order", "menu", description="Which element starts first.")
            g.input("Basis", "menu", description="What counts as one element.")
            g.input("Easing", "menu", description="Speed curve of one element.")
            g.input("Loop", "menu", description="Play once, repeat, or go back and forth.")
            g.input("Direction", "menu", description="In: from the start state into place. Out: from place away.")
            g.input("Seed", "int", 0, min=0, max=10000, description="Seed for the Random order.")
        with g.panel(sub("Move")):
            g.input(
                "Offset",
                "vector",
                (0.0, -1.0, 0.0),
                subtype="TRANSLATION",
                description="Where an element starts, relative to its place.",
            )
        with g.panel(sub("Rotate")):
            g.input("Rotation", "vector", (0.0, 0.0, 0.0), subtype="EULER", description="Start rotation.")
            g.input("Center", "menu", description="Rotation and scale centre: glyph pivot, word, line or text.")
        with g.panel(sub("Scale")):
            g.input("Scale", "vector", (1.0, 1.0, 1.0), subtype="XYZ", description="Start scale.")
        with g.panel(sub("Reveal"), default_closed=True):
            g.input("Hide Before Start", "bool", False, description="Elements are invisible until they start.")
        with g.panel(sub("Bounce"), description="Continuous wobble, independent of the timing.", default_closed=True):
            g.input("Bounce", "bool", False, panel_toggle=True)
            g.input(
                "Bounce Strength",
                "vector",
                (0.0, 0.1, 0.0),
                subtype="TRANSLATION",
                description="Amplitude per axis.",
            )
            g.input("Bounce Speed", "float", 1.0, min=0.0, max=100.0, description="Cycles per second.")
            g.input("Bounce Phase", "float", 0.1, min=0.0, max=10.0, description="Cycle offset per element.")
    for name, value in MENU_DEFAULTS:
        g.menu_default(name, value)


def build():
    g = GroupBuilder(
        NAME,
        description="Per-letter animation (timing, move, rotate, scale, bounce) and cleanup of helper attributes.",
        default_width=320,
    )
    g.input("Mesh", "geometry")
    declare_inputs(g, decorated=True)
    with g.panel(heading("Output"), default_closed=True):
        g.input(
            "Keep Helper Attributes",
            "bool",
            False,
            description="Keep the et_* attributes (character, word, line index, pivot, weight) on the mesh.",
        )
    g.output("Mesh", "geometry")

    # ------------------------------------------------------------------ element index and count
    with g.frame("Elements"):
        gi = g.inputs("Mesh", "Basis", label="Elements")
        char = g.named("et_char_index", "INT", name="Letter Index")["Attribute"]
        word = g.named("et_word_index", "INT", name="Word Index")["Attribute"]
        line = g.named("et_line_index", "INT", name="Line Index")["Attribute"]
        idx = g.menu("Basis", {"Letters": char, "Words": word, "Lines": line}, type="INT", select=gi["Basis"])[0]
        count = g.node(
            "GeometryNodeAttributeStatistic",
            "Element Count",
            inputs={"Geometry": gi["Mesh"], "Attribute": idx},
            props={"data_type": "FLOAT", "domain": "POINT"},
        )["Max"]  # highest index; the count is one more

    # ------------------------------------------------------------------ local time per element
    with g.frame("Time"):
        gi = g.inputs("Start", "Duration", "Stagger", "Order", "Loop", "Seed", label="Timing")
        time = g.node("GeometryNodeInputSceneTime", "Scene Time")
        rtl = g.math("SUBTRACT", count, idx, name="Right to Left")[0]
        half = g.math("MULTIPLY", count, 0.5, name="Middle")[0]
        center = g.math("ABSOLUTE", g.math("SUBTRACT", idx, half, name="From Middle")[0], name="Center Out")[0]
        rnd = g.node(
            "FunctionNodeRandomValue",
            "Random Order",
            props={"data_type": "FLOAT"},
            inputs={"Min": 0.0, "Max": count, "ID": idx, "Seed": gi["Seed"]},
        )["Value"]
        order = g.menu(
            "Order",
            {"Left to Right": idx, "Right to Left": rtl, "Center Out": center, "Random": rnd},
            type="FLOAT",
            select=gi["Order"],
        )[0]
        delay = g.math("MULTIPLY", order, gi["Stagger"], name="Delay")[0]
        begin = g.math("ADD", gi["Start"], delay, name="Element Start")[0]
        elapsed = g.math("SUBTRACT", time["Frame"], begin, name="Elapsed")[0]
        duration = g.math("MAXIMUM", gi["Duration"], 1.0, name="Duration (min 1)")[0]
        t_raw = g.math("DIVIDE", elapsed, duration, name="Time Raw")[0]
        t_positive = g.math("MAXIMUM", t_raw, 0.0, name="Time ≥ 0")[0]
        once = g.math("MINIMUM", t_positive, 1.0, name="Once")[0]
        loop = g.math("FRACT", t_positive, name="Loop")[0]
        ping = g.math("PINGPONG", t_positive, 1.0, name="Ping-Pong")[0]
        t = g.menu("Loop", {"Once": once, "Loop": loop, "Ping-Pong": ping}, type="FLOAT", select=gi["Loop"])[0]

    # ------------------------------------------------------------------ easing -> weight of the start state
    with g.frame("Easing"):
        gi = g.inputs("Easing", "Direction", label="Easing")
        ease_in = g.math("MULTIPLY", t, t, name="Ease In")[0]
        inv = g.math("SUBTRACT", 1.0, t, name="1 - t")[0]
        ease_out = g.math("SUBTRACT", 1.0, g.math("MULTIPLY", inv, inv, name="(1 - t)²")[0], name="Ease Out")[0]
        ease_in_out = g.node(
            "ShaderNodeMapRange", "Ease In-Out", props={"interpolation_type": "SMOOTHSTEP"}, inputs={"Value": t}
        )["Result"]
        # overshoot: 1 + c3 (t-1)^3 + c1 (t-1)^2 with c1 = 1.70158, c3 = c1 + 1
        tm1 = g.math("SUBTRACT", t, 1.0, name="t - 1")[0]
        cubic = g.math("MULTIPLY", g.math("POWER", tm1, 3.0, name="(t-1)³")[0], 2.70158, name="c3 (t-1)³")[0]
        square = g.math("MULTIPLY", g.math("MULTIPLY", tm1, tm1, name="(t-1)²")[0], 1.70158, name="c1 (t-1)²")[0]
        overshoot = g.math("ADD", 1.0, g.math("ADD", cubic, square, name="back terms")[0], name="Overshoot")[0]
        eased = g.menu(
            "Easing",
            {
                "Linear": t,
                "Ease In": ease_in,
                "Ease Out": ease_out,
                "Ease In-Out": ease_in_out,
                "Overshoot": overshoot,
            },
            type="FLOAT",
            select=gi["Easing"],
        )[0]
        weight_in = g.math("SUBTRACT", 1.0, eased, name="Weight In")[0]
        weight = g.menu("Direction", {"In": weight_in, "Out": eased}, type="FLOAT", select=gi["Direction"])[0]

    # ------------------------------------------------------------------ pivot per element
    with g.frame("Pivot"):
        gi = g.inputs("Mesh", "Center", label="Pivot")
        glyph_pivot = g.named("et_pivot", "FLOAT_VECTOR", name="Glyph Pivot")["Attribute"]

        def group_mean(group, label):
            total = g.node(
                "GeometryNodeAccumulateField",
                f"{label} Pivot Sum",
                props={"data_type": "FLOAT_VECTOR", "domain": "POINT"},
                inputs={"Value": glyph_pivot, "Group ID": group},
            )["Total"]
            n = g.node(
                "GeometryNodeAccumulateField",
                f"{label} Point Count",
                props={"data_type": "FLOAT", "domain": "POINT"},
                inputs={"Value": 1.0, "Group ID": group},
            )["Total"]
            return g.vmath(
                "DIVIDE", total, g.combine_xyz(n, n, n, name=f"{label} Count XYZ")[0], name=f"{label} Pivot"
            )[0]

        word_pivot = group_mean(word, "Word")
        line_pivot = group_mean(line, "Line")
        text_pivot = g.node(
            "GeometryNodeAttributeStatistic",
            "Text Pivot",
            inputs={"Geometry": gi["Mesh"], "Attribute": glyph_pivot},
            props={"data_type": "FLOAT_VECTOR", "domain": "POINT"},
        )["Mean"]
        pivot = g.menu(
            "Center",
            {"Letter": glyph_pivot, "Word": word_pivot, "Line": line_pivot, "Text": text_pivot},
            type="VECTOR",
            select=gi["Center"],
        )[0]

    # ------------------------------------------------------------------ transform: scale, rotate, move
    with g.frame("Transform"):
        gi = g.inputs("Offset", "Rotation", "Scale", label="Transform")
        position = g.node("GeometryNodeInputPosition", "Position")[0]
        relative = g.vmath("SUBTRACT", position, pivot, name="From Pivot")[0]
        scale_delta = g.vmath("SUBTRACT", gi["Scale"], (1.0, 1.0, 1.0), name="Scale - 1")[0]
        scale_now = g.vmath(
            "ADD", g.vmath("SCALE", scale_delta, scale=weight, name="Scale Δ × w")[0], (1.0, 1.0, 1.0), name="Scale Now"
        )[0]
        scaled = g.vmath("MULTIPLY", relative, scale_now, name="Scaled")[0]
        rotation_now = g.vmath("SCALE", gi["Rotation"], scale=weight, name="Rotation Now")[0]
        rotated = g.node(
            "ShaderNodeVectorRotate",
            "Rotated",
            props={"rotation_type": "EULER_XYZ"},
            inputs={"Vector": scaled, "Rotation": rotation_now},
        )["Vector"]
        offset_now = g.vmath("SCALE", gi["Offset"], scale=weight, name="Offset Now")[0]
        moved = g.vmath("ADD", g.vmath("ADD", pivot, rotated, name="Back to Pivot")[0], offset_now, name="Moved")[0]

    # ------------------------------------------------------------------ bounce: continuous wobble
    with g.frame("Bounce"):
        gi = g.inputs("Bounce", "Bounce Strength", "Bounce Speed", "Bounce Phase", label="Bounce")
        cycles = g.math(
            "ADD",
            g.math("MULTIPLY", time["Seconds"], gi["Bounce Speed"], name="Seconds × Speed")[0],
            g.math("MULTIPLY", idx, gi["Bounce Phase"], name="Index × Phase")[0],
            name="Cycles",
        )[0]
        wave = g.math("SINE", g.math("MULTIPLY", cycles, 2.0 * math.pi, name="Angle")[0], name="Wave")[0]
        bounce = g.vmath("SCALE", gi["Bounce Strength"], scale=wave, name="Bounce Offset")[0]
        bounce_on = g.switch("VECTOR", gi["Bounce"], (0.0, 0.0, 0.0), bounce, name="Bounce?")[0]
        final_position = g.vmath("ADD", moved, bounce_on, name="Final Position")[0]

    # ------------------------------------------------------------------ apply, reveal, cleanup
    with g.frame("Apply"):
        gi = g.inputs("Mesh", "Animate", "Hide Before Start", "Keep Helper Attributes", label="Apply")
        is_letter = g.compare("GREATER_EQUAL", char, 0, data_type="INT", name="Is Letter")[0]  # the plate is -1
        animated = g.node(
            "GeometryNodeSetPosition",
            "Animate Position",
            inputs={"Geometry": gi["Mesh"], "Selection": is_letter, "Position": final_position},
        )[0]
        animated = g.store(animated, "et_weight", weight, name="Store et_weight")[0]
        not_started = g.compare("LESS_EQUAL", t_raw, 0.0, name="Not Started")[0]
        hide = g.boolean("AND", gi["Hide Before Start"], not_started, name="Hide")[0]
        hide = g.boolean("AND", hide, is_letter, name="Hide Letter")[0]
        revealed = g.node(
            "GeometryNodeDeleteGeometry",
            "Hide Elements",
            inputs={"Geometry": animated, "Selection": hide},
            props={"domain": "POINT", "mode": "ALL"},
        )[0]
        mesh = g.switch("GEOMETRY", gi["Animate"], gi["Mesh"], revealed, name="Animate?")[0]
        stripped = g.node(
            "GeometryNodeRemoveAttribute",
            "Remove et_*",
            inputs={"Geometry": mesh, "Pattern Mode": "Wildcard", "Name": "et_*"},
        )[0]
        final = g.switch("GEOMETRY", gi["Keep Helper Attributes"], stripped, mesh, name="Keep Attributes")[0]
    g.set_output("Mesh", final)
    return g.finish()
