"""Text source: join lines, String to Curves with every option exposed, store the character index, realize glyphs."""

from ..core import GroupBuilder, builtin_font
from . import et_lines_join

NAME = ".ET Text Source"
LINE_INPUTS = ("Text", "Line 2", "Line 3", "Line 4")
TYPOGRAPHY_INPUTS = (
    "Font",
    "Size",
    "Align X",
    "Align Y",
    "Pivot",
    "Character Spacing",
    "Word Spacing",
    "Line Spacing",
    "Box Width",
    "Box Height",
    "Overflow",
)


def build():
    g = GroupBuilder(NAME, description="Up to four lines of text as realized glyph curves with et_char_index.")
    g.input("Text", "string", "Easy Text")
    for i in (2, 3, 4):
        g.input(f"Line {i}", "string", "")
    g.input("Font", "font", builtin_font())
    g.input("Size", "float", 1.0, min=0.001, max=100.0, subtype="DISTANCE")
    g.input("Align X", "menu")
    g.input("Align Y", "menu")
    g.input("Pivot", "menu")
    g.input("Character Spacing", "float", 1.0, min=0.0, max=10.0)
    g.input("Word Spacing", "float", 1.0, min=0.0, max=10.0)
    g.input("Line Spacing", "float", 1.0, min=0.0, max=10.0)
    g.input("Box Width", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE")
    g.input("Box Height", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE")
    g.input("Overflow", "menu")
    g.output("Curves", "geometry")
    g.output("Character Count", "int", description="Number of characters in the joined text.")
    for name, value in (("Align X", "Center"), ("Align Y", "Middle"), ("Pivot", "Midpoint"), ("Overflow", "Overflow")):
        g.menu_default(name, value)

    with g.frame("Lines"):
        gi = g.inputs(*LINE_INPUTS, label="Lines")
        joined = g.group(
            et_lines_join.NAME, "Lines Join", inputs={f"Line {i}": gi[n] for i, n in enumerate(LINE_INPUTS, start=1)}
        )["String"]
        char_count = g.node("FunctionNodeStringLength", "Character Count", inputs={"String": joined})["Length"]

    with g.frame("Font"):
        gi = g.inputs("Font")
        # Blender 5.2.0 does not copy interface font defaults into the modifier: fall back inside the tree.
        font = g.fallback("FONT", gi["Font"], builtin_font(), name="Font")

    with g.frame("Typeset"):
        gi = g.inputs(*TYPOGRAPHY_INPUTS[1:], label="Typography")
        curves_inst = g.node(
            "GeometryNodeStringToCurves",
            "String to Curves",
            inputs={
                "String": joined,
                "Size": gi["Size"],
                "Font": font,
                "Align X": gi["Align X"],
                "Align Y": gi["Align Y"],
                "Pivot Point": gi["Pivot"],
                "Character Spacing": gi["Character Spacing"],
                "Word Spacing": gi["Word Spacing"],
                "Line Spacing": gi["Line Spacing"],
                "Overflow": gi["Overflow"],
                "Text Box Width": gi["Box Width"],
                "Text Box Height": gi["Box Height"],
            },
        )

    with g.frame("Instances"):
        index = g.node("GeometryNodeInputIndex", "Index")[0]
        with_char = g.store(
            curves_inst["Curve Instances"],
            "et_char_index",
            index,
            domain="INSTANCE",
            data_type="INT",
            name="Store et_char_index",
        )
        curves = g.node("GeometryNodeRealizeInstances", "Realize Glyphs", inputs={"Geometry": with_char[0]})[0]

    with g.frame("Warning"):
        # Shown on the modifier (warnings of nested groups propagate). The pass-through switch only makes sure
        # the Warning node is evaluated.
        no_text = g.compare("EQUAL", char_count, 0, data_type="INT", name="No Text")[0]
        shown = g.node(
            "GeometryNodeWarning",
            "Warn Empty",
            inputs={"Show": no_text, "Message": "No text."},
            props={"warning_type": "WARNING"},
        )["Show"]
        curves = g.switch("GEOMETRY", shown, curves, curves, name="Curves")[0]
    g.set_output("Curves", curves)
    g.set_output("Character Count", char_count)
    return g.finish()
