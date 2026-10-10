# Easy Text v3 – Zielbild, Plattform, Architektur-Optionen

Teil 2 von 2 (Teil 1: `01-analyse-v2.1.md`). Stand: 2026-10-10.
Quellen: offizielle Blender-Release-Notes 3.3 bis 5.3-Beta, Blender-Handbuch 5.2, Python-API-Changelogs,
Blender-Quellcode (`vfont_curve.cc`), GitHub-Metadaten der genannten Projekte (Stand 2026-10-10).
Mit [U] markierte Punkte konnten nicht aus einer Primärquelle bestätigt werden.

## 1. Zielplattform

| Version | Status (Okt. 2026) | Python | Für v3 relevant |
|---|---|---|---|
| 4.2 LTS | Support beendet Juli 2026 | 3.11 | Nicht mehr als Ziel sinnvoll. |
| 4.5 LTS | Support bis Juli 2027 | 3.11 | Panels, Menu Switch, Zonen, Gizmos, Camera Info, Panel-Toggles. **Kein Font-Socket.** |
| 5.0 / 5.1 | reguläre Releases | 3.11 / 3.13 | 5.0: Bundles, Closures, SDF-Grids offiziell. 5.1: Font-Socket, alle String-to-Curves-Optionen als Sockets, Word-Index. |
| **5.2 LTS** | aktuell, Support bis Juli 2028 | 3.13 | String-Felder, Trim/Split/Set Case, Listen, Mesh Bevel, Sound-Sampling, GN auf Empties, saubere Modifier-Property-API. |
| 5.3 | Beta, Release Nov. 2026 | 3.13 | Vulkan wird Standard auf Windows/Linux. |

Empfehlung: **Minimum Blender 5.2 LTS.** Begründung: Font-Socket (5.1) ist die einzige Möglichkeit, den Font im
Modifier-UI zu wählen; die String-Nodes und Listen (5.2) ersparen die Python-Krücken für Zeilen/Wörter;
5.2 ist LTS bis 2028. Ein 4.5-Pfad wäre ein zweiter Build mit Einschränkungen (kein Font-Picker im Modifier,
kein Mesh Bevel, andere Modifier-API) und ist aus meiner Sicht den Aufwand nicht wert.
Das ist Entscheidung 1 (siehe Abschnitt 9).

## 2. Welche neuen Geometry-Nodes-Funktionen was in v2.1 ersetzen

| Problem in v2.1 | Lösung in 5.2 | seit |
|---|---|---|
| Überschriften als Fake-Sockets | Interface-Panels (verschachtelbar), Panel-Beschreibung als Tooltip, Panel-Toggle (Bool-Socket im Panel-Header) | 4.0 / 4.4 / 4.5 |
| Kein Modifier-UI | Panels im Modifier, "Single Value"-Inputs ohne Attribut-Toggle, Node-Group-Selector ausblendbar, Asset-Modifier im Add-Modifier-Menü | 4.0 / 4.1 |
| Bool-Schalter-Kaskaden (Logic Board) | Menu Switch (Dropdown im Modifier), Index Switch | 4.1 |
| 4 feste Zeilen + Line Combiner | Join Strings + leere Zeilen per String Length überspringen; alternativ Split String → Liste; Import Text (Textdatei) | 5.2 / 4.5 |
| Font nur im Node-Editor | Font-Socket, alle String-to-Curves-Optionen als Sockets (Align, Overflow, Pivot als Menüs) | 5.1 |
| Keine Wort-/Zeilen-Auswahl | String to Curves liefert Line- und Word-Index pro Zeichen, Instanzen heißen wie ihr Zeichen | 5.1 / 4.5 |
| Animation per Hand-Vektor | Scene Time bzw. `default_input = SCENE_FRAME` an einem Input, Simulation Zone, For-Each-Element-Zone, Closures für austauschbare Easings | 3.1 / 5.2 / 3.6 / 4.3 / 5.0 |
| Bevel-Platte über dichtes Grid + Proximity | Mesh to SDF Grid → SDF Grid Offset / Fillet → Grid to Mesh (Rundung bei konstanten Kosten) oder Mesh Bevel Node; Ergebnis per Bake Node cachen | 5.0 / 5.2 / 4.1 |
| "Danger"-Labels | Warning Node (Warnung im Modifier-Panel, nach Schwere sortiert) | 4.3 |
| Keine Viewport-Handles | Linear-, Dial-, Transform-Gizmo an Group-Inputs (z. B. Textbox-Breite, Extrusion, Plattengröße) | 4.3 |
| Rotation als Euler-Vektor | Rotation-Socket, Matrix-Socket, Set Instance Transform | 4.0 / 4.2 |
| Materialien 3.x / Legacy-EEVEE | Neu aufbauen für EEVEE (4.2+): Render-Methode statt Blend-Mode, kein Bloom, neue Schatten | 4.2 |
| Hilfetexte als Text-Datablocks an Frames | Socket- und Panel-Descriptions (Tooltips), Node-Group-Description im Asset | 4.0 / 4.3 |

