# Easy Text 2026 (v3)

Geometry-Nodes-Typografie und Text-Animation für **Blender 5.2 LTS**: Node-Group-Assets
(funktionieren als Modifier ohne Add-on) plus eine optionale Extension für Font-Picker,
mehrzeiligen Text, Presets sowie Kamera- und Licht-Rigs.

Status: Phase 1, erste Node-Gruppe `ET Text Mesh` (Text → sauberes Mesh mit Extrusion, Bevel, Materialien, UVs).
Analyse der Vorgängerversion: `docs/01-analyse-v2.1.md`, Zielbild: `docs/02-zielbild-v3.md`,
Entwicklungsregeln und API-Fallen: `docs/03-entwicklung.md`, Architektur: `docs/04-architektur-v3.md`.

## Testen in Blender (5.2 LTS)

1. `assets/easytext_v3.blend` herunterladen (aus dem Repo oder als CI-Artefakt).
2. In einer eigenen Datei: File → Append → `easytext_v3.blend` → NodeTree → `ET Text Mesh`.
   Alternativ den Ordner `assets/` in den Preferences als Asset-Bibliothek eintragen; die Gruppe erscheint dann
   im Add-Modifier-Menü unter "Easy Text".
3. Ein beliebiges Mesh-Objekt (oder seit 5.2 ein Empty) anlegen, Modifier "Geometry Nodes" hinzufügen, Gruppe `ET Text Mesh` wählen.
4. Panels im Modifier: Text (4 Zeilen), Typografie (Font-Socket, Größe, Ausrichtung, Abstände, Textbox),
   Kontur (Auflösung, Vereinfachen, Füllung), Form (Tiefe, Bevel, Glättungswinkel), Material, UV, Ausgabe.

Was die Gruppe garantiert (headless geprüft): geschlossenes, manifoldes Mesh ohne doppelte Vertices; Deckflächen als
N-Gons oder Dreiecke; Seiten als Quads; Bevel als Quads; UV-Map `UVMap` mit planaren Deckflächen und einer
durchgehenden, unverzerrten UV-Bahn für Seiten und Bevel (U = Konturlänge, V = Bogenlänge über Rück-Bevel, Seite, Front-Bevel);
Materialien in den Slots Front/Seite/Bevel; Warnungen bei leerem Text und zu breitem Bevel.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `src/easytext_build/` | Builder: erzeugt alle Node-Gruppen per Skript (Quelle der Wahrheit). |
| `src/easytext_build/groups/` | Eine Datei pro Node-Gruppe. |
| `assets/easytext_v3.blend` | Gebaute Asset-Bibliothek (nie von Hand editieren). |
| `assets/blender_assets.cats.txt` | Asset-Katalog. |
| `assets/snapshots/*.json` | Textuelle Abbilder der Node-Gruppen für Diffs und Reviews. |
| `tools/dump_blend.py` | Liest eine .blend ohne Blender aus (für Referenzdateien). |
| `docs/` | Analyse, Zielbild, Entwicklungsregeln, Referenz-Dumps von v2.1. |

## Bauen

Benötigt Python 3.13 (wie Blender 5.2). Das `bpy`-Wheel ist Blender als Python-Modul (~400 MB).

```bash
python -m pip install -e ".[dev,bpy]"
python -m easytext_build.build     # baut assets/easytext_v3.blend, Katalog und Snapshots
python -m easytext_build.smoke     # lädt die Datei, hängt den Modifier an, prüft das Ergebnis
pytest                             # Tests ohne Blender
```

Alternativ mit einer Blender-Installation:

```bash
blender -b --python-expr "import sys; sys.path.insert(0, 'src'); import easytext_build.build as b; b.main()"
```

## Lizenz

Code (Builder, Extension, Werkzeuge): GPL-3.0-or-later, siehe `LICENSE`.
Node-Assets und Beispielszenen unter `assets/`: CC0 1.0, siehe `assets/LICENSE`.
