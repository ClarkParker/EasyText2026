"""Convert Blender values into JSON-friendly, deterministic Python values (no bpy import)."""

FLOAT_DIGITS = 5


def convert(value):
    """Round floats, vectors/colors/matrices to lists, IDs to names."""
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        rounded = round(value, FLOAT_DIGITS)
        return 0.0 if rounded == 0 else rounded
    name = getattr(value, "name", None)
    if name is not None and hasattr(value, "bl_rna") and not hasattr(value, "__len__"):
        return {"id": name, "type": type(value).__name__}
    if hasattr(value, "__len__"):
        return [convert(v) for v in value]
    return str(value)
