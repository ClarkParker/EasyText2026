# Easy Text 2026 (v3)

Geometry-Nodes-Typografie und Text-Animation für **Blender 5.2 LTS**: Node-Group-Assets
(funktionieren als Modifier ohne Add-on) plus eine optionale Extension für Font-Picker,
mehrzeiligen Text, Presets sowie Kamera- und Licht-Rigs.

Status: Phase 0 (Infrastruktur). Die Analyse der Vorgängerversion und das Zielbild stehen in
`docs/01-analyse-v2.1.md` und `docs/02-zielbild-v3.md`, die Entwicklungsregeln in `docs/03-entwicklung.md`.

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
