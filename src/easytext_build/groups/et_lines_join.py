"""Join up to four text lines with line breaks; empty lines are skipped."""

from ..core import GroupBuilder

NAME = ".ET Lines Join"


def build():
    g = GroupBuilder(NAME, description="Four lines to one string with line breaks; empty lines are dropped.")
    for i in range(1, 5):
        g.input(f"Line {i}", "string", "", hide_value=True)
    g.output("String", "string")

    with g.frame("Join Lines"):
        line_break = g.node("FunctionNodeInputSpecialCharacters", "Line Break")["Line Break"]
        gi = g.inputs("Line 1", "Line 2", "Line 3", "Line 4", label="Lines")
        parts = [gi["Line 1"]]
        for i in (2, 3, 4):
            line = gi[f"Line {i}"]
            length = g.node("FunctionNodeStringLength", f"Length {i}", inputs={"String": line})["Length"]
            has_text = g.compare("GREATER_THAN", length, 0, data_type="INT", name=f"Has Text {i}")
            with_break = g.node(
                "GeometryNodeStringJoin", f"Break + Line {i}", inputs={"Delimiter": "", "Strings": [line_break, line]}
            )
            parts.append(g.switch("STRING", has_text[0], "", with_break["String"], name=f"Use Line {i}")[0])
        joined = g.node("GeometryNodeStringJoin", "Join", inputs={"Delimiter": "", "Strings": parts})
        trimmed = g.node(
            "FunctionNodeTrimString",
            "Trim",
            inputs={"String": joined["String"], "Whitespace": True, "Start": True, "End": True},
        )
    g.set_output("String", trimmed["String"])
    return g.finish()