Weitere Bausteine, die es 2022 nicht gab und die v3 nutzen sollte:
Sort Elements / Split to Instances (4.1), Set Geometry Name (4.3), Format String / Match String (4.5),
Active Camera (4.1) und Camera Info (4.5) für "an Kamera ausrichten / ins Bild einpassen",
Essentials-Assets Box/Sphere Selection (5.0) als fertige Falloff-Felder, 3D↔Screen-Space-Assets (5.2),
Sample Sound Frequencies (5.2) für tongesteuerte Animation, Grease-Pencil-Strokes aus Kurven (4.3, Füllungen über `fill_id` seit 5.1) für 2D-Typo.

## 3. Typografie: was nativ geht und was nicht

Nativ mit String to Curves (5.2): mehrzeiliger Text, Textbox mit Umbruch / Scale-to-Fit / Truncate (Rest über "Remainder" weiterreichen),
Ausrichtung links/zentriert/rechts/Blocksatz/Flush, vertikale Ausrichtung inkl. Grundlinien, 7 Pivot-Modi pro Zeichen,
Zeichen-/Wort-/Zeilenabstand (je ein Skalar), Line- und Word-Index, Font-Wechsel pro String-to-Curves-Node,
String-Manipulation (Join, Replace, Slice, Trim, Split, Case, Find, Format), Typewriter über Slice/Truncate pro Frame,
Text aus Datei, Füllung mit Fill Rule, Extrusion, Bevel (Mesh Bevel 5.2 oder Curve to Mesh mit Profil), Outline/Stroke (Curve to Mesh mit Kreisprofil),
runde/aufgeblasene/verschmolzene Glyphen über SDF-Grids, Text auf Pfad (Kurve bei akkumuliertem Vorschub sampeln).

Nicht nativ (aus dem Blender-Quelltext `vfont_curve.cc` verifiziert): Kerning-Paare (GPOS/kern; es gibt nur den manuellen Per-Zeichen-Kern),
Ligaturen und sonstige OpenType-Features (ss01, smcp, liga, Brüche), Shaping/Bidi (Arabisch, Hebräisch, Indisch),
Variable-Font-Achsen, Farb-Emoji, Font- oder Stilwechsel **innerhalb** eines String-to-Curves-Nodes (Textobjekte können
Bold/Italic pro Zeichen, GN nicht), String-Attribute pro Zeichen (5.2: "noch nicht unterstützt").

Lösungsweg für "echte" Typografie (so macht es das GPL-3-Add-on ST2): Shaping in Python mit `uharfbuzz` (Apache-2.0, Wheels für
Windows/macOS/Linux, als Extension-Wheel bündelbar) und Glyph-Konturen mit `fontTools` (MIT) als Bezier-Splines nach Blender;
Variable Fonts über `fontTools.varLib.instancer`. Ausgabe: eine Kurve pro Glyphe (Glyph-Atlas-Collection) plus Punktwolke
mit Attributen (glyph_id, char_index, word_index, line_index, advance) → Instance on Points. Damit entsteht dieselbe
Instanzstruktur wie bei String to Curves, und **dieselben Animator-Node-Gruppen funktionieren für beide Wege**.

