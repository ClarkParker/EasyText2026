"""Text-Quelle: Zeilen joinen, String to Curves mit allen Optionen, Zeichenindex speichern, Glyphen realisieren."""

from ..core import GroupBuilder, builtin_font
from . import et_lines_join

NAME = ".ET Text Source"


def build():
    g = GroupBuilder(NAME, description="Bis zu vier Zeilen Text als realisierte Glyphenkurven mit et_char_index.")
    g.input("Text", "string", "Easy Text")
    for i in (2, 3, 4):
        g.input(f"Zeile {i}", "string", "")
    g.input("Font", "font", builtin_font())
    g.input("Größe", "float", 1.0, min=0.001, max=100.0, subtype="DISTANCE")
    g.input("Ausrichtung X", "menu")
    g.input("Ausrichtung Y", "menu")
    g.input("Pivot", "menu")
    g.input("Zeichenabstand", "float", 1.0, min=0.0, max=10.0)
    g.input("Wortabstand", "float", 1.0, min=0.0, max=10.0)
    g.input("Zeilenabstand", "float", 1.0, min=0.0, max=10.0)
    g.input("Breite", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE")
    g.input("Höhe", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE")
    g.input("Überlauf", "menu")
    g.output("Curves", "geometry")
    g.output("Zeichen", "int", description="Zeichenzahl des zusammengesetzten Textes.")
    for name, value in (
        ("Ausrichtung X", "Center"),
        ("Ausrichtung Y", "Middle"),
        ("Pivot", "Midpoint"),
        ("Überlauf", "Overflow"),
    ):
        g.menu_default(name, value)

    with g.frame("Zeilen"):
        gi = g.inputs("Text", "Zeile 2", "Zeile 3", "Zeile 4", label="Zeilen")
        joined = g.group(
            et_lines_join.NAME,
            "Lines Join",
            inputs={f"Line {i}": gi[n] for i, n in enumerate(("Text", "Zeile 2", "Zeile 3", "Zeile 4"), start=1)},
        )["String"]
        text_len = g.node("FunctionNodeStringLength", "Text Length", inputs={"String": joined})["Length"]

    with g.frame("Font"):
        gi = g.inputs("Font")
        # Blender 5.2.0 übernimmt Font-Defaults des Interfaces nicht in den Modifier: Ersatzwert im Baum.
        font = g.fallback("FONT", gi["Font"], builtin_font(), name="Font")

    with g.frame("Satz"):
        gi = g.inputs(
            "Größe",
            "Ausrichtung X",
            "Ausrichtung Y",
            "Pivot",
            "Zeichenabstand",
            "Wortabstand",
            "Zeilenabstand",
            "Breite",
            "Höhe",
            "Überlauf",
            label="Typografie",
        )
        curves_inst = g.node(
            "GeometryNodeStringToCurves",
            "String to Curves",
            inputs={
                "String": joined,
                "Size": gi["Größe"],
                "Font": font,
                "Align X": gi["Ausrichtung X"],
                "Align Y": gi["Ausrichtung Y"],
                "Pivot Point": gi["Pivot"],
                "Character Spacing": gi["Zeichenabstand"],
                "Word Spacing": gi["Wortabstand"],
                "Line Spacing": gi["Zeilenabstand"],
                "Overflow": gi["Überlauf"],
                "Text Box Width": gi["Breite"],
                "Text Box Height": gi["Höhe"],
            },
        )

    with g.frame("Instanzen"):
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
    g.set_output("Curves", curves)
    g.set_output("Zeichen", text_len)
    return g.finish()
