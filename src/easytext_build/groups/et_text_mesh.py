"""ET Text Mesh: Text -> sauberes, exportfähiges Mesh mit UVs (Kern von Easy Text v3, ohne Animation).

Hauptgruppe mit sechs Frames; die Arbeit steckt in den Untergruppen Outline Clean, Solid, Bevel, Text UV, Finish.
"""

from .. import catalog, materials
from ..core import GroupBuilder, builtin_font
from . import et_bevel, et_finish, et_outline, et_solid, et_text_source, et_uv

NAME = "ET Text Mesh"

COLORS = {
    "Text": (0.22, 0.27, 0.34),
    "Kontur": (0.24, 0.31, 0.29),
    "Körper": (0.33, 0.30, 0.24),
    "Bevel": (0.34, 0.27, 0.24),
    "UV": (0.29, 0.25, 0.34),
    "Ausgabe": (0.26, 0.26, 0.26),
}


def build():
    mats = materials.ensure_all()
    g = GroupBuilder(
        NAME,
        description="Text als sauberes Mesh mit Extrusion, Bevel, Materialien und exportfähigen UVs.",
        is_modifier=True,
        catalog=catalog.TEXT,
        color_tag="GEOMETRY",
        default_width=240,
    )

    # ------------------------------------------------------------------ Interface (Reihenfolge = Identifier)
    with g.panel("Text", description="Bis zu vier Zeilen; leere Zeilen werden übersprungen."):
        g.input("Text", "string", "Easy Text", description="Erste Zeile.")
        for i in (2, 3, 4):
            g.input(f"Zeile {i}", "string", "", description=f"Zeile {i}, optional.")
    with g.panel("Typografie"):
        g.input("Font", "font", builtin_font(), description="Schriftart (Font-Datablock).")
        g.input("Größe", "float", 1.0, min=0.001, max=100.0, subtype="DISTANCE", description="Schriftgröße.")
        g.input("Ausrichtung X", "menu", description="Horizontale Ausrichtung der Zeilen.")
        g.input("Ausrichtung Y", "menu", description="Vertikale Ausrichtung des Textblocks.")
        g.input("Pivot", "menu", description="Ursprung des Textblocks.")
        g.input("Zeichenabstand", "float", 1.0, min=0.0, max=10.0, description="Faktor für den Abstand der Zeichen.")
        g.input("Wortabstand", "float", 1.0, min=0.0, max=10.0, description="Faktor für den Abstand der Wörter.")
        g.input("Zeilenabstand", "float", 1.0, min=0.0, max=10.0, description="Faktor für den Zeilenabstand.")
        with g.panel("Textbox", description="Umbruch und Überlauf.", default_closed=True):
            g.input("Breite", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = kein Umbruch.")
            g.input("Höhe", "float", 0.0, min=0.0, max=1000.0, subtype="DISTANCE", description="0 = unbegrenzt.")
            g.input("Überlauf", "menu", description="Verhalten, wenn der Text nicht in die Box passt.")
    with g.panel("Kontur", description="Qualität der Buchstabenkonturen."):
        g.input("Auflösung", "int", 12, min=1, max=64, description="Punkte pro Kurvensegment.")
        g.input(
            "Vereinfachen",
            "float",
            0.5,
            min=0.0,
            max=10.0,
            description="Punkte entfernen, deren Richtungsänderung unter diesem Winkel (Grad) liegt. 0 = aus.",
        )
        g.input("Füllung", "menu", description="N-Gons oder Dreiecke auf den Deckflächen.")
        g.input("Füllregel", "menu", description="Even-Odd oder Non-Zero für überlappende Konturen.")
    with g.panel("Form"):
        g.input("Tiefe", "float", 0.1, min=0.0, max=10.0, subtype="DISTANCE", description="Extrusionstiefe.")
        with g.panel("Bevel", description="Kantenrundung an Vorder- und Rückseite."):
            g.input("Bevel", "bool", False, panel_toggle=True)
            g.input(
                "Breite",
                "float",
                0.01,
                min=0.0,
                max=1.0,
                subtype="DISTANCE",
                description="Bevel-Breite, maximal halbe Tiefe.",
            )
            g.input("Segmente", "int", 3, min=1, max=16, description="Unterteilungen des Bevels.")
            g.input("Profil", "float", 0.5, min=0.0, max=1.0, subtype="FACTOR", description="0.5 = rund.")
        g.input(
            "Glättungswinkel",
            "float",
            30.0,
            min=0.0,
            max=180.0,
            description="Kanten über diesem Winkel (Grad) bleiben hart.",
        )
    with g.panel("Material"):
        g.input("Vorderseite", "material", mats["ET Front"], description="Auch für die Rückseite.")
        g.input("Seite", "material", mats["ET Side"])
        g.input("Bevelfläche", "material", mats["ET Bevel"])
    with g.panel("UV", description="UV-Map 'UVMap': Deckflächen planar, Seiten und Bevel entlang der Kontur."):
        g.input("UV", "bool", True, panel_toggle=True)
        g.input(
            "Auf Text normieren",
            "bool",
            True,
            description="Deckflächen in 0..1 skalieren; aus = Blender-Einheiten (kachelbar).",
        )
        g.input("Maßstab", "float", 1.0, min=0.0001, max=1000.0, description="Zusätzlicher UV-Faktor.")
    with g.panel("Ausgabe", default_closed=True):
        g.input(
            "Hilfsattribute behalten",
            "bool",
            False,
            description="et_*-Attribute (Zeichenindex, Konturlänge, Flächengruppe) am Mesh lassen.",
        )
    g.output("Geometry", "geometry")
    for name, value in (
        ("Ausrichtung X", "Center"),
        ("Ausrichtung Y", "Middle"),
        ("Pivot", "Midpoint"),
        ("Überlauf", "Overflow"),
        ("Füllung", "N-gons"),
        ("Füllregel", "Even-Odd"),
    ):
        g.menu_default(name, value)

    # Die Textbox-"Breite" wurde vor der Bevel-"Breite" angelegt; lokale Inputs greifen über den Identifier zu.
    box_width_id = [
        i.identifier for i in g.tree.interface.items_tree if i.item_type == "SOCKET" and i.name == "Breite"
    ][0]
    bevel_width_id = [
        i.identifier for i in g.tree.interface.items_tree if i.item_type == "SOCKET" and i.name == "Breite"
    ][1]

    # ------------------------------------------------------------------ Text
    with g.frame("Text", color=COLORS["Text"]):
        names = (
            "Text",
            "Zeile 2",
            "Zeile 3",
            "Zeile 4",
            "Font",
            "Größe",
            "Ausrichtung X",
            "Ausrichtung Y",
            "Pivot",
            "Zeichenabstand",
            "Wortabstand",
            "Zeilenabstand",
            "Höhe",
            "Überlauf",
        )
        gi = g.inputs(*names, label="Text")
        box_width = g.inputs(box_width_id, label="Textbox Breite")[box_width_id]
        source = g.group(et_text_source.NAME, inputs={**{n: gi[n] for n in names}, "Breite": box_width})
        curves, text_len = source["Curves"], source["Zeichen"]

    # ------------------------------------------------------------------ Kontur
    with g.frame("Kontur", color=COLORS["Kontur"]):
        gi = g.inputs("Auflösung", "Vereinfachen")
        outline = g.group(
            et_outline.NAME, inputs={"Curves": curves, "Auflösung": gi["Auflösung"], "Vereinfachen": gi["Vereinfachen"]}
        )["Curves"]

    # ------------------------------------------------------------------ Körper
    with g.frame("Körper", color=COLORS["Körper"]):
        gi = g.inputs("Tiefe", "Füllung", "Füllregel", "Vorderseite")
        solid = g.group(
            et_solid.NAME,
            inputs={
                "Curves": outline,
                "Tiefe": gi["Tiefe"],
                "Füllung": gi["Füllung"],
                "Füllregel": gi["Füllregel"],
                "Front Material": gi["Vorderseite"],
            },
        )["Mesh"]

    # ------------------------------------------------------------------ Bevel
    with g.frame("Bevel", color=COLORS["Bevel"]):
        gi = g.inputs("Bevel", "Segmente", "Profil", "Tiefe", label="Bevel")
        bevel_width = g.inputs(bevel_width_id, label="Bevel Breite")[bevel_width_id]
        bevel = g.group(
            et_bevel.NAME,
            inputs={
                "Mesh": solid,
                "Bevel": gi["Bevel"],
                "Breite": bevel_width,
                "Segmente": gi["Segmente"],
                "Profil": gi["Profil"],
                "Tiefe": gi["Tiefe"],
            },
        )

    # ------------------------------------------------------------------ UV
    with g.frame("UV", color=COLORS["UV"]):
        gi = g.inputs("UV", "Auf Text normieren", "Maßstab", "Tiefe", label="UV")
        with_uv = g.group(
            et_uv.NAME,
            inputs={
                "Mesh": bevel["Mesh"],
                "Tiefe": gi["Tiefe"],
                "Radius": bevel["Radius"],
                "Auf Text normieren": gi["Auf Text normieren"],
                "Maßstab": gi["Maßstab"],
            },
        )["Mesh"]
        mesh = g.switch("GEOMETRY", gi["UV"], bevel["Mesh"], with_uv, name="Use UV")[0]

    # ------------------------------------------------------------------ Ausgabe
    with g.frame("Ausgabe", color=COLORS["Ausgabe"]):
        gi = g.inputs("Seite", "Bevelfläche", "Glättungswinkel", "Hilfsattribute behalten", label="Ausgabe")
        final = g.group(
            et_finish.NAME,
            inputs={
                "Mesh": mesh,
                "Seite": gi["Seite"],
                "Bevelfläche": gi["Bevelfläche"],
                "Glättungswinkel": gi["Glättungswinkel"],
                "Hilfsattribute behalten": gi["Hilfsattribute behalten"],
            },
        )["Mesh"]
        warn_empty = g.node(
            "GeometryNodeWarning",
            "Warn Empty",
            inputs={
                "Show": g.compare("EQUAL", text_len, 0, data_type="INT", name="No Text")[0],
                "Message": "Kein Text.",
            },
            props={"warning_type": "WARNING"},
        )["Show"]
        warn_bevel = g.node(
            "GeometryNodeWarning",
            "Warn Bevel",
            inputs={"Show": bevel["Begrenzt"], "Message": "Bevel-Breite auf halbe Tiefe begrenzt."},
            props={"warning_type": "INFO"},
        )["Show"]
        hook = g.boolean("OR", warn_empty, warn_bevel, name="Warnings")[0]
        out = g.switch("GEOMETRY", hook, final, final, name="Output")[0]
    g.set_output("Geometry", out)
    return g.finish()
