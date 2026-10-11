"""Thin helper layer over bpy for building node groups deterministically.

Deliberately small: create nodes, set or link inputs, interface with panels, frames with a block layout,
local Group Input copies and asset marking. Everything else stays plain bpy.
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

COLUMN_GAP = 50  # gap between columns inside a block (Essentials: ~40-60)
ROW_GAP = 36  # gap between nodes in a column
BLOCK_GAP = 140  # gap between frame columns
BLOCK_VGAP = 110  # gap between stacked frames
FRAME_PAD = 40  # padding Blender draws around frame children (estimate for the block width)
PROP_IDS = {"operation", "data_type", "domain", "mode", "input_type", "warning_type"}
HEADER_H = 30.0  # node header
SOCKET_H = 22.0  # height of one socket row
PROP_H = 24.0  # height of one property row (dropdown)
COLLAPSED_H = 32.0
REROUTE_SIZE = 16.0
GROUP_INPUT_COLOR = (0.510, 0.208, 0.298)  # theme Input class colour, as used by Blender's Essentials
SOCKET_MAP_KEY = "et_sockets"  # ID property on every built group: input name -> socket identifier
COMPACT_TYPES = {
    "ShaderNodeMath",
    "ShaderNodeVectorMath",
    "FunctionNodeBooleanMath",
    "FunctionNodeCompare",
    "ShaderNodeSeparateXYZ",
    "ShaderNodeCombineXYZ",
}


def heading(name: str) -> str:
    """Panel or frame title in the ASCII style of the v2.1 GUI, e.g. '-=| Mesh Settings |=-'."""
    return f"-=| {name} |=-"


def subheading(name: str) -> str:
    """Nested panel title, e.g. '-- Bevel --'."""
    return f"-- {name} --"


def socket_type(alias: str) -> str:
    return SOCKET_ALIASES.get(alias, alias)


def find_socket(sockets, key):
    """Find a socket by index, identifier or (as fallback) name. Prefers available sockets."""
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
    raise KeyError(f"No socket {key!r}; available: {names}")


class SocketRef:
    """Reference to a socket, resolved when linking (sockets can change during updates)."""

    __slots__ = ("node", "key", "is_output")

    def __init__(self, node: bpy.types.Node, key, is_output: bool):
        self.node = node
        self.key = key
        self.is_output = is_output

    def resolve(self) -> bpy.types.NodeSocket:
        sockets = self.node.outputs if self.is_output else self.node.inputs
        try:
            return find_socket(sockets, self.key)
        except KeyError:
            # Group node: Blender 5.2 renames a panel-toggle socket to its panel's name ("-- Bevel --"), so the
            # builder's own name -> identifier map, stored on the group, resolves the logical name ("Bevel").
            tree = getattr(self.node, "node_tree", None)
            identifier = (tree.get(SOCKET_MAP_KEY) or {}).get(self.key) if tree is not None else None
            if identifier is None:
                raise
            return find_socket(sockets, identifier)


def group_socket(node: bpy.types.Node, name: str, *, output: bool = False) -> bpy.types.NodeSocket:
    """Socket of a group node by interface name, including panel toggles (shown under the panel's name)."""
    return SocketRef(node, name, output).resolve()


class NodeRef:
    """Wrapper around a bpy node with convenient socket access."""

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
        compact: bool = True,
        reroutes: bool = False,
        arrange: bool = True,
    ):
        self.arrange = arrange  # False: positions are set by hand (control-panel trees)
        self.compact = compact  # draw small math nodes collapsed (as in Blender's Essentials)
        self.reroutes = reroutes  # fallback layout only: route long links through reroute stations
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
        self._input_sockets: dict[str, str] = {}  # name -> identifier (first definition wins)

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
        """Default of a menu input; applied in finish() once the menu items are known through links."""
        self._menu_defaults[name] = value

    def output(self, name: str, type: str, *, description: str = "") -> SocketRef:
        parent = self._panels[-1] if self._panels else None
        sock = self.tree.interface.new_socket(name, in_out="OUTPUT", socket_type=socket_type(type), parent=parent)
        sock.description = description
        return SocketRef(self.group_out, sock.identifier, False)

    def set_output(self, key, value) -> None:
        self._connect(SocketRef(self.group_out, key, False), value)

    def inputs(self, *names: str, label: str | None = None) -> dict[str, SocketRef]:
        """Local copy of the Group Input in the current frame, showing only the named sockets."""
        node = self.tree.nodes.new("NodeGroupInput")
        node.name = f"Group Input ({label or ', '.join(names)})"
        node.parent = self._frames[-1] if self._frames else None
        node.use_custom_color = True
        node.color = GROUP_INPUT_COLOR
        wanted = {self._input_sockets.get(n, n) for n in names}
        for sock in node.outputs:
            try:
                sock.hide = sock.identifier not in wanted
            except Exception:  # virtual __extend__ socket
                pass
        return {n: SocketRef(node, self._input_sockets.get(n, n), True) for n in names}

    # ---------------------------------------------------------------- frames
    @contextlib.contextmanager
    def frame(
        self,
        label: str,
        *,
        color: tuple | None = None,
        label_size: int = 20,
        text: str | None = None,
        size: tuple | None = None,
        location: tuple | None = None,
    ):
        node = self.tree.nodes.new("NodeFrame")
        node.name = f"[{label}]"  # frames share the node namespace; keep the plain name free for nodes
        node.label = label
        node.label_size = label_size
        node.shrink = True
        if color is not None:
            node.use_custom_color = True
            node.color = color
        if text:
            note = bpy.data.texts.new(f"{self.tree.name} – {label}")
            note.write(text)
            node.text = note
        if size is not None:
            node.shrink = False
            node.width, node.height = size
        if location is not None:
            node.location_absolute = location
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
        default_name = node.name.split(".")[0]
        if name:
            node.name = name
            if label is None and name != default_name and idname not in ("NodeGroupInput", "NodeGroupOutput"):
                label = name  # visible header = intent, not node type
        if label:
            node.label = label
        node.hide = hide or (self.compact and idname in COMPACT_TYPES)
        if width:
            node.width = width
        node.parent = self._frames[-1] if self._frames else None
        for key, value in (props or {}).items():
            setattr(node, key, value)
        ref = NodeRef(node)
        for key, value in (inputs or {}).items():
            self.set_input(ref, key, value)
        return ref

    def place(self, ref: NodeRef, x: float, y: float) -> NodeRef:
        """Manual position (absolute canvas coordinates); used by hand-laid-out trees."""
        ref.node.location_absolute = (x, y)
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
            # Multi-input socket (Join Strings, Join Geometry): Blender puts every new link on top, so link in
            # reverse to keep the list order (matters for strings).
            for item in reversed(value):
                self._connect(target, item)
        else:
            sock.default_value = value

    # ---------------------------------------------------------------- shortcuts for common nodes
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
        """Data-block input with fallback: when `value` is empty (None), `default` is used as the node default.

        Needed because Blender 5.2.0 does not copy interface data-block defaults into the modifier.
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
            self.tree.nodes.remove(self.group_in)  # all inputs go through local copies
            self.group_in = None
        if self.arrange and not self._arrange():
            self._layout()
        for node in self.tree.nodes:
            node.select = False  # a saved file should not open with every node highlighted
        self.tree[SOCKET_MAP_KEY] = dict(self._input_sockets)  # logical names survive panel-toggle renames
        if self.catalog is not None:
            self.tree.asset_mark()
            self.tree.asset_data.catalog_id = self.catalog.uuid
            self.tree.asset_data.description = self.tree.description
            self.tree.asset_data.author = "Easy Text 2026"
            self.tree.asset_data.license = "CC0-1.0"
        return self.tree

    # ---------------------------------------------------------------- layout
    def _arrange(self) -> bool:
        """Sugiyama layout from nodebpy (headless port of the Node Arrange add-on). Returns False if unavailable."""
        try:
            from nodebpy.layout import api, config
        except ImportError:
            return False
        options = config.SugiyamaOptions(
            margin=(40.0, 30.0),
            socket_alignment="MODERATE",
            reroutes="blocked",
            fit_collapsed_widths=True,
        )
        api.arrange(self.tree, options)
        return True

    def _layout(self) -> None:
        """Block layout: every top-level frame is a block with its own columns; blocks are arranged in data-flow
        order, independent blocks stacked vertically. Nodes without a frame form a block at the start (Group
        Input) or at the end (rest)."""
        for node in self.tree.nodes:
            if node.hide and node.bl_idname not in ("NodeFrame", "NodeReroute"):
                node.width = _collapsed_width(node)
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

        # blocks in columns by dependency; independent blocks of one column are stacked
        block_of = {n.name: i for i, block in enumerate(blocks) for n in block}
        block_preds: dict[int, set[int]] = {i: set() for i in range(len(blocks))}
        for link in self.tree.links:
            a, b = block_of.get(link.from_node.name), block_of.get(link.to_node.name)
            if a is not None and b is not None and a != b:
                block_preds[b].add(a)
        block_depth: dict[int, int] = {}

        def resolve_block(i: int) -> int:
            if i in block_depth:
                return block_depth[i]
            block_depth[i] = 0
            block_depth[i] = 1 + max((resolve_block(p) for p in block_preds[i]), default=-1)
            return block_depth[i]

        for i in range(len(blocks)):
            resolve_block(i)
        x_cursor = 0.0
        top: dict[str, float] = {}
        for col in sorted(set(block_depth.values())):
            members = [i for i in range(len(blocks)) if block_depth[i] == col]
            col_width = 0.0
            y_shift = 0.0
            for i in members:
                block = blocks[i]
                width = self._layout_block(block, x_cursor, top)
                col_width = max(col_width, width)
                if y_shift:
                    for n in block:
                        n.location_absolute = (n.location_absolute.x, n.location_absolute.y - y_shift)
                        top[n.name] -= y_shift
                lowest = min(n.location_absolute.y - _node_height(n) for n in block)
                y_shift = -lowest + BLOCK_VGAP
            x_cursor += col_width + BLOCK_GAP

    def _layout_block(self, block: list, x_start: float, top: dict[str, float]) -> float:
        names = {n.name for n in block}
        by_name = {n.name: n for n in block}

        def block_links():
            return [lk for lk in self.tree.links if lk.from_node.name in names and lk.to_node.name in names]

        preds: dict[str, list] = {n.name: [] for n in block}
        succs: dict[str, list] = {n.name: [] for n in block}
        for link in block_links():
            preds[link.to_node.name].append(link.from_node.name)
            succs[link.from_node.name].append(link.to_node.name)

        # 1. columns: longest path; sources right before their consumers
        depth: dict[str, int] = {}

        def resolve(name: str) -> int:
            if name in depth:
                return depth[name]
            depth[name] = 0
            depth[name] = 1 + max((resolve(p) for p in preds[name]), default=-1)
            return depth[name]

        for n in block:
            resolve(n.name)
        for n in block:
            if not preds[n.name] and succs[n.name]:
                depth[n.name] = min(depth[s] for s in succs[n.name]) - 1
        if self.group_out in block:
            depth[self.group_out.name] = max(depth.values()) + 1
        min_depth = min(depth.values())
        for n in block:
            depth[n.name] -= min_depth

        # 2. route long links through reroutes (one station after the source, one before the target)
        if self.reroutes:
            for link in list(block_links()):
                a, b = link.from_node, link.to_node
                span = depth[b.name] - depth[a.name]
                if span < 2 or a.bl_idname == "NodeReroute" or b.bl_idname == "NodeReroute":
                    continue
                from_sock, to_sock = link.from_socket, link.to_socket
                self.tree.links.remove(link)
                prev_sock = from_sock
                stations = [depth[a.name] + 1]
                if span >= 3:
                    stations.append(depth[b.name] - 1)
                for col in stations:
                    rr = self.tree.nodes.new("NodeReroute")
                    rr.name = f"→ {from_sock.name}"
                    rr.label = from_sock.name if col == stations[0] else ""
                    rr.parent = a.parent if a.parent == b.parent else b.parent
                    self.tree.links.new(prev_sock, rr.inputs[0])
                    prev_sock = rr.outputs[0]
                    block.append(rr)
                    names.add(rr.name)
                    by_name[rr.name] = rr
                    depth[rr.name] = col
                    preds[rr.name] = []
                    succs[rr.name] = []
                self.tree.links.new(prev_sock, to_sock)
            preds = {n.name: [] for n in block}
            succs = {n.name: [] for n in block}
            for link in block_links():
                preds[link.to_node.name].append(link.from_node.name)
                succs[link.from_node.name].append(link.to_node.name)

        columns: dict[int, list] = {}
        for n in block:
            columns.setdefault(depth[n.name], []).append(n)

        # 3. order per column: geometry chain first, then barycenter of predecessors
        rank: dict[str, float] = {}
        link_by_target: dict[str, list] = {}
        for link in block_links():
            link_by_target.setdefault(link.to_node.name, []).append(link)

        def primary_link(node):
            links = link_by_target.get(node.name, [])
            if not links:
                return None
            geo = [lk for lk in links if lk.to_socket.bl_idname == "NodeSocketGeometry"]
            if geo:
                return geo[0]
            return min(links, key=lambda lk: _socket_index(lk.to_node, lk.to_socket))

        for col in sorted(columns):
            members = columns[col]
            for i, n in enumerate(members):
                linked = [rank[p] for p in preds[n.name] if p in rank]
                base = sum(linked) / len(linked) if linked else float(i) + 100.0
                pl = primary_link(n)
                if pl is not None and pl.to_socket.bl_idname == "NodeSocketGeometry":
                    base -= 0.5
                rank[n.name] = base
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

        # 4. coordinates column by column; desired y keeps the primary link horizontal
        x = x_start
        col_x: dict[int, float] = {}
        for col in sorted(columns):
            members = columns[col]
            col_x[col] = x
            desired: dict[str, float] = {}
            for n in members:
                pl = primary_link(n)
                if pl is not None and pl.from_node.name in top:
                    src = pl.from_node
                    src_sock_y = top[src.name] - _socket_offset(src, pl.from_socket, output=True)
                    desired[n.name] = src_sock_y + _socket_offset(n, pl.to_socket, output=False)
                else:
                    desired[n.name] = None
            placed: list = []
            y_cursor = None
            ordered = sorted(members, key=lambda n: rank[n.name])
            for n in ordered:
                want = desired[n.name]
                if want is None:
                    want = 0.0 if y_cursor is None else y_cursor
                y = want if y_cursor is None else min(want, y_cursor)
                top[n.name] = y
                y_cursor = y - _node_height(n) - ROW_GAP
                placed.append(n)

            col_width = max(_node_width(n) for n in members)
            for n in members:
                n.location_absolute = (
                    x + (col_width - _node_width(n)) / 2 if n.bl_idname == "NodeReroute" else x,
                    top[n.name],
                )
            x += col_width + COLUMN_GAP
        # right-align sources (Group Input copies, constants) to their column
        for n in block:
            if not preds[n.name] and succs[n.name] and n.bl_idname != "NodeReroute":
                col = depth[n.name]
                col_width = max(_node_width(m) for m in columns[col])
                n.location_absolute = (col_x[col] + col_width - _node_width(n), top[n.name])
        return x - x_start - COLUMN_GAP + (2 * FRAME_PAD if any(n.parent for n in block) else 0)


def _socket_index(node, socket) -> int:
    sockets = node.outputs if socket.is_output else node.inputs
    return next((i for i, s in enumerate(sockets) if s == socket), 0)


def _socket_offset(node, socket, *, output: bool) -> float:
    """Distance of the socket centre from the node top (estimated like Blender draws it)."""
    if node.bl_idname == "NodeReroute":
        return REROUTE_SIZE / 2
    if node.hide:
        return COLLAPSED_H / 2
    outputs = [s for s in node.outputs if s.enabled and not s.hide]
    inputs = [s for s in node.inputs if s.enabled and not s.hide]
    if output:
        idx = next((i for i, s in enumerate(outputs) if s == socket), 0)
        return HEADER_H + SOCKET_H * idx + SOCKET_H / 2
    props = sum(1 for p in node.bl_rna.properties if p.identifier in PROP_IDS)
    idx = next((i for i, s in enumerate(inputs) if s == socket), 0)
    return HEADER_H + SOCKET_H * len(outputs) + PROP_H * props + SOCKET_H * idx + SOCKET_H / 2


def _collapsed_width(node) -> float:
    text = node.label or node.name
    return max(90.0, min(220.0, 7.0 * len(text) + 50.0))


def _node_width(node: bpy.types.Node) -> float:
    if node.bl_idname == "NodeReroute":
        return REROUTE_SIZE
    return float(node.width)


def _node_height(node: bpy.types.Node) -> float:
    if node.bl_idname == "NodeReroute":
        return REROUTE_SIZE
    if node.hide:
        return COLLAPSED_H
    visible = [s for s in node.inputs if s.enabled and not s.hide] + [
        s for s in node.outputs if s.enabled and not s.hide
    ]
    props = sum(1 for p in node.bl_rna.properties if p.identifier in PROP_IDS)
    extra = 24 if node.bl_idname in ("GeometryNodeInputNamedAttribute", "GeometryNodeStringToCurves") else 0
    return HEADER_H + SOCKET_H * len(visible) + PROP_H * props + extra + 6


def builtin_font() -> bpy.types.VectorFont:
    """Blender's built-in font (Bfont Regular); loaded on demand."""
    font = bpy.data.fonts.get("Bfont Regular")
    if font is None:
        font = bpy.data.fonts.load("<builtin>")
    # A reference from a socket default does not count as a user in 5.2.0: without a fake user the font is lost on load.
    font.use_fake_user = True
    return font


def iter_trees(names: Iterable[str]):
    for name in names:
        yield bpy.data.node_groups[name]
