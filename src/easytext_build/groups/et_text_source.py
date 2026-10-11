"""Text source ("Text Settings" on the control panel): String to Curves with every option exposed in panels,
the character index stored per glyph, glyphs realized. Takes the already joined text (see .ET Lines Join)."""

from ..core import GroupBuilder, builtin_font, heading

NAME = ".ET Text Source"
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
    g = GroupBuilder(
        NAME,
        description="Text as realized glyph curves with et_char_index; font, alignment, spacing and text box.",
        default_width=300,
    )
    g.input("Text", "string", "Easy Text", description="The text; line breaks start new lines.")
    with g.panel(heading("Font")):
        g.input("Font", "font", builtin_font(), description="Font data-block.")
        g.input("Size", "float", 1.0, min=0.001, max=100.0, subtype="DISTANCE", description="Font size.")
    with g.panel(heading("Alignment")):
        g.input("Align X", "menu", description="Horizontal alignment of the lines.")
        g.input("Align Y", "menu", description="Vertical alignment of the text block.")
        g.input("Pivot", "menu", description="Origin of the text block.")
    with g.panel(heading("Spacing")):
        g.input("Character Spacing", "float", 1.0, min=0.0, max=10.0, description="Spacing factor between characters.")
        g.input("Word Spacing", "float", 1.0, min=0.0, max=10.0, description="Spacing factor between words.")
        g.input("Line Spacing", "float", 1.0, min=0.0, max=10.0, description="Spacing factor between lines.")
    with g.panel(heading("Text Box"), description="Wrapping and overflow.", default_closed=True):
        g.input("Box Width", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = no wrapping.")
        g.input("Box Height", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = unlimited.")
        g.input("Overflow", "menu", description="What happens when the text does not fit the box.")
    g.output("Curves", "geometry")
    g.output("Character Count", "int", description="Number of characters in the text.")
    for name, value in (("Align X", "Center"), ("Align Y", "Middle"), ("Pivot", "Midpoint"), ("Overflow", "Overflow")):
        g.menu_default(name, value)

    with g.frame("Text"):
        gi = g.inputs("Text")
        text = gi["Text"]
        char_count = g.node("FunctionNodeStringLength", "Character Count", inputs={"String": text})["Length"]

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
                "String": text,
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
        # One instance per glyph: character, word and line index plus the typographic pivot travel with the
        # points through realize, fill and extrude (see .ET Solid) and drive the per-letter animation.
        index = g.node("GeometryNodeInputIndex", "Index")[0]
        inst = g.store(
            curves_inst["Curve Instances"],
            "et_char_index",
            index,
            domain="INSTANCE",
            data_type="INT",
            name="Store et_char_index",
        )[0]
        inst = g.store(
            inst, "et_word_index", curves_inst["Word"], domain="INSTANCE", data_type="INT", name="Store et_word_index"
        )[0]
        inst = g.store(
            inst, "et_line_index", curves_inst["Line"], domain="INSTANCE", data_type="INT", name="Store et_line_index"
        )[0]
        # String to Curves gives the pivot relative to the glyph; the instance position places the glyph.
        glyph_origin = g.node("GeometryNodeInputPosition", "Glyph Origin")[0]
        pivot = g.vmath("ADD", glyph_origin, curves_inst["Pivot Point"], name="Glyph Pivot")[0]
        inst = g.store(inst, "et_pivot", pivot, domain="INSTANCE", data_type="FLOAT_VECTOR", name="Store et_pivot")[0]
        curves = g.node("GeometryNodeRealizeInstances", "Realize Glyphs", inputs={"Geometry": inst})[0]

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
