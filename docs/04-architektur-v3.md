# Architektur v3 (Entwurf für Phase 1 und 2)

Stand: 2026-10-10. Baut auf `02-zielbild-v3.md` auf; konkretisiert Gruppen, Attribut-Vertrag und Modifier-UI.
Entwurf zur Besprechung, noch nicht umgesetzt.

## 1. Pipeline

```
Text (String, "\n" erlaubt)  ──► ET Text Source ──► Zeichen-Instanzen (Kurven) + Attribute
                                                      │
                                     ET Glyph Mesh:   │  Realize → Fill Curve → Extrude → Mesh Bevel
                                                      │  → Split to Instances (et_char_index)
                                                      ▼
                        Zeichen-Instanzen (Meshes, Pivot bekannt) ──► Selektoren (schreiben et_weight)
                                                      │               ──► Animatoren (lesen et_weight)
                                                      ▼
                                     Realize → Materialien → Shade Smooth → Ausgabe
```

Warum Realize vor dem Fill und danach wieder Split: `Fill Curve` und `Extrude Mesh` arbeiten auf dem
realisierten Mesh in einem Rutsch (schnell, ein Thread-Pool), und `Split to Instances` (4.1) stellt die
Per-Zeichen-Instanzen über das vorher gespeicherte `et_char_index` wieder her. Instanz-Attribute überleben
`Realize Instances` als Punkt-Attribute, also bleiben Pivot und Indizes erhalten. Erst ganz am Ende wird
endgültig realisiert. Das ersetzt die drei Realize-Schritte und den Instanz/Realize-Switch aus v2.1.

## 2. Attribut-Vertrag

Alle Attribute liegen auf der Instanz-Domain der Zeichen-Instanzen (nach dem Fill auf dem Punkt-Domain
und nach dem Split wieder auf Instanzen).

| Attribut | Typ | Quelle | Zweck |
|---|---|---|---|
| `et_char_index` | int | Index der Glyph-Instanz (Leerzeichen erzeugen keine Instanz) | Basis jeder Auswahl, Split-Schlüssel |
| `et_word_index` | int | String to Curves "Word" | Auswahl nach Wörtern |
| `et_line_index` | int | String to Curves "Line" | Auswahl nach Zeilen |
| `et_char_in_word` | int | Accumulate Field (Leading, Group ID = Wort) | Stagger innerhalb eines Wortes |
| `et_char_in_line` | int | Accumulate Field (Leading, Group ID = Zeile) | Stagger innerhalb einer Zeile |
| `et_char_count`, `et_word_count`, `et_line_count` | int (uniform) | Attribute Statistic (Max + 1) | Prozent-Einheiten in Selektoren |
| `et_pivot` | vector | String to Curves "Pivot Point" | Rotation/Skalierung um Grundlinie oder Mitte |
| `et_weight` | float 0..1 | Selektoren | Stärke der Animation pro Element; Default 1 |
| `et_time` | float | ET Time | lokale, normierte Zeit 0..1 pro Element |

Der Python-Shaping-Pfad (v3.1) liefert dieselben Attribute plus `et_glyph_id`; die Animatoren
bleiben unverändert.

## 3. Gruppen-Inventar