## 4. Was es an freiem Code zum Adaptieren gibt

Ergebnis der Recherche: Es gibt **kein** reifes Open-Source-Kinetic-Typography-System auf Geometry-Nodes-Basis für Blender.
Alles mit After-Effects-artigen Per-Zeichen-Animatoren ist kostenpflichtig (PopText, Quick Motion, Text Improver, TextTools, Type Animator Pro).
Die Extensions-Plattform liefert zu "typography" null Treffer. v3 wäre das erste freie System dieser Art.

Verwendbar (GPL-kompatibel):

| Projekt | Lizenz | Stand | Was wir übernehmen |
|---|---|---|---|
| ST2 (coldtype/st2) | GPL-3 | Juni 2026 | Shaping-Pipeline (HarfBuzz/fontTools → Blender-Kurven), Variable-Font-Handling. Referenz für den Pro-Typo-Pfad. |
| Text Helper (AIGODLIKE) | GPL-3+ | Juli 2026, Blender 5.2+ | System-Font-Scan (Win/mac/Linux), Font-Picker mit Vorschau, Viewport-HUD. Vorlage für die Font-UX. |
| writinganimation (Shriinivas) | GPL-3 | 2024 | "Write-on"-Effekt; in GN als Trim Curve pro Spline nachbaubar. |
| Add Camera Rigs (Extension) | GPL | Feb. 2026, 4.2+ | Dolly-/Crane-/2D-Rig-Code für ein "Text-Kamera"-Preset. |
| Camera Shakify | GPL-3 (Code), CC0 (Daten) | Feb. 2026, 5.0-fix | Handheld-Shake als Action-Layer. |
| Tri-Lighting (Extension) | GPL | 4.2+ | Kleinstes Drei-Punkt-Licht-Rig mit Track-To. |
| Light It Up | GPL-3+ | Sept. 2026, 4.2–5.2 | Controller-Empty mit Live-Reglern (Intensität, Temperatur, Orbit), "Fit to Subject". Quelltext-Verfügbarkeit [U]. |
| Extra Lights (jlampel) | GPL-3+ | Nov. 2025 | Photometrische Licht-Presets. |
| Essentials-Assets (Blender) | Blender-Projekt | 5.0 / 5.2 | Box/Sphere/Normal Selection als Falloff-Felder, Screen-Space-Assets. Lizenz des Asset-Repos vor dem Kopieren prüfen [U]. |
| MOPs (Houdini, LGPL-3) | LGPL-3 | Sept. 2026 | Nur das Konzept: ein Falloff-Attribut, das Selektoren schreiben und Animatoren lesen. |

Nicht verwendbar oder unklar: Gumroad-Node-Packs (Typotheque, Two Dancing Clams, menghour) ohne Lizenzangabe; johnnygizmo/node_repo (keine Lizenzdatei);
Erindale Toolkit (GPL, aber Stand 2023 / Blender 3.x); Animation Nodes und Sverchok (keine Glyph-Geometrie, zu schwer als Abhängigkeit).

UX-Modelle, deren Begriffe wir übernehmen sollten (alle teilen dasselbe Schema: Elementhierarchie × Selektor/Falloff × Animator × Zeit × Komposition):
- After Effects Range Selector: Start/End/Offset, Einheit Prozent/Index, Basis Zeichen/Wörter/Zeilen, Form (Square, Ramp Up/Down, Triangle, Round, Smooth), Ease High/Low, Randomize + Seed, Modus Add/Subtract/Min/Max, Amount. Wiggly Selector als Noise-Gewicht.
- Cavalry: "Transition Size + Completion" (ein Regler = Fortschritt des Reveals), "Specific Indices"-Syntax ("0,1:3,last").
- Cinema 4D Fields: Falloff-Objekte (Box/Kugel/Linear) als Layer mit Blend-Modi.
- Kinetic Typography Engine (Lee/Forlizzi/Hudson, UIST 2002): Sequenzbaum Phrase→Wort→Buchstabe, Zeitfilter (Delay, Speed, Loop, Reverse, PaceInOut), Verhalten als additive Wellenformen. Das ist die sauberste Blaupause für die Node-Architektur.
- Kinedit (CHI 2003): "Preset zuerst, Parameter danach" für Nicht-Experten.
- Whitepaper zu GPU-Fontrendering (Loop-Blinn, Slug, SDF/msdfgen) sind für die Blender-Pipeline nicht anwendbar; nur das SDF-Konzept landet über die 5.0-SDF-Grid-Nodes im Tool.

