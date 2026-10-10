# Development Rules

## Source of truth

The node groups are created exclusively from the builder scripts in `src/easytext_build/groups/`.
`assets/easytext_v3.blend` is a build artifact and is never edited in the node editor and saved back.
Prototypes may be created in the editor; they are exported with NodeToPython and then transferred into the builder style.

Every build additionally writes `assets/snapshots/<group>.json`. These snapshots are deterministic
(sorted keys, rounded floats) and are committed so that pull requests show readable diffs.
CI fails if the snapshots do not match the code.

## Naming conventions

- Node groups: prefix `ET `, e.g. `ET Text Source`, `ET Range Selector`. Internal helper groups start with `.ET ` (hidden in menus).
- Attributes on geometry: prefix `et_`, e.g. `et_char_index`, `et_word_index`, `et_line_index`, `et_weight`.
- Socket identifiers are stable: once published, an input keeps its identifier, otherwise user files lose their values.
- Every exposed input has a description, min/max (soft limits) and a subtype. No fake sockets as headings, use panels instead.
- Warnings for users go through the Warning node, not through socket names.

## Build and test

```bash
python -m easytext_build.build
python -m easytext_build.smoke
pytest
ruff check .
```

The smoke test loads the built file, checks that no node was loaded as `NodeUndefined`,
attaches the test group as a modifier to an object and evaluates it.

## Target version

Blender 5.2 LTS, Python 3.13. API specifics that the builder relies on:
`tree.interface.new_socket/new_panel` (4.0), nested panels (4.4), panel toggles (4.5),
`default_input` on sockets (4.1), font socket (5.1), modifier properties via `modifier.properties` (5.2).

## API facts Blender 5.2.2 (verified via bpy wheel, 2026-10-10)

- `NodeTreeInterfaceSocket`: `structure_type` ∈ AUTO, DYNAMIC, FIELD, GRID, LIST, SINGLE; `default_input` ∈ VALUE, INDEX, ID_OR_INDEX, NORMAL, POSITION, INSTANCE_TRANSFORM, HANDLE_LEFT, HANDLE_RIGHT, SCENE_FRAME, UNIFORM_IMAGE_COORDINATES, SELF_OBJECT; `is_panel_toggle`, `menu_expanded`, `optional_label`, `hide_in_modifier`, `force_non_field` (deprecated) are present. Subtypes are set by string (`DISTANCE`, `FACTOR`, `ANGLE` …).
- `String to Curves` no longer has node properties; everything is sockets: String, Size (Distance), Font (`NodeSocketFont`), Align X / Align Y / Pivot Point / Overflow (menu sockets with text values such as `Left`, `Top Baseline`, `Midpoint`, `Overflow`), Character/Word/Line Spacing, Text Box Width/Height. Outputs: Curve Instances, Remainder, Line, Word, Pivot Point. Default font is `Bfont Regular`.
- `Fill Curve`: sockets Curve, Group ID, Mode (menu, default `Triangles`), Fill Rule (menu, default `Even-Odd`).
- `Extrude Mesh`: property `mode` (VERTICES/EDGES/FACES), sockets Mesh, Selection, Offset, Offset Scale, Individual; outputs Mesh, Top, Side.
- `Mesh Bevel` (5.2): sockets Mesh, Selection, Affect Kind, Offset, Miter, Spread, Segments, Shape, Profile …; outputs Mesh, Vertex Face, Edge Face, Outer Edge, Mid Edge.
- `Menu Switch`: properties `enum_items`/`enum_definition`, `data_type`; inputs `Menu`, `Item_0`, `Item_1`, … `Index Switch`: `index_switch_items`, `data_type`.
- `Switch`: property `input_type`, sockets Switch/False/True with fixed identifiers.
- `Math`: input identifiers `Value`, `Value_001`, `Value_002` (names are identical, so use identifiers in the builder).
- `Warning`: inputs Show, Message; property `warning_type`.
- String nodes 5.2: `FunctionNodeTrimString` (not `GeometryNode…`), `FunctionNodeStringLength`, `GeometryNodeStringJoin`, `FunctionNodeInputSpecialCharacters` (Line Break, Tab).
- SDF: `GeometryNodeMeshToSDFGrid` (Voxel Size, Band Width) → `GeometryNodeSDFGridOffset` (Distance) → `GeometryNodeGridToMesh` (Threshold, Adaptivity).
- Camera: `GeometryNodeInputActiveCamera`, `GeometryNodeCameraInfo` (Projection Matrix, Focal Length, Sensor, Shift, Clip, Focus Distance, Is Orthographic, Orthographic Scale).
- Gizmo: `GeometryNodeGizmoLinear` (Value, Position, Direction; `color_id`, `draw_style`).
- Modifier: `mod.properties.inputs[<identifier>]`, `.outputs`, `.panels`; `mod.node_warnings`, `mod.bakes`, `mod.bake_target`.

## Pitfalls in the 5.2 API (found while building ET Text Mesh)

- **Mesh Bevel:** The inputs `Start Left Offset`, `Start Right Offset`, `End Left Offset`, `End Right Offset` have a default of 0.1 and override `Offset`. Without setting them explicitly, spikes appear at corners, non-manifold edges, and duplicate vertices with an odd segment count. With all five offsets set to the radius the result is clean. `Miter = True` on text outlines makes the geometry explode (faces with hundreds of corners).
- **Fill Curve** does not carry over point attributes of the curve. Transport via `Curve to Points` (property `mode = 'EVALUATED'`) → `Sample Nearest` (only mesh/point cloud as source) → `Sample Index`.
- **Extrude Mesh** and **Mesh Bevel** copy vertex attributes to new vertices (no interpolation).
- **Set Material** with a selection on a mesh that already carries `material_index` creates an empty slot 0. Set the first material without a selection directly after the Fill, then overwrite selectively.
- **Menu inputs** on the group interface get their entries via the linked node; `default_value` can only be set after linking (builder: `menu_default()` in `finish()`).
- **Font socket:** Without a default font, String to Curves yields the error "Font not specified". Built-in font via `bpy.data.fonts.load('<builtin>')` (name `Bfont Regular`).
- **String to Curves** creates an empty instance (reference `None`) for spaces; the instance index counts spaces.
- **Modifier inputs in Python 5.2:** `mod.properties.inputs[identifier]` is an `IDPropertyGroup` with keys `value` and `type` (`p['value'] = …`). After setting, `mod.node_group = mod.node_group` plus `ob.update_tag()`, otherwise the evaluation stays stale. Inputs with the same name (e.g. "Width" in two panels) need the identifiers, not the name.
- **Remove Named Attribute:** `Pattern Mode` knows only `Exact` and `Wildcard` (`et_*`).
- **Delete Geometry** on curve points works for cyclic poly curves without side effects; `Offset Point in Curve` always returns valid neighbors for cyclic curves.
- **Blender 5.2.0 vs 5.2.2:** 5.2.0 does not carry the font and material defaults of the group interface over into the modifier inputs ("Font not specified"), 5.2.2 does. Therefore all datablock inputs go through `GroupBuilder.fallback()` (Compare "Is None" + Switch with node default). The build is pinned to `bpy==5.2.0` so that the files correspond exactly to the lowest target version (5.2.2 writes file subversion 45, 5.2.0 reads 44).
- **Datablocks referenced only as a socket default** (font, materials) need `use_fake_user = True`, otherwise they are missing after saving.
- **Node groups without users** are discarded on saving; set the asset mark or `use_fake_user`.
