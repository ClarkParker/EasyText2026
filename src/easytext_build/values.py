"""Konvertierung von Blender-Werten in JSON-taugliche, deterministische Python-Werte (ohne bpy-Import)."""

FLOAT_DIGITS = 5


def convert(value):
    """Floats runden, Vektoren/Farben/Matrizen zu Listen, IDs zu Namen."""
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