## 5. Architektur-Vorschlag v3

Ebene A: **Node-Group-Assets** (`easytext_v3.blend` + `blender_assets.cats.txt`, Modell der Blender-Essentials). Funktioniert ohne Add-on als Modifier.
1. Glyph-Quelle: `ET Text Source` (String to Curves mit Font-Socket, Zeilen-Join, Textbox, Pivot) oder `ET Glyph Points` (Instanzen aus dem Python-Shaping).
   Vertrag: Instanzen pro Zeichen mit Attributen `char_index`, `word_index`, `line_index`, `pivot`, `advance`, `is_space`.
2. Selektoren (schreiben `et_weight` 0..1 auf die Instanz-Domain): `Range` (AE-Modell), `Transition` (Cavalry-Modell), `Field` (Objekt-Falloff, nutzt Essentials Box/Sphere Selection), `Noise`, `Sound` (5.2).
   Kombination über Modus (Add/Sub/Mul/Min/Max) durch Hintereinanderschalten.
3. Animatoren (lesen `et_weight`): `Transform` (Position/Rotation/Scale um Pivot, per-Zeichen 3D), `Opacity/Color` (Attribut fürs Material), `Tracking/Line Spacing`,
   `Typewriter/Reveal`, `Write-on`, `Scramble/Decoder` (String-Nodes), `Bounce/Oscillate/Jitter` (Wellenformen, optional Simulation Zone für Physik).
4. Zeitmodell (KT Engine): lokale Zeit pro Element `t_i = ease((frame − start − stagger·rank_i) / duration)`, Rang aus Index, Zufall oder Sortierung (Sort Elements);
   Easing als Menu (Linear, Smooth, Elastic, Bounce, Back) plus "Custom" als Closure (5.0) oder Float Curve.
5. Mesh: Fill → Extrude → Bevel (Mesh Bevel 5.2) → Top/Side/Bevel-Material → Shade Smooth; Platte und Outline über SDF-Grids; Bake Node für schwere Ergebnisse.
6. Modifier-UI: Panels "Text", "Typografie", "Form", "Material", "Animation" (mit Panel-Toggle), "Grundplatte", "Erweitert";
   Menüs für Ausrichtung/Preset/Easing; Gizmos für Textbox, Extrusion, Plattengröße; Warning Node für Grenzwerte.

Ebene B: **Extension (GPL-3, Blender-Extensions-Format)**. Liefert, was Nodes nicht können:
Asset-Bibliothek registrieren; N-Panel "Easy Text" mit Presets (Kinedit-Prinzip); mehrzeiliger Text-Editor (Text-Datablock → String-Input, weil
String-Sockets im Modifier einzeilig sind); Font-Picker mit System-Scan (Text-Helper-Muster); Operatoren "Kamera-Rig hinzufügen" (Dolly/Crane/Orbit, Fit-to-Text über Camera Info),
"Licht-Rig hinzufügen" (Drei-Punkt, Softbox, Rim, als Controller-Empty mit Live-Reglern); Pro-Typo-Pfad (uharfbuzz + fontTools als gebündelte Wheels);
Export-Helfer (Apply/Realize, glTF/USD/Alembic-Voreinstellungen). GN kann weder Lichter noch Kameras erzeugen und GN-Modifier liegen nur auf Geometrie-Objekten
(seit 5.2 auch auf Empties), daher gehört Licht/Kamera zwingend in die Extension.

## 6. GPU-Frage, ehrlich beantwortet

