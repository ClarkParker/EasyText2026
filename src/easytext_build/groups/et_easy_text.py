"""Easy Text: the control panel. The same six-stage pipeline as ET Text Mesh, but every input is a value node
(a control) sitting next to the stage that uses it, so the whole tool is operated inside the node editor:
text, font and spacing at the Text stage, depth at Solid, bevel settings at Bevel, and so on. A value that
several stages need (Depth) travels along a labelled reroute bus below the stages.

Use ET Text Mesh as the modifier instead when you prefer the properties editor."""

from __future__ import annotations

from .. import catalog, materials
from ..core import GroupBuilder, NodeRef, SocketRef, _node_height, _node_width, builtin_font
from . import et_text_mesh

NAME = "Easy Text"

NODE_W = 140  # control width
WIDE_W = 320  # the multi-line text box
PITCH_X = 180  # column pitch of controls
ROW = 96  # row pitch of controls
TEXTBOX_H = 150  # the multi-line text box is taller than a value node
GAP = 60  # controls -> stage node
STAGE_GAP = 120  # between stage frames
GRID_TOP = -90  # controls start below the geometry bus that enters the stage node at its top socket
BUS_GAP = 50  # reroute bus below the lowest control grid
README_H = 180

README = """EASY TEXT 3 — control panel
Six stages from left to right: Text → Outline → Solid → Bevel → UV → Finish. Each stage is one node group; \
the controls on its left feed it, the mesh flows along the top.
Type into the Text box (several lines are fine), pick a font, then shape the mesh with Depth, Bevel and the \
materials. UV adds the export-ready UV map. Tab into a stage to see how it works.
Prefer the properties editor? Use the node group ET Text Mesh as the modifier: same pipeline, inputs as panels."""

# name -> (kind, default); kinds map to Blender's constant input nodes
CONTROLS = {
    "Text": ("string", "Easy Text\nGeometry Node 3"),
    "Font": ("font", None),
    "Size": ("float", 1.0),
    "Align X": ("menu", "Center"),
    "Align Y": ("menu", "Middle"),
    "Pivot": ("menu", "Midpoint"),
    "Character Spacing": ("float", 1.0),
    "Word Spacing": ("float", 1.0),
    "Line Spacing": ("float", 1.0),
    "Box Width": ("float", 0.0),
    "Box Height": ("float", 0.0),
    "Overflow": ("menu", "Overflow"),
    "Resolution": ("int", 12),
    "Simplify": ("float", 0.5),
    "Fill Mode": ("menu", "N-gons"),
    "Fill Rule": ("menu", "Even-Odd"),
    "Front Material": ("material", "ET Front"),
    "Depth": ("float", 0.1),
    "Bevel": ("bool", False),
    "Bevel Width": ("float", 0.01),
    "Segments": ("int", 3),
    "Profile": ("float", 0.5),
    "UV": ("bool", True),
    "Normalize to Text": ("bool", True),
    "UV Scale": ("float", 1.0),
    "Side Material": ("material", "ET Side"),
    "Bevel Material": ("material", "ET Bevel"),
    "Smooth Angle": ("float", 30.0),
    "Keep Helper Attributes": ("bool", False),
}
NODE_TYPES = {
    "string": "FunctionNodeInputString",
    "font": "GeometryNodeInputFont",
    "float": "ShaderNodeValue",
    "int": "FunctionNodeInputInt",
    "bool": "FunctionNodeInputBool",
    "menu": "FunctionNodeInputMenu",
    "material": "GeometryNodeInputMaterial",
}


class Controls:
    """Input provider for `build_pipeline`: one value node per input name, created in the stage frame that asks
    for it first. A later stage that needs the same value gets a labelled reroute in its own frame, so the value
    travels along a visible bus instead of a long diagonal link."""

    def __init__(self, g: GroupBuilder, mats):
        self.g = g
        self.mats = mats
        self.nodes: dict[str, NodeRef] = {}  # name -> control
        self.last: dict[str, SocketRef] = {}  # name -> socket the bus continues from
        self.per_frame: dict[str, list] = {}  # frame name -> controls in grid order
        self.reroutes: dict[str, list] = {}  # frame name -> bus reroutes

    def __call__(self, stage: str, *names: str) -> dict[str, SocketRef]:
        frame = self.g._frames[-1]
        out = {}
        for name in names:
            if name not in CONTROLS:
                continue  # Line 2-4: the text box takes several lines itself
            if name in self.nodes:
                rr = self.g.node("NodeReroute", f"{name} ({stage})", label=name, inputs={0: self.last[name]})
                self.reroutes.setdefault(frame.name, []).append(rr.node)
                self.last[name] = rr[0]
            else:
                ref = self._make(name)
                self.nodes[name] = ref
                self.last[name] = ref[0]
                self.per_frame.setdefault(frame.name, []).append(ref.node)
            out[name] = self.last[name]
        return out

    def _make(self, name: str) -> NodeRef:
        kind, default = CONTROLS[name]
        ref = self.g.node(NODE_TYPES[kind], name, label=name, width=WIDE_W if kind == "string" else NODE_W)
        node = ref.node
        if kind == "string":
            node.string = default  # multi-line; drag the text box edge in the editor to show more lines
        elif kind == "font":
            node.font = builtin_font()
        elif kind == "float":
            node.outputs[0].default_value = default
        elif kind == "int":
            node.integer = default
        elif kind == "bool":
            node.boolean = default
        elif kind == "material":
            node.material = self.mats[default]
        # menus: the items are known once the node is linked, see build()
        return ref


