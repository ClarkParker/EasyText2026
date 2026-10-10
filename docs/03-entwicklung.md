# Entwicklungsregeln

## Quelle der Wahrheit

Die Node-Gruppen entstehen ausschließlich aus den Builder-Skripten in `src/easytext_build/groups/`.
`assets/easytext_v3.blend` ist ein Build-Artefakt und wird nie im Node-Editor editiert und zurückgespeichert.
Prototypen dürfen im Editor entstehen; sie werden mit NodeToPython exportiert und dann in den Builder-Stil überführt.

Jeder Build schreibt zusätzlich `assets/snapshots/<Gruppe>.json`. Diese Snapshots sind deterministisch
(sortierte Schlüssel, gerundete Floats) und werden committet, damit Pull Requests lesbare Diffs zeigen.
Die CI schlägt fehl, wenn die Snapshots nicht zum Code passen.

## Namenskonventionen

- Node-Gruppen: Präfix `ET `, z. B. `ET Text Source`, `ET Range Selector`. Interne Hilfsgruppen beginnen mit `.ET ` (werden in Menüs ausgeblendet).
- Attribute auf Geometrie: Präfix `et_`, z. B. `et_char_index`, `et_word_index`, `et_line_index`, `et_weight`.
- Socket-Identifier sind stabil: Ein einmal veröffentlichter Input behält seinen Identifier, sonst verlieren Nutzerdateien ihre Werte.
- Jeder exponierte Input hat Beschreibung, Min/Max (Soft-Limits) und Subtyp. Keine Fake-Sockets als Überschriften, dafür Panels.
- Warnungen für Nutzer über den Warning-Node, nicht über Socket-Namen.

## Build und Test

```bash
python -m easytext_build.build
python -m easytext_build.smoke
pytest
ruff check .
```

Der Smoke-Test lädt die gebaute Datei, prüft, dass keine Node als `NodeUndefined` geladen wurde,
hängt die Test-Gruppe als Modifier an ein Objekt und evaluiert sie.

## Zielversion

Blender 5.2 LTS, Python 3.13. API-Besonderheiten, die der Builder voraussetzt:
`tree.interface.new_socket/new_panel` (4.0), verschachtelte Panels (4.4), Panel-Toggles (4.5),
`default_input` an Sockets (4.1), Font-Socket (5.1), Modifier-Properties über `modifier.properties` (5.2).

## API-Fakten Blender 5.2.2 (per bpy-Wheel geprüft, 2026-10-10)

- `NodeTreeInterfaceSocket`: `structure_type` ∈ AUTO, DYNAMIC, FIELD, GRID, LIST, SINGLE; `default_input` ∈ VALUE, INDEX, ID_OR_INDEX, NORMAL, POSITION, INSTANCE_TRANSFORM, HANDLE_LEFT, HANDLE_RIGHT, SCENE_FRAME, UNIFORM_IMAGE_COORDINATES, SELF_OBJECT; `is_panel_toggle`, `menu_expanded`, `optional_label`, `hide_in_modifier`, `force_non_field` (veraltet) vorhanden. Subtypen werden per String gesetzt (`DISTANCE`, `FACTOR`, `ANGLE` …).
- `String to Curves` hat keine Node-Properties mehr; alles sind Sockets: String, Size (Distance), Font (`NodeSocketFont`), Align X / Align Y / Pivot Point / Overflow (Menu-Sockets mit Textwerten wie `Left`, `Top Baseline`, `Midpoint`, `Overflow`), Character/Word/Line Spacing, Text Box Width/Height. Outputs: Curve Instances, Remainder, Line, Word, Pivot Point. Default-Font ist `Bfont Regular`.
- `Fill Curve`: Sockets Curve, Group ID, Mode (Menu, Default `Triangles`), Fill Rule (Menu, Default `Even-Odd`).
- `Extrude Mesh`: Property `mode` (VERTICES/EDGES/FACES), Sockets Mesh, Selection, Offset, Offset Scale, Individual; Outputs Mesh, Top, Side.
- `Mesh Bevel` (5.2): Sockets Mesh, Selection, Affect Kind, Offset, Miter, Spread, Segments, Shape, Profile …; Outputs Mesh, Vertex Face, Edge Face, Outer Edge, Mid Edge.
- `Menu Switch`: Properties `enum_items`/`enum_definition`, `data_type`; Inputs `Menu`, `Item_0`, `Item_1`, … `Index Switch`: `index_switch_items`, `data_type`.
- `Switch`: Property `input_type`, Sockets Switch/False/True mit festen Identifiern.
- `Math`: Input-Identifier `Value`, `Value_001`, `Value_002` (Namen sind gleich, daher im Builder Identifier verwenden).
- `Warning`: Inputs Show, Message; Property `warning_type`.
- String-Nodes 5.2: `FunctionNodeTrimString` (nicht `GeometryNode…`), `FunctionNodeStringLength`, `GeometryNodeStringJoin`, `FunctionNodeInputSpecialCharacters` (Line Break, Tab).
- SDF: `GeometryNodeMeshToSDFGrid` (Voxel Size, Band Width) → `GeometryNodeSDFGridOffset` (Distance) → `GeometryNodeGridToMesh` (Threshold, Adaptivity).
- Kamera: `GeometryNodeInputActiveCamera`, `GeometryNodeCameraInfo` (Projection Matrix, Focal Length, Sensor, Shift, Clip, Focus Distance, Is Orthographic, Orthographic Scale).
- Gizmo: `GeometryNodeGizmoLinear` (Value, Position, Direction; `color_id`, `draw_style`).
- Modifier: `mod.properties.inputs[<identifier>]`, `.outputs`, `.panels`; `mod.node_warnings`, `mod.bakes`, `mod.bake_target`.