Geometry Nodes werden **auf der CPU** ausgewertet (multithreaded), in jeder Version bis einschließlich 5.3-Beta. GPU-Auswertung ist laut
GN-Workshop vom September 2026 ein "lang gehegtes Ziel" im Design-Stadium: opt-in pro Node, nur Attribute/Listen/Grids, Vulkan/Metal-fokussiert,
ohne Release-Ziel. Volume-Grids laufen über OpenVDB auf der CPU. Es gibt also für v3 keine GPU-Beschleunigung der Nodes, die man
verlässlich oder überhaupt nutzen könnte. Eigene GPU-Compute-Shader über das Python-`gpu`-Modul wären backend-abhängig (OpenGL/Vulkan/Metal) und
genau das Gegenteil von "verlässlich auf allen GPUs".

Was auf der GPU läuft und auf allen unterstützten GPUs funktioniert: EEVEE (OpenGL, Vulkan, Metal), Workbench, GPU-Subdivision, der Viewport-Compositor,
Cycles (CUDA/OptiX/HIP/Metal/oneAPI). Konsequenz für v3:
- GN-Seite auf CPU-Effizienz auslegen: Instanzen so lange wie möglich behalten, erst am Ende realisieren, keine dichten Grids, SDF-Auflösung begrenzen, Bake Node für Platte/Outline, For-Each-Zonen nur wo Felder nicht reichen.
- Render-Seite backend-neutral halten: Materialien ohne EEVEE-Legacy-Tricks, keine Backend-spezifischen Shader; 5.3 macht Vulkan auf Windows/Linux zum Standard, macOS ist seit 4.0 Metal-only, OpenGL-Entfernung wird für 6.0 diskutiert (nicht entschieden).
- Mindestanforderung an Hardware übernehmen wie Blender 5.2 selbst (2 GB VRAM, OpenGL 4.3 / Vulkan 1.3; 5.3 senkt auf Vulkan 1.1).

## 7. Versionierung im Git (Node-Trees als Code)

Blender hat kein offizielles Text-/JSON-Format für Node-Trees und plant keines; die offizielle Verteileinheit ist das Node-Group-Asset in einer .blend mit Katalogdatei.
Für ein Repo bedeutet das:

| Werkzeug | Lizenz | Stand | Rolle |
|---|---|---|---|
| nodebpy (Brady Johnston) | GPL-3+ | PyPI 520.35.1, Okt. 2026, folgt Blender 5.2, Python ≥ 3.13 | Python-Builder, typisiert, sehr aktiv. Kandidat für die Quelle der Wahrheit. |
| reines `bpy` (`interface.new_socket/new_panel`, `nodes.new`) | – | – | Alternative ohne Abhängigkeit, mehr Boilerplate. |
| NodeToPython | GPL-3 | v4.2.0, Aug. 2026, 4.2–5.2 | Nur zum Bootstrappen: im Editor prototypen, nach Python exportieren, in den Builder überführen. |
| Tree Clipper | GPL-3 | v0.1.12, Sept. 2026, 5.0 | JSON-Snapshots für Diffs/Reviews; Kern vendoren statt Add-on-Abhängigkeit. |
| geometry-script, geonodes, NodeKit, pynodes | gemischt | 2025 / keine Lizenz / unreif / archiviert | Nicht verwenden. |

Vorschlag: `src/nodegroups/*.py` (ein Builder pro Gruppe) → `blender -b --python build_assets.py` erzeugt `assets/easytext_v3.blend` + Katalog + JSON-Snapshots als
CI-Artefakt. Die .blend wird nie von Hand editiert. Headless-Build in CI über das `bpy`-Wheel von PyPI (5.2 braucht Python 3.13) oder einen Blender-Download in GitHub Actions.
Hinweis: In dieser Cloud-Session läuft Python 3.13; ob das `bpy`-5.2-Wheel hier installierbar ist (Größe, Proxy), habe ich noch nicht geprüft. Falls ja, können wir Node-Gruppen
direkt hier bauen und testen, ohne dass du jedes Mal Blender öffnen musst.

