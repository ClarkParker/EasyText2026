"""Deterministische JSON-Abbilder von Node-Gruppen für Diffs und Reviews."""

from __future__ import annotations

from .values import convert

SOCKET_FIELDS = (
    "description",
    "hide_value",
    "hide_in_modifier",
    "default_value",
    "min_value",
    "max_value",
    "subtype",
    "structure_type",
    "default_input",
    "is_panel_toggle",
    "default_attribute_name",
    "attribute_domain",
    "layer_selection_field",
    "menu_expanded",
    "optional_label",
)
NODE_FIELDS = ("label", "mute", "hide", "width")
SKIP_PROP_TYPES = {"COLLECTION"}


def _base_node_props():
    import bpy

    return {p.identifier for p in bpy.types.Node.bl_rna.properties}


def interface_to_list(tree) -> list[dict]:
    items = []
    for item in tree.interface.items_tree:
        parent = item.parent
        entry = {
            "item_type": item.item_type,
            "name": item.name,
            "parent": parent.name if parent is not None and parent.name else None,
        }
        if item.item_type == "PANEL":
            entry["description"] = item.description
            entry["default_closed"] = item.default_closed
        else:
            entry["in_out"] = item.in_out
            entry["socket_type"] = item.socket_type
            entry["identifier"] = item.identifier
            for field in SOCKET_FIELDS:
                if hasattr(item, field):
                    entry[field] = convert(getattr(item, field))
        items.append(entry)
    return items


def node_to_dict(node, base_props: set[str]) -> dict:
    entry = {
        "idname": node.bl_idname,
        "name": node.name,
        "location": [round(node.location.x), round(node.location.y)],
        "parent": node.parent.name if node.parent else None,
    }
    for field in NODE_FIELDS:
        entry[field] = convert(getattr(node, field))
    props = {}
    for prop in node.bl_rna.properties:
        pid = prop.identifier
        if pid in base_props or prop.type in SKIP_PROP_TYPES or prop.is_readonly:
            continue
        value = getattr(node, pid)
        if prop.type == "POINTER":
            if value is None:
                continue
            value = convert(value) if hasattr(value, "name") else str(value)
        else:
            value = convert(value)
        props[pid] = value
    if props:
        entry["props"] = props
    inputs = {}
    for sock in node.inputs:
        if not sock.enabled:
            continue
        sock_entry = {"name": sock.name}
        if sock.is_linked:
            sock_entry["linked"] = True
        elif hasattr(sock, "default_value"):
            sock_entry["value"] = convert(sock.default_value)
        if sock.hide:
            sock_entry["hide"] = True
        inputs[sock.identifier] = sock_entry
    entry["inputs"] = inputs
    entry["outputs"] = [s.identifier for s in node.outputs if s.enabled]
    return entry


def tree_to_dict(tree) -> dict:
    base_props = _base_node_props()
    flags = {}
    for flag in ("is_modifier", "is_tool", "color_tag", "default_group_node_width"):
        if hasattr(tree, flag):
            flags[flag] = convert(getattr(tree, flag))
    links = sorted(
        [
            [link.from_node.name, link.from_socket.identifier, link.to_node.name, link.to_socket.identifier]
            + (["muted"] if link.is_muted else [])
            for link in tree.links
        ]
    )
    return {
        "name": tree.name,
        "tree_type": tree.bl_idname,
        "description": tree.description,
        "flags": flags,
        "asset_catalog_id": tree.asset_data.catalog_id if tree.asset_data else None,
        "interface": interface_to_list(tree),
        "nodes": [node_to_dict(n, base_props) for n in sorted(tree.nodes, key=lambda n: n.name)],
        "links": links,
    }
