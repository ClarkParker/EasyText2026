# Easy Text Geometry Node – Analyse der Version 2.1 (Blender 3.2)

Stand: 2026-10-10. Grundlage: die hochgeladene Datei `easy-text-geometry-node.blend`
(zstd-komprimiert, Header `BLENDER-v302`, also gespeichert mit Blender 3.2 aus dem Jahr 2022).
Die Datei wurde ohne Blender mit einem eigenen Parser ausgelesen
(`tools/dump_blend.py`, Rohdumps in `docs/reference/v2.1-dump/`).

## 1. Inhalt der Datei

| Block | Name | Bemerkung |
|---|---|---|
| Scene | `upload` | 1920x1080, 24 fps, Frame 1–250, Engine `BLENDER_EEVEE` (Legacy-EEVEE). **Keine Kamera, kein World, keine Lichter.** |
| Object | `Easy Text Geometry Node` | Mesh `Cube.001` (8 Verts, nur Träger), Scale 0.839. Modifier-Stack: Geometry Nodes → Bevel → SimpleDeform (deaktiviert). |
| NodeTree | `EasyTextGeometryNodeV2.1` | Haupt-Gruppe, 17 Nodes. Nur ein Input (Geometry), **keine exponierten Parameter**. |
| NodeTree | `Geo_LineCombinerNodeGroup` | 56 Nodes (43 Reroutes). Fügt bis zu 4 Textzeilen mit Zeilenumbruch zusammen. |
| NodeTree | `LogicBoardNodeGroup` | 72 Nodes (59 Reroutes, 10 Switches). Reines Boolean-Logikbrett für "1/2/3/4 Zeilen". |
| NodeTree | `Geo_MeshGenerationNodeGroup` | 119 Nodes (60 Reroutes, 11 Switches). 33 Group-Inputs. Mesh, Material, Animation, Bevel-Platte. |
| NodeTree | `Tex_NoiseNodeGroup` | Shader-Gruppe (Noise → Bright/Contrast → Mix → Bump). |
| Material | `Text Top`, `Text Side` | Principled BSDF (metallic 1.0) mit Noise-Rauheit und Bump. Rot / Grün. |
| VFont | `Monoton Regular` | gepackt (Google Fonts, SIL OFL). |
| Text | `EditText`, `ExportMesh` | je ein Satz Bedienhinweis, als Notiz an Frames gehängt. |
| Action | `Geo_MeshGenerationNodeGroupAction` | ein einzelner Keyframe (Frame 96) auf `Switch.005` in der Mesh-Gruppe. |

Nodes gesamt: 270 in den Geometry-Gruppen, davon 166 Reroutes (61 %).

## 2. Datenfluss (so wie v2.1 arbeitet)

```
String ×4 (fest: "Easy", "Text", "Geometry", "Node")
   └─> Line Combiner  (4 Bool-Schalter "1/2/3/4 Lines of text" → Logic Board → Join Strings mit Line Break)
         └─> String to Curves  (Font Monoton, Size 0.9, Align X = Center, Align Y = Middle, Line Spacing 0.8)
               └─> "Curve Instances" (eine Instanz pro Zeichen)
                     └─> Mesh Generation
                           ├─ Resample Curve (Evaluated) → Fill Curve (N-Gons) → Extrude Mesh (Faces) → Flip Faces (Boden)
                           ├─ Join → Realize Instances → Set Material (Top / Side) → Merge by Distance → Set Shade Smooth
                           ├─ Animation: Position → Separate XYZ → ×"Animation Driver x|y|z" → Float Curve → Scale Instances (3×) → Rotate Instances
                           └─ Bevel-Platte: Grid (Subdivision bis 2000²) → Geometry Proximity zum Text → Map Range → Set Position (Z) → Material-Shift
                                 └─> Realize Instances → Group Output
   └─> Objekt-Modifier: Bevel (Kanten) → SimpleDeform (aus)
```

## 3. Was v2.1 kann

- Bis zu 4 Textzeilen, ein Font, Größe, Zeichen-/Wort-/Zeilenabstand, Textbox-Breite.
- Extrusion mit getrenntem Top- und Seiten-Material, Shade Smooth, Merge by Distance.
- Eine "Buchstaben-Bounce"-Animation: pro Achse an/aus, invertieren, Stärke 0–1, Easing über drei Float-Curves,
  Treiber ist ein vom Nutzer per Hand zu animierender Vektor ("Animation Driver x|y|z").