def _layout(g: GroupBuilder, controls: Controls, stages: list) -> float:
    """Stage frames in a row: controls in a grid on the left, the stage node to its right at the top, the reroute
    bus below everything. Returns the right edge of the last stage."""
    tree = g.tree
    x = 0.0
    bus_frames: list[tuple[list, float]] = []  # (reroutes, x) per frame
    bottoms: dict[str, float] = {}  # frame name -> lowest node edge
    bus_names = {rr.label for bus in controls.reroutes.values() for rr in bus}
    bus_sources = {controls.nodes[name].node.parent.name for name in bus_names}
    for i, frame in enumerate(stages):
        ctrls = controls.per_frame.get(frame.name, [])
        cols = 2 if len(ctrls) > 4 else 1
        top = 0.0 if i == 0 else GRID_TOP  # the first stage has no geometry coming in
        y, col = top, 0
        grid_w = NODE_W + (cols - 1) * PITCH_X
        for node in ctrls:
            if node.width > NODE_W:  # wide control: a row of its own
                if col:
                    y, col = y - ROW, 0
                node.location_absolute = (x, y)
                y -= TEXTBOX_H
                grid_w = max(grid_w, node.width)
                continue
            node.location_absolute = (x + col * PITCH_X, y)
            col += 1
            if col == cols:
                y, col = y - ROW, 0
        if col:
            y -= ROW
        bottoms[frame.name] = y
        bus = controls.reroutes.get(frame.name, [])
        if bus:
            bus_frames.append((bus, x))

        others = [n for n in tree.nodes if n.parent == frame and n not in ctrls and n not in bus]
        sx, sy, right = x + grid_w + GAP, 0.0, x + grid_w
        for node in others:  # normally just the stage node
            node.location_absolute = (sx, sy)
            right = max(right, sx + _node_width(node))
            sy -= _node_height(node) + 30
        bottoms[frame.name] = min(bottoms[frame.name], sy)
        x = right + STAGE_GAP
    # the bus runs just below the frames it touches: the one holding the control and the ones with reroutes
    touched = bus_sources | {name for name, bus in controls.reroutes.items() if bus}
    bus_y = min(bottoms[name] for name in touched) - BUS_GAP if touched else 0.0
    for bus, fx in bus_frames:
        for k, rr in enumerate(bus):
            rr.location_absolute = (fx + k * 40, bus_y)
    return x - STAGE_GAP


def build():
    mats = materials.ensure_all()
    g = GroupBuilder(
        NAME,
        description="Easy Text control panel: the text pipeline with value nodes as controls.",
        is_modifier=True,
        catalog=catalog.ROOT,
        color_tag="GEOMETRY",
        default_width=240,
        compact=False,
        arrange=False,
    )
    g.output("Geometry", "geometry")
    controls = Controls(g, mats)

    with g.frame("Easy Text 3", label_size=32) as outer:
        with g.frame("Read Me", text=README, size=(WIDE_W, README_H)):
            pass  # a note frame: no child nodes, the text is the content
        final = et_text_mesh.build_pipeline(g, controls)
    g.set_output("Geometry", final)
    g.group_out.parent = outer

    for name, (kind, default) in CONTROLS.items():  # menu items exist once the node is linked
        if kind == "menu":
            controls.nodes[name].node.value = default
    for node in g.tree.nodes:  # the text box carries all lines; hide the unused line sockets
        if node.bl_idname == "GeometryNodeGroup":
            for sock in node.inputs:
                if sock.name.startswith("Line ") and not sock.is_linked:
                    sock.hide = True

    # ---------------------------------------------------------------- layout by hand
    stages = [f for f in g._frame_order if f.parent == outer and f.label != "Read Me"]
    right = _layout(g, controls, stages)
    readme = next(f for f in g._frame_order if f.label == "Read Me")
    readme.width = right
    readme.location_absolute = (0.0, README_H + 110.0)  # above the stage frames and their labels
    g.place(NodeRef(g.group_out), right + STAGE_GAP, 0.0)
    return g.finish()
