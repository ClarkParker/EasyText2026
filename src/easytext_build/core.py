"""Dünne Helferschicht über bpy zum deterministischen Bauen von Node-Gruppen.

Absichtlich klein gehalten: Nodes anlegen, Inputs setzen oder verlinken, Interface mit Panels,
automatisches Spalten-Layout und Asset-Markierung. Alles andere bleibt reines bpy.
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

X_GAP = 280
Y_GAP = 40


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
        default_width: int | None = None,
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
        return SocketRef(self.group_in, sock.identifier, True)

    def output(self, name: str, type: str, *, description: str = "") -> SocketRef:
        parent = self._panels[-1] if self._panels else None
        sock = self.tree.interface.new_socket(name, in_out="OUTPUT", socket_type=socket_type(type), parent=parent)
        sock.description = description
        return SocketRef(self.group_out, sock.identifier, False)

    def set_output(self, key, value) -> None:
        self._connect(SocketRef(self.group_out, key, False), value)

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
    ) -> NodeRef:
        node = self.tree.nodes.new(idname)
        if name:
            node.name = name
        if label:
            node.label = label
        node.hide = hide
        for key, value in (props or {}).items():
            setattr(node, key, value)
        ref = NodeRef(node)
        for key, value in (inputs or {}).items():
            self.set_input(ref, key, value)
        return ref

    def group(self, tree_or_name, name: str | None = None, *, inputs: dict | None = None) -> NodeRef:
        tree = tree_or_name if isinstance(tree_or_name, bpy.types.NodeTree) else bpy.data.node_groups[tree_or_name]
        idname = {"GeometryNodeTree": "GeometryNodeGroup", "ShaderNodeTree": "ShaderNodeGroup"}[tree.bl_idname]
        ref = self.node(idname, name or tree.name)
        ref.node.node_tree = tree
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

    # ---------------------------------------------------------------- finish
    def finish(self) -> bpy.types.NodeTree:
        self._layout()
        if self.catalog is not None:
            self.tree.asset_mark()
            self.tree.asset_data.catalog_id = self.catalog.uuid
            self.tree.asset_data.description = self.tree.description
            self.tree.asset_data.author = "Easy Text 2026"
            self.tree.asset_data.license = "CC0-1.0"
        return self.tree

    def _layout(self) -> None:
        """Einfaches Spalten-Layout: Spalte = längster Pfad von einer Quelle, Group Output ganz rechts."""
        nodes = list(self.tree.nodes)
        preds: dict[str, set[str]] = {n.name: set() for n in nodes}
        for link in self.tree.links:
            preds[link.to_node.name].add(link.from_node.name)
        depth: dict[str, int] = {}

        def resolve(name: str) -> int:
            if name in depth:
                return depth[name]
            depth[name] = 0
            depth[name] = 1 + max((resolve(p) for p in preds[name]), default=-1)
            return depth[name]

        for n in nodes:
            resolve(n.name)
        max_depth = max((d for k, d in depth.items() if k != self.group_out.name), default=0)
        depth[self.group_out.name] = max_depth + 1
        columns: dict[int, list] = {}
        for n in nodes:
            columns.setdefault(depth[n.name], []).append(n)
        for col, members in columns.items():
            members.sort(key=lambda n: (n.name != self.group_in.name, n.name))
            y = 0.0
            for n in members:
                n.location = (col * X_GAP, y)
                y -= _node_height(n) + Y_GAP


def _node_height(node: bpy.types.Node) -> float:
    visible = [s for s in node.inputs if s.enabled and not s.hide] + [
        s for s in node.outputs if s.enabled and not s.hide
    ]
    return 60 + 22 * len(visible)


def iter_trees(names: Iterable[str]):
    for name in names:
        yield bpy.data.node_groups[name]