- Eine globale Rotation aller Zeichen-Instanzen.
- Eine "Beveled Plate" (Grundplatte mit Wulst um die Buchstaben) über Proximity auf einem dichten Grid.

## 4. Schwachstellen (sortiert nach Gewicht)

1. **Kein Modifier-UI.** Die Hauptgruppe exponiert nichts. Die Notiz in der Datei sagt wörtlich: "To edit your text ... open a Geometry Node Editor." Jeder Parameter wird im Node-Editor auf den Gruppen-Nodes gesetzt. Für Nutzer ist das die größte Hürde.
2. **Überschriften als Fake-Sockets.** Weil Blender 3.2 keine Panels kannte, sind 8 der 33 Inputs leere Float-Sockets mit Namen wie `=========General Settings=========` oder `^^^^^^^!CAREFULL OVER 1000!^^^^^^^`. Das ist genau das, was Interface-Panels (seit 4.0) und der Warning-Node ersetzen.
3. **Mehrzeiliger Text ist ein Logik-Umweg.** Vier feste String-Nodes, vier Bool-Schalter und ein 72-Node-"Logic Board" aus verketteten Switches nur, um zu entscheiden, wie viele Zeilen gejoint werden. Das ist mit einem Integer "Zeilen" oder Menu Switch (4.1) plus Join Strings ein Dutzend Nodes.
4. **Reroute-Spaghetti.** 61 % der Nodes sind Reroutes. Die Gruppen sind so faktisch nicht wartbar und nicht diff-bar.
5. **Bevel-Platte skaliert quadratisch.** Grid mit `Subdivision²` Vertices (Default 300² = 90 000, erlaubt bis 2000² = 4 Mio.) plus Geometry Proximity pro Vertex. Daher die "Danger"-Labels. Heute macht man das mit SDF-Volume-Grids (Mesh to SDF Grid → Grid to Mesh) oder Mesh Boolean und bekommt eine echte Rundung bei konstanten Kosten.
6. **Animation ist nicht zeitbasiert und nicht selektiv.** Kein Scene Time, kein Typewriter, keine Auswahl nach Zeichen/Wort/Zeile, kein Offset/Stagger, kein Ease-In/Out pro Zeichen. Der Nutzer muss einen Vektor keyframen. Die "Bounce"-Skalierung ist von der Weltposition der Buchstaben abhängig (Position → Separate XYZ), nicht vom Zeichenindex, verhält sich also bei Verschieben des Objekts anders.
7. **Streu-Keyframe in der Node-Gruppe.** Der einzige Keyframe (Frame 96) liegt als Action auf `Geo_MeshGenerationNodeGroup`, also auf der Gruppe selbst. Jeder, der die Gruppe appendet, bekommt diese Animation mit.
8. **Font ist eine Node-Eigenschaft, kein Socket.** `String to Curves` trägt den Font als Node-Property; ein Font-Wechsel ist im Modifier-UI nicht möglich. (Das gilt auch in 4.x/5.x, siehe Teil 2.)
9. **Materialien sind Legacy-EEVEE / Principled 3.x.** Sockets wie `Subsurface Color`, `Specular`, `Clearcoat` existieren seit 4.0 anders (Versioning fängt es ab, aber man sollte neu aufbauen). Kein World, kein Licht, keine Kamera: das Rendering ist nicht Teil des Pakets, obwohl das Ziel von v3 ist.
10. **Drei Realize-Instances-Schritte**, Merge by Distance auf dem Gesamtmesh und Resample "Evaluated" auf allen Glyphen: funktioniert, kostet aber bei langen Texten unnötig.
11. **Kleinigkeiten.** Typos in Socket-Namen (`Bevel With`, `Bevel Hight`), keine Tooltips/Descriptions, keine Min/Max an den meisten Floats, `Shade Smooth` hat `default_attribute_name = "1"` (Zufallswert).

## 5. Was aus v2.1 übernommen werden sollte

- Das Grundprinzip **"String to Curves → Curve Instances pro Zeichen → Fill → Extrude → am Ende Realize"** ist richtig und bleibt der Kern. Instanzen pro Zeichen sind die Basis für jede Per-Character-Animation.
- Getrenntes Top-/Side-Material über die `Top`/`Side`-Selektionen von Extrude Mesh.
- Die Idee eines Easing über Float Curves (in v3 als Menü mit festen Easings plus optionaler eigener Kurve).
- Die Idee einer Grundplatte, aber anders gebaut.
- Der Font Monoton (OFL) als Beispielfont.

