"""Standard-Materialien, die als Defaults an den Material-Inputs der Gruppen hängen (CC0, Teil der Asset-Datei)."""

import bpy

DEFAULTS = {
    # Name: (Base Color RGBA, Roughness, Metallic)
    "ET Front": ((0.85, 0.85, 0.85, 1.0), 0.35, 0.0),
    "ET Side": ((0.35, 0.35, 0.38, 1.0), 0.45, 0.0),
    "ET Bevel": ((0.95, 0.75, 0.25, 1.0), 0.25, 0.6),
}


def ensure(name: str) -> bpy.types.Material:
    color, roughness, metallic = DEFAULTS[name]
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = next((n for n in tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in tree.nodes if n.bl_idname == "ShaderNodeOutputMaterial"), None)
        if out is None:
            out = tree.nodes.new("ShaderNodeOutputMaterial")
        tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = color
    mat.use_fake_user = True  # Socket-Defaults zählen nicht als Nutzer; sonst fehlen die Materialien nach dem Laden.
    return mat


def ensure_all() -> dict[str, bpy.types.Material]:
    return {name: ensure(name) for name in DEFAULTS}