## 8. Breaking Changes, die uns beim Neuaufbau betreffen

- 4.0: `tree.inputs/outputs` → `tree.interface` mit Panels; `socket_type` ist der Basistyp (`NodeSocketFloat`), Subtyp danach setzen.
- 4.1: dynamische Sockets (Switch, Store Named Attribute) → in Python nur über Socket-Identifier, nie über Index. Rotate Euler → Rotate Rotation.
- 4.2: Modifier-Inputs statisch typisiert; EEVEE-Material-Properties umbenannt.
- 4.5: Curve to Mesh bekommt "Scale"-Input statt impliziten Radius (Verhaltensänderung).
- 5.0: Dateien nur noch ab 4.5 lesbar, Random Value liefert andere Integer, `material.use_nodes` immer True.
- 5.1: Node-Tools brauchen eindeutige Operator-IDs (Re-Save), Python 3.13, User-Site-Packages nicht mehr geladen.
- 5.2: `modifier["Input_x"]` → `modifier.properties.inputs.<identifier>.value`; Compare/Random-Value-Identifier geändert; Node-Tool-Assets erneut speichern.
Konsequenz: v2.1 wird nicht migriert, sondern neu gebaut; v2.1 dient nur als Verhaltensreferenz (die Dumps liegen in `docs/reference/v2.1-dump/`).

## 9. Entscheidungen mit begründetem Vorschlag