## Fallen in der 5.2-API (beim Bau von ET Text Mesh gefunden)

- **Mesh Bevel:** Die Inputs `Start Left Offset`, `Start Right Offset`, `End Left Offset`, `End Right Offset` haben Default 0.1 und überstimmen `Offset`. Ohne sie explizit zu setzen entstehen Spitzen an Ecken, nicht-manifolde Kanten und bei ungerader Segmentzahl doppelte Vertices. Mit allen fünf Offsets auf dem Radius ist das Ergebnis sauber. `Miter = True` auf Textkonturen explodiert die Geometrie (Faces mit Hunderten Ecken).
- **Fill Curve** übernimmt keine Punkt-Attribute der Kurve. Transport über `Curve to Points` (Property `mode = 'EVALUATED'`) → `Sample Nearest` (nur Mesh/Punktwolke als Quelle) → `Sample Index`.
- **Extrude Mesh** und **Mesh Bevel** kopieren Vertex-Attribute auf neue Vertices (keine Interpolation).
- **Set Material** mit Selektion auf einem Mesh, das schon `material_index` trägt, legt einen leeren Slot 0 an. Erstes Material ohne Selektion direkt nach dem Fill setzen, danach selektiv überschreiben.
- **Menü-Inputs** am Group-Interface bekommen ihre Einträge über den verlinkten Node; `default_value` lässt sich erst nach dem Verlinken setzen (Builder: `menu_default()` in `finish()`).
- **Font-Socket:** Ohne Default-Font liefert String to Curves den Fehler "Font not specified". Eingebauter Font über `bpy.data.fonts.load('<builtin>')` (Name `Bfont Regular`).
- **String to Curves** erzeugt für Leerzeichen eine leere Instanz (Referenz `None`); der Instanz-Index zählt Leerzeichen mit.
- **Modifier-Inputs in Python 5.2:** `mod.properties.inputs[identifier]` ist eine `IDPropertyGroup` mit Schlüsseln `value` und `type` (`p['value'] = …`). Nach dem Setzen `mod.node_group = mod.node_group` plus `ob.update_tag()`, sonst bleibt die Auswertung alt. Gleichnamige Inputs (z. B. "Breite" in zwei Panels) brauchen die Identifier, nicht den Namen.
- **Remove Named Attribute:** `Pattern Mode` kennt nur `Exact` und `Wildcard` (`et_*`).
- **Delete Geometry** auf Kurvenpunkten funktioniert für zyklische Poly-Kurven ohne Nebenwirkung; `Offset Point in Curve` liefert für zyklische Kurven immer gültige Nachbarn.
- **Blender 5.2.0 vs 5.2.2:** 5.2.0 übernimmt Font- und Material-Defaults des Group-Interfaces nicht in die Modifier-Eingaben ("Font not specified"), 5.2.2 schon. Deshalb laufen alle Datablock-Inputs durch `GroupBuilder.fallback()` (Compare "Is None" + Switch mit Node-Default). Der Build ist auf `bpy==5.2.0` gepinnt, damit die Dateien exakt der niedrigsten Zielversion entsprechen (5.2.2 schreibt Datei-Subversion 45, 5.2.0 liest 44).
- **Datablocks, die nur als Socket-Default referenziert sind** (Font, Materialien), brauchen `use_fake_user = True`, sonst fehlen sie nach dem Speichern.
- **Node-Gruppen ohne Nutzer** werden beim Speichern verworfen; Asset-Markierung oder `use_fake_user` setzen.
