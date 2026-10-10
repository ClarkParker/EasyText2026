"""Dünne Helferschicht über bpy zum deterministischen Bauen von Node-Gruppen.

Absichtlich klein gehalten: Nodes anlegen, Inputs setzen oder verlinken, Interface mit Panels,
Frames mit Block-Layout, lokale Group-Input-Kopien und Asset-Markierung. Alles andere bleibt reines bpy.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable

import bpy

from . import catalog as catalog_mod

SOCKET_ALIASES = {
    "float": "NodeSocketFloat",
    "int": "NodeSocketInt",
    "bool": "NodeSocketBool",
    "vector": "NodeSocketVector",
    "color": "NodeSocketColor",
    "string": "NodeSocketString",
    "geometry": "NodeSocketGeometry",
    "material": "NodeSocketMaterial",
    "object": "NodeSocketObject",
    "collection": "NodeSocketCollection",
    "image": "NodeSocketImage",
    "texture": "NodeSocketTexture",
    "rotation": "NodeSocketRotation",
    "matrix": "NodeSocketMatrix",
    "menu": "NodeSocketMenu",
    "font": "NodeSocketFont",
}

COLUMN_GAP = 70  # Abstand zwischen Spalten innerhalb eines Blocks
ROW_GAP = 30  # Abstand zwischen Nodes einer Spalte
BLOCK_GAP = 160  # Abstand zwischen Frames
FRAME_PAD = 40  # Rand, den Blender um Frame-Kinder legt (nur für die Blockbreite geschätzt)
PROP_IDS = {"operation", "data_type", "domain", "mode", "input_type", "warning_type"}


def socket_type(alias: str) -> str:
    return SOCKET_ALIASES.get(alias, alias)


def find_socket(sockets, key):
    """Socket per Index, Identifier oder (als Fallback) Name finden. Bevorzugt verfügbare Sockets."""
    if isinstance(key, int):
        return sockets[key]
    for sock in sockets:
        if sock.identifier == key:
            return sock
    for sock in sockets:
        if sock.name == key and sock.enabled:
            return sock
    for sock in sockets:
        if sock.name == key:
            return sock
    names = [f"{s.name}({s.identifier})" for s in sockets]
    raise KeyError(f"Kein Socket {key!r}; vorhanden: {names}")


class SocketRef:
    """Verweis auf einen Socket, erst beim Verlinken aufgelöst (Sockets können sich bei Updates ändern)."""

    __slots__ = ("node", "key", "is_output")

    def __init__(self, node: bpy.types.Node, key, is_output: bool):
        self.node = node
        self.key = key
        self.is_output = is_output

    def resolve(self) -> bpy.types.NodeSocket:
        sockets = self.node.outputs if self.is_output else self.node.inputs
        return find_socket(sockets, self.key)


class NodeRef:
    """Wrapper um einen bpy-Node mit bequemem Socket-Zugriff."""

    __slots__ = ("node",)

    def __init__(self, node: bpy.types.Node):
        self.node = node

    def out(self, key=0) -> SocketRef:
        return SocketRef(self.node, key, True)

    def inp(self, key=0) -> SocketRef:
        return SocketRef(self.node, key, False)

    def __getitem__(self, key) -> SocketRef:
        return self.out(key)

    @property
    def name(self) -> str:
        return self.node.name


class GroupBuilder:
    def __init__(
        self,
        name: str,
        *,
        tree_type: str = "GeometryNodeTree",
        description: str = "",
        is_modifier: bool = False,
        is_tool: bool = False,
        color_tag: str | None = None,
        catalog: catalog_mod.Catalog | None = None,
        default_width: int | None = 200,
    ):
        old = bpy.data.node_groups.get(name)
        if old is not None:
            bpy.data.node_groups.remove(old)
        self.tree = bpy.data.node_groups.new(name, tree_type)
        self.tree.description = description
        if tree_type == "GeometryNodeTree":
            self.tree.is_modifier = is_modifier
            self.tree.is_tool = is_tool
        if color_tag:
            self.tree.color_tag = color_tag
        if default_width:
            self.tree.default_group_node_width = default_width
        self.catalog = catalog
        self.group_in = self.tree.nodes.new("NodeGroupInput")
        self.group_in.name = "Group Input"
        self.group_out = self.tree.nodes.new("NodeGroupOutput")
        self.group_out.name = "Group Output"
        self.group_out.is_active_output = True
        self._panels: list[bpy.types.NodeTreeInterfacePanel] = []
        self._menu_defaults: dict[str, str] = {}
        self._frames: list[bpy.types.Node] = []
        self._frame_order: list[bpy.types.Node] = []
        self._input_sockets: dict[str, str] = {}  # Name -> Identifier (erste Definition gewinnt)

    # ---------------------------------------------------------------- interface
    @contextlib.contextmanager
    def panel(self, name: str, *, description: str = "", default_closed: bool = False):
        panel = self.tree.interface.new_panel(name, description=description, default_closed=default_closed)
        if self._panels:
            parent = self._panels[-1]
            self.tree.interface.move_to_parent(panel, parent, len(parent.interface_items))
        self._panels.append(panel)
        try:
            yield panel
        finally:
            self._panels.pop()

    def input(
        self,
        name: str,
        type: str,
        default=None,
        *,
        min=None,
        max=None,
        subtype: str | None = None,
        description: str = "",
        hide_value: bool = False,
        hide_in_modifier: bool = False,
        single_value: bool = False,
        default_input: str | None = None,
        panel_toggle: bool = False,
    ) -> SocketRef:
        parent = self._panels[-1] if self._panels else None
        sock = self.tree.interface.new_socket(name, in_out="INPUT", socket_type=socket_type(type), parent=parent)
        sock.description = description
        if subtype is not None:
            sock.subtype = subtype
        if default is not None:
            sock.default_value = default
        if min is not None:
            sock.min_value = min
        if max is not None:
            sock.max_value = max
        sock.hide_value = hide_value
        sock.hide_in_modifier = hide_in_modifier
        if single_value:
            sock.structure_type = "SINGLE"
        if default_input is not None:
            sock.default_input = default_input
        if panel_toggle:
            sock.is_panel_toggle = True
        self._input_sockets.setdefault(name, sock.identifier)
        return SocketRef(self.group_in, sock.identifier, True)

    def menu_default(self, name: str, value: str) -> None:
        """Default eines Menü-Inputs; wird in finish() gesetzt, wenn die Menü-Einträge über Links bekannt sind."""
        self._menu_defaults[name] = value

    def output(self, name: str, type: str, *, description: str = "") -> SocketRef:
        parent = self._panels[-1] if self._panels else None
        sock = self.tree.interface.new_socket(name, in_out="OUTPUT", socket_type=socket_type(type), parent=parent)
        sock.description = description
        return SocketRef(self.group_out, sock.identifier, False)

    def set_output(self, key, value) -> None:
        self._connect(SocketRef(self.group_out, key, False), value)

    def inputs(self, *names: str, label: str | None = None) -> dict[str, SocketRef]:
        """Lokale Kopie des Group Input im aktuellen Frame, nur mit den genannten Sockets sichtbar."""
        node = self.tree.nodes.new("NodeGroupInput")
        node.name = f"Group Input ({label or ', '.join(names)})"
        node.parent = self._frames[-1] if self._frames else None
        wanted = {self._input_sockets.get(n, n) for n in names}
        for sock in node.outputs:
            try:
                sock.hide = sock.identifier not in wanted
            except Exception:  # virtueller __extend__-Socket
                pass
        return {n: SocketRef(node, self._input_sockets.get(n, n), True) for n in names}

    # ---------------------------------------------------------------- frames
    @contextlib.contextmanager
    def frame(self, label: str, *, color: tuple | None = None, label_size: int = 20):
        node = self.tree.nodes.new("NodeFrame")
        node.name = label
        node.label = label
        node.label_size = label_size
        node.shrink = True
        if color is not None:
            node.use_custom_color = True
            node.color = color
        if self._frames:
            node.parent = self._frames[-1]
        self._frames.append(node)
        self._frame_order.append(node)
        try:
            yield node
        finally:
            self._frames.pop()

    # ---------------------------------------------------------------- nodes
    def node(
        self,
        idname: str,
        name: str | None = None,
        *,
        label: str | None = None,
        inputs: dict | None = None,
        props: dict | None = None,
        hide: bool = False,
        width: float | None = None,
    ) -> NodeRef:
        node = self.tree.nodes.new(idname)
        if name:
            node.name = name
        if label:
            node.label = label
        node.hide = hide
        if width:
            node.width = width
        node.parent = self._frames[-1] if self._frames else None
        for key, value in (props or {}).items():
            setattr(node, key, value)
        ref = NodeRef(node)
        for key, value in (inputs or {}).items():
            self.set_input(ref, key, value)
        return ref

    def group(self, tree_or_name, name: str | None = None, *, inputs: dict | None = None, label=None) -> NodeRef:
        tree = tree_or_name if isinstance(tree_or_name, bpy.types.NodeTree) else bpy.data.node_groups[tree_or_name]
        idname = {"GeometryNodeTree": "GeometryNodeGroup", "ShaderNodeTree": "ShaderNodeGroup"}[tree.bl_idname]
        ref = self.node(idname, name or tree.name.lstrip("."), label=label)
        ref.node.node_tree = tree
        ref.node.width = tree.default_group_node_width
        for key, value in (inputs or {}).items():
            self.set_input(ref, key, value)
        return ref

    def set_input(self, ref: NodeRef, key, value) -> None:
        self._connect(ref.inp(key), value)

    def link(self, source, target) -> None:
        self._connect(target if isinstance(target, SocketRef) else SocketRef(target.node, 0, False), source)

    def _connect(self, target: SocketRef, value) -> None:
        sock = target.resolve()
        if isinstance(value, NodeRef):
            value = value.out(0)
        if isinstance(value, SocketRef):
            self.tree.links.new(value.resolve(), sock)
        elif isinstance(value, bpy.types.NodeSocket):
            self.tree.links.new(value, sock)
        elif isinstance(value, list | tuple) and value and isinstance(value[0], SocketRef | NodeRef):
            for item in value:  # Multi-Input-Socket (z. B. Join Geometry)
                self._connect(target, item)
        else:
            sock.default_value = value

    # ---------------------------------------------------------------- Kurzformen für häufige Nodes
    def math(self, op: str, a, b=None, c=None, *, name: str | None = None, clamp: bool = False) -> NodeRef:
        inputs = {"Value": a}
        if b is not None:
            inputs["Value_001"] = b
        if c is not None:
            inputs["Value_002"] = c
        return self.node("ShaderNodeMath", name, props={"operation": op, "use_clamp": clamp}, inputs=inputs)

    def vmath(self, op: str, a, b=None, *, scale=None, name: str | None = None) -> NodeRef:
        inputs = {"Vector": a}
        if b is not None:
            inputs["Vector_001"] = b
        if scale is not None:
            inputs["Scale"] = scale
        return self.node("ShaderNodeVectorMath", name, props={"operation": op}, inputs=inputs)

    def compare(self, op: str, a, b, *, data_type: str = "FLOAT", name: str | None = None) -> NodeRef:
        return self.node(
            "FunctionNodeCompare", name, props={"operation": op, "data_type": data_type}, inputs={"A": a, "B": b}
        )

    def boolean(self, op: str, a, b=None, *, name: str | None = None) -> NodeRef:
        inputs = {"Boolean": a}
        if b is not None:
            inputs["Boolean_001"] = b
        return self.node("FunctionNodeBooleanMath", name, props={"operation": op}, inputs=inputs)

    def switch(self, type: str, condition, false, true, *, name: str | None = None) -> NodeRef:
        return self.node(
            "GeometryNodeSwitch",
            name,
            props={"input_type": type},
            inputs={"Switch": condition, "False": false, "True": true},
        )

    def fallback(self, type: str, value, default, *, name: str | None = None) -> SocketRef:
        """Datablock-Input mit Ersatzwert: Ist `value` leer (None), wird `default` als Node-Default verwendet.

        Nötig, weil Blender 5.2.0 Datablock-Defaults am Group-Interface nicht in den Modifier übernimmt.
        """
        is_none = self.node(
            "FunctionNodeCompare",
            f"{name or type.title()} Is None",
            props={"data_type": type, "operation": "EQUAL"},
            inputs={"A": value},
        )
        switch = self.node(
            "GeometryNodeSwitch",
            f"{name or type.title()} Fallback",
            props={"input_type": type},
            inputs={"Switch": is_none[0], "False": value},
        )
        switch.node.inputs["True"].default_value = default
        return switch[0]

    def named(self, attr: str, data_type: str = "FLOAT", *, name: str | None = None) -> NodeRef:
        return self.node("GeometryNodeInputNamedAttribute", name, props={"data_type": data_type}, inputs={"Name": attr})

    def store(
        self, geometry, attr: str, value, *, domain: str = "POINT", data_type: str = "FLOAT", selection=None, name=None
    ) -> NodeRef:
        inputs = {"Geometry": geometry, "Name": attr, "Value": value}
        if selection is not None:
            inputs["Selection"] = selection
        return self.node(
            "GeometryNodeStoreNamedAttribute",
            name,
            props={"data_type": data_type, "domain": domain},
            inputs=inputs,
        )

    def sample_index(
        self, geometry, value, index, *, domain: str = "POINT", data_type: str = "FLOAT", name=None
    ) -> NodeRef:
        return self.node(
            "GeometryNodeSampleIndex",
            name,
            props={"data_type": data_type, "domain": domain},
            inputs={"Geometry": geometry, "Value": value, "Index": index},
        )

    def separate_xyz(self, vector, *, name=None) -> NodeRef:
        return self.node("ShaderNodeSeparateXYZ", name, inputs={"Vector": vector})

    def combine_xyz(self, x=0.0, y=0.0, z=0.0, *, name=None) -> NodeRef:
        return self.node("ShaderNodeCombineXYZ", name, inputs={"X": x, "Y": y, "Z": z})

    # ---------------------------------------------------------------- finish
    def finish(self) -> bpy.types.NodeTree:
        for name, value in self._menu_defaults.items():
            self.tree.interface.items_tree[name].default_value = value
        if not any(link.from_node == self.group_in for link in self.tree.links):
            self.tree.nodes.remove(self.group_in)  # alle Inputs laufen über lokale Kopien
            self.group_in = None
        self._layout()
        if self.catalog is not None:
            self.tree.asset_mark()
            self.tree.asset_data.catalog_id = self.catalog.uuid
            self.tree.asset_data.description = self.tree.description
            self.tree.asset_data.author = "Easy Text 2026"
            self.tree.asset_data.license = "CC0-1.0"
        return self.tree

    # ---------------------------------------------------------------- layout
    def _layout(self) -> None:
        """Block-Layout: jeder Top-Level-Frame ist ein Block (eigene Spalten), Blöcke stehen in Datenflussreihenfolge
        nebeneinander. Nodes ohne Frame bilden einen Block am Anfang (Group Input) bzw. am Ende (Rest)."""
        nodes = [n for n in self.tree.nodes if n.bl_idname != "NodeFrame"]
        top_frames = [f for f in self._frame_order if f.parent is None]

        def top_frame(node):
            parent = node.parent
            while parent is not None and parent.parent is not None:
                parent = parent.parent
            return parent

        blocks: list[list] = []
        head = [n for n in nodes if top_frame(n) is None and n == self.group_in]
        if head:
            blocks.append(head)
        for frame in top_frames:
            members = [n for n in nodes if top_frame(n) == frame]
            if members:
                blocks.append(members)
        tail = [n for n in nodes if top_frame(n) is None and n != self.group_in]
        if tail:
            blocks.append(tail)

        x_cursor = 0.0
        for block in blocks:
            width = self._layout_block(block, x_cursor)
            x_cursor += width + BLOCK_GAP

    def _layout_block(self, block: list, x_start: float) -> float:
        names = {n.name for n in block}
        preds: dict[str, list] = {n.name: [] for n in block}
        succs: dict[str, list] = {n.name: [] for n in block}
        for link in self.tree.links:
            a, b = link.from_node.name, link.to_node.name
            if a in names and b in names:
                preds[b].append(a)
                succs[a].append(b)
        depth: dict[str, int] = {}

        def resolve(name: str) -> int:
            if name in depth:
                return depth[name]
            depth[name] = 0
            depth[name] = 1 + max((resolve(p) for p in preds[name]), default=-1)
            return depth[name]

        for n in block:
            resolve(n.name)
        # Quellen (ohne Vorgänger im Block) direkt vor ihre Verbraucher ziehen
        for n in block:
            if not preds[n.name] and succs[n.name]:
                depth[n.name] = min(depth[s] for s in succs[n.name]) - 1
        if self.group_out in block:
            depth[self.group_out.name] = max(depth.values()) + 1
        min_depth = min(depth.values())
        columns: dict[int, list] = {}
        for n in block:
            columns.setdefault(depth[n.name] - min_depth, []).append(n)

        # Reihenfolge je Spalte: Schwerpunkt der Vorgänger (zwei Durchläufe, zweiter rückwärts für Quellen)
        rank: dict[str, float] = {}
        for col in sorted(columns):
            members = columns[col]
            for i, n in enumerate(members):
                linked = [rank[p] for p in preds[n.name] if p in rank]
                rank[n.name] = sum(linked) / len(linked) if linked else float(i)
            members.sort(key=lambda n: (rank[n.name], n.name))
            for i, n in enumerate(members):
                rank[n.name] = float(i)
        for col in sorted(columns, reverse=True):
            members = columns[col]
            for n in members:
                if not preds[n.name] and succs[n.name]:
                    linked = [rank[s] for s in succs[n.name] if s in rank]
                    if linked:
                        rank[n.name] = sum(linked) / len(linked) - 0.01
            members.sort(key=lambda n: (rank[n.name], n.name))
            for i, n in enumerate(members):
                rank[n.name] = float(i)

        x = x_start
        for col in sorted(columns):
            members = columns[col]
            col_width = max(_node_width(n) for n in members)
            y = 0.0
            for n in members:
                n.location_absolute = (x, y)
                y -= _node_height(n) + ROW_GAP
            x += col_width + COLUMN_GAP
        return x - x_start - COLUMN_GAP + (2 * FRAME_PAD if any(n.parent for n in block) else 0)


def _node_width(node: bpy.types.Node) -> float:
    return float(node.width)


def _node_height(node: bpy.types.Node) -> float:
    if node.hide:
        return 32.0
    visible = [s for s in node.inputs if s.enabled and not s.hide] + [
        s for s in node.outputs if s.enabled and not s.hide
    ]
    props = sum(1 for p in node.bl_rna.properties if p.identifier in PROP_IDS)
    extra = 24 if node.bl_idname in ("GeometryNodeInputNamedAttribute", "GeometryNodeStringToCurves") else 0
    return 34 + 22 * len(visible) + 24 * props + extra


def builtin_font() -> bpy.types.VectorFont:
    """Blenders eingebauter Font (Bfont Regular); wird bei Bedarf geladen."""
    font = bpy.data.fonts.get("Bfont Regular")
    if font is None:
        font = bpy.data.fonts.load("<builtin>")
    # Nur als Socket-Default referenziert zählt in 5.2.0 nicht als Nutzer: ohne Fake-User fehlt der Font nach dem Laden.
    font.use_fake_user = True
    return font


def iter_trees(names: Iterable[str]):
    for name in names:
        yield bpy.data.node_groups[name]