1. **Mindestversion: nur Blender 5.2 LTS.** Der Font-Socket (5.1) ist die einzige Möglichkeit, den Font im Modifier zu wählen; String-Felder, Split/Trim, Listen und Mesh Bevel (5.2) ersparen Python-Krücken; die Modifier-Property-API wurde in 5.2 neu geschnitten, die Extension müsste für 4.5 einen zweiten Code-Pfad pflegen. 5.2 ist LTS bis Juli 2028, 4.5 endet Juli 2027, also noch bevor v3 reif ist. Ein 4.5-Build wäre ein zweites Produkt mit halbem Funktionsumfang.
2. **Paketform: Node-Assets plus optionale Extension.** Die Assets allein müssen als Modifier funktionieren und in jeder Datei ohne Add-on rendern (Prinzip der Blender-Essentials; Kollegen und Renderfarmen brauchen nichts zu installieren). Die Extension liefert nur, was Nodes nicht können: Font-Scan, mehrzeiliger Text-Editor, Presets, Kamera-/Licht-Rigs, Shaping. Regel: Die Extension erzeugt ausschließlich native Blender-Daten, nie Laufzeit-Abhängigkeiten in der Szene.
3. **Pro-Typografie in v3.1, Schnittstelle in v3.0.** Shaping (uharfbuzz, fontTools, drei Plattform-Wheels, Variable Fonts) ist der größte Einzelrisiko-Block und nützt nur, wenn Kern und Animation stehen. In 3.0 wird der Attribut-Vertrag (char/word/line-Index, Pivot, Advance, Gewicht) so festgelegt, dass die Shaping-Quelle später ohne Änderung an den Animatoren einsteckt. Ein Zwischenschritt für 3.0 ist möglich: Kerning-Paare mit fontTools (reines Python, MIT) vorab berechnen und als X-Offset pro Instanz anwenden.
4. **Presets für 3.0: acht Stück, alle aus denselben fünf Animatoren.** Typewriter, Pop (Scale/Fade-In), Drop (Fall mit Bounce-Easing), Wave, Slide pro Wort, Zeilen-Reveal, Scramble/Decoder, Bounce (Erbe aus v2.1). Dazu der Sound-Selektor (Sample Sound Frequencies, 5.2), weil er nur ein weiterer Selektor ist. Write-on braucht eine Stroke-Pipeline (Trim Curve vor Fill) und wandert nach 3.1. Begründung: Der Wert steckt im Selektor- und Zeitmodell; wenn das steht, kostet ein Preset eine Stunde, nicht einen Tag. Der Opacity-Animator braucht von Anfang an den Material-Hook (Attribut → Alpha), sonst fehlen Fade-Effekte in jedem Preset.
5. **Licht/Kamera in 3.0: minimal, aber dabei.** Ein Operator "Licht-Rig" mit drei Presets (Drei-Punkt, Softbox/Produkt, Rim/Dramatisch) als Controller-Empty mit Live-Reglern (Intensität, Farbtemperatur, Orbit) nach dem Muster von Light It Up/Tri-Lighting. Ein Operator "Kamera" mit drei Presets (Frontal mit Fit-to-Text über die Bounding-Box, Turntable/Orbit, Dolly-In). Kamera-Shake (Shakify-Daten, CC0) in 3.1. Begründung: Ein Titel ohne Kamera-Shot ist nur das halbe Ergebnis, und drei Presets decken den Großteil der Title-Shots ab. Alles als native Daten, die Datei rendert ohne Extension.
6. **Builder: reines bpy mit eigener dünner Helferschicht, nicht nodebpy.** Der Builder ist die Quelle der Wahrheit für Jahre; eine Drittbibliothek mit eigenem Release-Takt (nodebpy 520.x) bringt API-Drift in die Build-Kette. Ein Helfer von etwa 200 Zeilen (Node anlegen, Inputs setzen, Links ziehen, Auto-Layout, Panels) liefert den Großteil des Komforts ohne Abhängigkeit, und NodeToPython-Exporte landen direkt in diesem Stil. nodebpy bleibt der Plan B, falls der Helfer über etwa 500 Zeilen wächst.
7. **Grease-Pencil-/2D-Ausgabe: nicht in 3.0, Architektur hält die Tür offen.** Die GP-Füllungen wurden in 5.1 umgestellt (`fill_id`), die Kurven-GP-Konvertierung ist laut Release-Notes nicht verlustfrei, und das Ziel von v3 ist 3D-Typografie mit Licht und Kamera. Da die Glyphen vor dem Fill als Kurven vorliegen, ist ein späterer GP-Ausgang ein eigener Endknoten, kein Umbau.
8. **Verteilung: GitHub-Releases zuerst, Extensions-Plattform ab 3.0 stabil.** GitHub erlaubt schnelle Betas und Pre-Releases ohne Review-Zyklus. Die Extensions-Plattform bringt Auffindbarkeit und Auto-Updates in Blender, verlangt aber GPL, keine Netzwerkzugriffe und einen Review pro Version; gebündelte Wheels sind erlaubt, also steht dem Shaping-Pfad nichts im Weg.
9. **Lizenz: GPL-3.0-or-later für Code, CC0 1.0 für Assets und Beispielszenen.** GPL ist für die Extension ohnehin Pflicht und erlaubt die Übernahme von Code aus Add Camera Rigs, Tri-Lighting, Camera Shakify, ST2 und Text Helper. CC0 für die Node-Gruppen nimmt Nutzern jede Unsicherheit, wenn sie die Gruppen in eigene oder kommerzielle Dateien einbetten. Folge: Essentials-Node-Gruppen (Lizenz ungeklärt) werden nicht kopiert, sondern selbst nachgebaut; der Beispielfont Monoton bleibt unter seiner OFL.

## 10. Vorgeschlagener Fahrplan (nach der Besprechung)

0. Infrastruktur: Repo-Layout, Builder-Skelett, headless Build (bpy-Wheel oder Blender in CI), Snapshot-Export, Smoke-Test (Datei lädt, Modifier evaluiert).
1. Kern: Glyph-Quelle, Layout, Mesh (Fill/Extrude/Bevel), Materialien (EEVEE/Cycles-neutral), Modifier-UI mit Panels/Menüs/Gizmos/Warnings.
2. Animation: Attribut-Vertrag, Selektoren, Animatoren, Zeitmodell, 8–10 Presets.
3. Szene: Extension mit N-Panel, Presets, mehrzeiligem Text-Editor, Font-Picker, Kamera- und Licht-Rigs.
4. Pro-Typo: Shaping-Pfad, Variable Fonts.
5. Politur: Grundplatte/Outline über SDF, Bake, Export-Helfer, Doku, Extension-Paket.
