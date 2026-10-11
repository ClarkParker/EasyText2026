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

### Group nodes as panels (found while building the Easy Text control panel)

- A panel-toggle socket is renamed by Blender to its panel's name: the toggle of panel `-- Bevel --` is the
  socket `-- Bevel --`, not `Bevel`. Every built group therefore stores its input name → identifier map as the
  ID property `et_sockets`; `SocketRef.resolve` and `core.group_socket` fall back to it, so wiring and the demo
  keep using the logical name (`Bevel`, `UV`).
- Links into a multi-input socket (Join Strings, Join Geometry) are inserted on top, so a list of sources has to
  be linked in reverse to keep its order. Visible as reversed text lines before the fix.
- Unlinked group-node inputs are editable widgets on the node (text fields, sliders, dropdowns, font and material
  pickers) and keep their values per node; `hide_value` on the interface socket would hide them.
- Frame text wraps to the frame width but is clipped at the frame height; size the frame for the text.
- The node editor overlay "Named Attributes" adds an "n Named Attribute" row to every group node that stores
  attributes; the demo turns it off for the panel view (`space.overlay.show_named_attributes`).

### Animation (found while building .ET Animation)

- A new Menu Switch node starts with the items A and B; clear them before adding your own (`core.menu` does).
- Input names must be unique across the whole interface, panels included: a second "Pivot" (animation centre next
  to the typography pivot) broke the menu defaults, so the animation one is called "Center".
- String to Curves' "Pivot Point" output is relative to the glyph instance; the glyph's place is the instance
  Position. `et_pivot` = Position + Pivot Point, stored on the instance domain and realized onto the points.
- A vector socket with subtype EULER stores radians and displays degrees: no conversion in the math, and defaults
  set from Python are radians.
- Instance attributes survive Realize Instances onto the points but not Fill Curve; .ET Solid carries them across
  with Sample Nearest + Sample Index (the list now includes word, line and pivot).

### Plate (found while building .ET Plate)

- Fillet Curve takes its mode as a menu socket (`"Poly"` with `Count` gives real corner vertices for the fill).
- Extrude Mesh moves the selected region and leaves no face behind: a closed slab is top + flipped copy extruded
  down + Merge by Distance, the same recipe as .ET Solid.
- A temporary face attribute (`plate_part`) feeds Mesh Face Set Boundaries to pick the top rim for Mesh Bevel and
  is removed afterwards; Mesh Bevel needs all five offsets set (see Phase 1 pitfalls).
- Geometry Proximity (target faces) against the text mesh gives the relief; Map Range with Smooth Step turns the
  distance into the bump, Triangulate + Subdivide Mesh give the top enough vertices.

### Rigs (found while building ET Light Rig and the camera orbit)

- Geometry Nodes instances of Light objects (Object Info with As Instance → Instance on Points) render as lights:
  verified headless with Cycles 5.2.0 (plane lit 0.82 vs 0.02 without the rig). EEVEE cannot be tested headless
  here (no EGL); it supports instanced lights as well.
- A light shines along its local -Z. Axes to Rotation with primary axis Z = direction away from the target and
  secondary axis Y = world up gives the aim rotation; Object Info in ORIGINAL space keeps the instance free of
  the light object's own transform.
- Empties take Geometry Nodes modifiers in 5.2, so the rig lives on an Empty; the source lights sit in a hidden
  collection and are still evaluated through the Object Info dependency.
- Camera orbit without node assets: a POLY spline arc with `use_path`, Follow Path with `use_fixed_location` and
  `offset_factor` keyframed through `camera.keyframe_insert('constraints["Orbit"].offset_factor', frame=...)`,
  plus Track To (-Z, up Y). Follow Path needs a real Curve object, not a Geometry Nodes curve.
- Modifier inputs from Python: `getattr(mod.properties.inputs, identifier).value = ...`, identifier from the
  group's `et_sockets` map (panel toggles are renamed), then `object.update_tag()` (`rigs.set_modifier_input`).

### Add-on (found while building extension/easy_text)

- Modifier inputs in 5.2 (breaking change, see `docs/reference/research-5.2-rigs-and-extension.md`):
  `mod["Socket_3"]` raises TypeError. `mod.properties.inputs` is an RNA struct with one property group per
  socket identifier; `slot = getattr(mod.properties.inputs, identifier)` and `slot.value` is typed: floats with
  their subtype, menus as enums whose identifiers are the option names ("Center"), ID pointers with a fixed type.
  So `slot.value = "Right"` sets a menu and `layout.prop(slot, "value")` draws the right widget (dropdown, ID
  search, unit slider). `mod.properties.inputs[identifier]["value"]` also works but bypasses RNA; after a write
  call `object.update_tag()`. Names can repeat across panels (the panel "Text" and the input "Text"), so look
  inputs up by identifier (`et_sockets` map, or filter `items_tree` by item_type).
- `Region.active_panel_category` is read-only, so a script cannot open the "Easy Text" tab; the window test draws
  the panels in the "Item" tab instead.
- Extensions: `blender --command extension validate <dir>` and `extension build` work headless with the real
  binary and check the manifest; the bpy wheel has no such command, CI zips with `easytext_build.package`.
  End-to-end check used here: `blender -b --command extension install-file dist/easy_text-3.0.0.zip --repo
  user_default --enable` into an empty `XDG_CONFIG_HOME`, then a `-b --python-expr` run confirms the module
  `bl_ext.user_default.easy_text` is enabled, the panel and operators are registered and Create Text appends
  ET Text Mesh from the bundled file.
- Appending a node group with `bpy.data.libraries.load(path, link=False)` brings its sub-groups, materials and
  fonts along; the add-on appends on first use and sets a fake user.

### Demo file: window layout and screenshots

`build` writes the demo scene headless. The window layout (workspace "Easy Text", camera view on top, node editor
below, properties on the modifier tab) is applied afterwards by `easytext_build.demo_ui` in a real Blender 5.2.0
window, because headless Blender neither switches workspaces nor keeps area changes in the saved file. It runs under
Xvfb (see README) and also captures a screenshot of every node group into `docs/screenshots/` for layout review.

What the script has to work around (all verified on 5.2.0):

- `window.workspace = ...` and redraws only happen in Blender's event loop, so the work is a generator driven by
  `bpy.app.timers`; every `yield` hands one tick to the event loop.
- The timer must be registered with `persistent=True`; a file load removes all other timers.
- After `wm.open_mainfile` the old window reference is gone; fetch `window_manager.windows[0]` again.
- `screen.screenshot_area` reads the GL front buffer, which stays black on a virtual display; the X server is
  captured instead with ImageMagick's `import` and cropped to the area.
- Areas are joined with `screen.area_join(source_xy, target_xy)` (5.x signature); `space_type_set_or_cycle` changes
  an area type, `screen_full_area` / `back_to_previous` maximise the node editor for the screenshots.

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
