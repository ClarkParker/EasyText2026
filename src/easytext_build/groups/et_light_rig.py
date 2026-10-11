"""ET Light Rig: a three-point light rig around a target object, built from instances of light objects.

Put the modifier on an Empty, pick the text as Target and your key, fill and rim light objects: the rig places
an instance of each light on a sphere around the centre of the target's bounds (angle, elevation, distance) and
aims it at the centre. Instanced lights render in Cycles and EEVEE; the original light objects can stay hidden.
Angle 0 is in front of the text (-Y), positive angles go clockwise seen from above."""

import math

from .. import catalog
from ..core import GroupBuilder, heading

NAME = "ET Light Rig"
LIGHTS = (  # name, angle, elevation, distance
    ("Key", -35.0, 35.0, 5.0),
    ("Fill", 45.0, 15.0, 6.0),
    ("Rim", 160.0, 40.0, 5.0),
)


def build():
    g = GroupBuilder(
        NAME,
        description="Three-point light rig: instances of your key, fill and rim lights around a target, aimed at it.",
        is_modifier=True,
        catalog=catalog.SCENE,
        color_tag="GEOMETRY",
        default_width=260,
    )
    g.input("Target", "object", description="The text (or any object); the rig aims at the centre of its bounds.")
    g.input("Aim at Target", "bool", True, description="Point every light at the target centre.")
    for name, angle, elevation, distance in LIGHTS:
        with g.panel(heading(f"{name} Light")):
            g.input(name, "bool", True, panel_toggle=True)
            g.input(f"{name} Light", "object", description="A light object; it is instanced here and can stay hidden.")
            g.input(
                f"{name} Angle",
                "float",
                math.radians(angle),
                min=-math.pi,
                max=math.pi,
                subtype="ANGLE",
                description="Around the target; 0 = in front.",
            )
            g.input(
                f"{name} Elevation",
                "float",
                math.radians(elevation),
                min=-math.pi / 2,
                max=math.pi / 2,
                subtype="ANGLE",
                description="Above (positive) or below the target.",
            )
            g.input(
                f"{name} Distance",
                "float",
                distance,
                min=0.01,
                max=1000.0,
                subtype="DISTANCE",
                description="From the centre.",
            )
    g.output("Lights", "geometry")

    # ------------------------------------------------------------------ target centre
    with g.frame("Target"):
        gi = g.inputs("Target", label="Target")
        info = g.node(
            "GeometryNodeObjectInfo",
            "Target Info",
            props={"transform_space": "RELATIVE"},
            inputs={"Object": gi["Target"]},
        )
        bbox = g.node("GeometryNodeBoundBox", "Target Bounds", inputs={"Geometry": info["Geometry"]})
        center = g.vmath(
            "SCALE", g.vmath("ADD", bbox["Min"], bbox["Max"], name="Min + Max")[0], scale=0.5, name="Target Centre"
        )[0]

    # ------------------------------------------------------------------ one instance per light
    rigs = []
    for name, _angle, _elevation, _distance in LIGHTS:
        with g.frame(f"{name} Light"):
            gi = g.inputs(
                name,
                f"{name} Light",
                f"{name} Angle",
                f"{name} Elevation",
                f"{name} Distance",
                "Aim at Target",
                label=name,
            )
            cos_el = g.math("COSINE", gi[f"{name} Elevation"], name="cos Elevation")[0]
            direction = g.combine_xyz(
                g.math("MULTIPLY", g.math("SINE", gi[f"{name} Angle"], name="sin Angle")[0], cos_el, name="Dir X")[0],
                g.math(
                    "MULTIPLY",
                    g.math(
                        "MULTIPLY", g.math("COSINE", gi[f"{name} Angle"], name="cos Angle")[0], -1.0, name="-cos Angle"
                    )[0],
                    cos_el,
                    name="Dir Y",
                )[0],
                g.math("SINE", gi[f"{name} Elevation"], name="Dir Z")[0],
                name="Direction",
            )[0]
            position = g.vmath(
                "ADD",
                center,
                g.vmath("SCALE", direction, scale=gi[f"{name} Distance"], name="Offset")[0],
                name="Position",
            )[0]
            # a light shines along its local -Z: Z away from the target, Y up
            aim = g.node(
                "FunctionNodeAxesToRotation",
                "Aim",
                props={"primary_axis": "Z", "secondary_axis": "Y"},
                inputs={"Primary Axis": direction, "Secondary Axis": (0.0, 0.0, 1.0)},
            )["Rotation"]
            rotation = g.switch("ROTATION", gi["Aim at Target"], (0.0, 0.0, 0.0), aim, name="Rotation")[0]
            point = g.node("GeometryNodePoints", "Point", inputs={"Count": 1, "Position": position})["Points"]
            light = g.node(
                "GeometryNodeObjectInfo",
                f"{name} Object",
                props={"transform_space": "ORIGINAL"},
                inputs={"Object": gi[f"{name} Light"], "As Instance": True},
            )["Geometry"]
            placed = g.node(
                "GeometryNodeInstanceOnPoints",
                f"Place {name}",
                inputs={"Points": point, "Instance": light, "Rotation": rotation},
            )["Instances"]
            empty = g.node("GeometryNodePoints", "Nothing", inputs={"Count": 0})["Points"]
            rigs.append(g.switch("GEOMETRY", gi[name], empty, placed, name=f"{name}?")[0])

    with g.frame("Rig"):
        lights = g.node("GeometryNodeJoinGeometry", "Join Lights", inputs={"Geometry": rigs})[0]
    g.set_output("Lights", lights)
    return g.finish()