| Gruppe | Katalog | Phase | Inhalt |
|---|---|---|---|
| `ET Text` | Easy Text | 1 | Haupt-Modifier für Nutzer ohne Node-Editor. Kapselt Source, Mesh, Material, Ausgabe; ab Phase 2 Animations-Panel mit Preset-Menü. |
| `ET Text Source` | Text | 1 | Zeilen-Join, String to Curves (alle Optionen als Inputs), Attribut-Vertrag. |
| `.ET Lines Join` | intern | 1 | 4 String-Inputs → ein String mit Line Break, leere Zeilen übersprungen (String Length > 0). |
| `ET Glyph Mesh` | Mesh | 1 | Realize → Fill (Mode/Fill Rule) → Extrude → optional Mesh Bevel → Split to Instances; Outputs: Instanzen, Selektionen Front/Side/Bevel als Attribute. |
| `ET Finish` | Mesh | 1 | Realize, Set Material (Front/Side/Bevel), Merge by Distance (optional), Shade Smooth by Angle. |
| `ET Time` | Animators | 2 | Frame (Default-Input SCENE_FRAME), Start, Dauer, Stagger, Reihenfolge (Index/Zufall/Rückwärts/Von der Mitte), Easing-Menü, Loop/Ping-Pong → `et_time`. |
| `ET Select Range` | Selectors | 2 | AE-Modell: Start/End/Offset, Einheit (Prozent/Index), Basis (Zeichen/Wort/Zeile), Form, Ease, Zufall + Seed, Modus → `et_weight`. |
| `ET Select Transition` | Selectors | 2 | Cavalry-Modell: Completion 0..1 + Breite + Richtung → `et_weight`. Kernstück der Reveals. |
| `ET Select Field` | Selectors | 2 | Falloff um Objekt (Box/Kugel/Linear), Invert, Stärke. |
| `ET Select Noise` | Selectors | 2 | Zeit-/raumabhängiges Noise-Gewicht (Wiggly Selector). |
| `ET Select Sound` | Selectors | 2 | Sample Sound Frequencies → Gewicht pro Band oder Index. |
| `ET Animate Transform` | Animators | 2 | Position/Rotation/Scale × `et_weight` um `et_pivot`, Pivot-Modus (Zeichen/Wort/Zeile/Alles). |
| `ET Animate Visibility` | Animators | 2 | Alpha-Attribut (`et_alpha`) für Material, optional Delete Geometry bei 0. |
| `ET Animate Tracking` | Animators | 2 | Zeichen-/Zeilenabstand animiert (Verschiebung entlang Grundlinie). |
| `ET Typewriter` | Animators | 2 | Sichtbare Zeichenanzahl aus `et_time`; Cursor optional. |
| `ET Scramble` | Animators | 2 | Zeichen vor dem Einblenden durch Zufallszeichen ersetzen (String-Nodes, Index Switch). |
| `ET Plate` | Mesh | 5 | Grundplatte mit Rundung über Mesh to SDF Grid → Offset → Grid to Mesh, Bake. |
| `ET Outline` | Mesh | 5 | Kontur über Curve to Mesh (Profil) oder SDF. |
| `ET Fit Camera` | Scene | 3 | Hilfsgruppe: Bounding Box → Abstand/Ortho-Scale für den Kamera-Operator (Camera Info). |

Presets in `ET Text` sind feste Kombinationen: Preset-Menü (Menu Switch) wählt Selektor + Animator-Parameter.
Nutzer mit Node-Editor setzen die Gruppen direkt zusammen.

## 4. Modifier-UI von `ET Text` (Phase 1)

```
Text
  Zeile 1 … Zeile 4          (String; die Extension schreibt mehrzeiligen Text mit "\n" in Zeile 1)
Typografie
  Font (Font-Socket), Größe, Ausrichtung X (Menü), Ausrichtung Y (Menü), Pivot (Menü)
  Zeichenabstand, Wortabstand, Zeilenabstand
  Textbox: Breite, Höhe, Überlauf (Menü)         [Unterpanel, standardmäßig zu]
Form
  Tiefe (Gizmo: Linear), Fill-Modus
  Bevel [Panel-Toggle]: Breite, Segmente, Profil
  Shade Smooth, Glättungswinkel
Material
  Front, Seite, Bevel
Ausgabe
  Merge by Distance, Attribute behalten (Bool)   [standardmäßig zu]
```

Warnungen über `Warning`-Node: leerer Text, Bevel größer als halbe Tiefe, mehr als 2000 Zeichen.

## 5. Offene Implementierungsfragen

1. Zeichen ohne Geometrie (Leerzeichen): Der Index läuft nur über Glyphen. Für Typewriter zählt die
   Extension die Zeichen im String, die Gruppe mappt über `et_char_index`. Zu prüfen, ob 5.2 Leerzeichen
   wirklich keine Instanz liefert.
2. Pivot nach Split to Instances: Instanz-Ursprung liegt dann im Welt-Ursprung; `ET Animate Transform`
   rechnet Rotation/Skalierung explizit um `et_pivot` (Translate → Rotate → Translate zurück) über
   Set Instance Transform mit Matrix-Nodes.
3. Fill Curve über alle Glyphen gleichzeitig: Überlappende Glyphen (negatives Tracking) füllen sich mit
   Even-Odd gegenseitig aus. Option: Fill innerhalb einer For-Each-Zone pro Instanz (langsamer) als
   Schalter "Überlappung erlauben".
4. Materialien gehören als CC0-Assets in dieselbe .blend (Front/Seite/Bevel mit Attribute-Node für `et_alpha`
   und Farbverlauf nach `et_char_index`).
