"""Fügt bis zu vier Textzeilen mit Zeilenumbruch zusammen; leere Zeilen werden übersprungen."""

from ..core import GroupBuilder

NAME = ".ET Lines Join"


def build():
    g = GroupBuilder(NAME, description="Vier Zeilen zu einem String mit Zeilenumbrüchen; leere Zeilen entfallen.")
    lines = [g.input(f"Line {i}", "string", "", hide_value=True) for i in range(1, 5)]
    g.output("String", "string")

    line_break = g.node("FunctionNodeInputSpecialCharacters", "Line Break")["Line Break"]
    parts = [lines[0]]
    for i, line in enumerate(lines[1:], start=2):
        length = g.node("FunctionNodeStringLength", f"Length {i}", inputs={"String": line})["Length"]
        has_text = g.compare("GREATER_THAN", length, 0, data_type="INT", name=f"Has Text {i}")
        with_break = g.node(
            "GeometryNodeStringJoin", f"Break + Line {i}", inputs={"Delimiter": "", "Strings": [line_break, line]}
        )
        parts.append(g.switch("STRING", has_text[0], "", with_break["String"], name=f"Use Line {i}")[0])
    joined = g.node("GeometryNodeStringJoin", "Join Lines", inputs={"Delimiter": "", "Strings": parts})
    trimmed = g.node(
        "FunctionNodeTrimString",
        "Trim",
        inputs={"String": joined["String"], "Whitespace": True, "Start": True, "End": True},
    )
    g.set_output("String", trimmed["String"])
    return g.finish()
