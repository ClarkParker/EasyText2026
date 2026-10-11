# Architecture v3 (Draft for Phases 1 and 2)

As of: 2026-10-10. Builds on `02-target-v3.md`; makes groups, attribute contract and modifier UI concrete.

**Priority change after consultation:** The main reason for the tool is clean mesh topology and usable UVs
for text. Therefore Phase 1 is the group `ET Text Mesh` (implemented, see `src/easytext_build/groups/et_text_mesh.py`);
animation (selectors/animators) follows afterwards. Sections 2 to 4 still describe the target vision for the animation phase.

## 0. Implemented: ET Text Mesh (Phase 1)

```
Join lines (.ET Lines Join) → String to Curves → store instance index → Realize
→ Set Spline Resolution → Resample (Evaluated) → delete collinear and duplicate points
→ store contour length (et_u) and loop length (et_loop_len)
→ Fill Curve (Mode/Fill Rule) → normals to +Z → Front Material → fetch attributes via Sample Nearest
→ back side (Flip) + Extrude (Faces) → Join → Merge by Distance   [et_face_group: 0 side, 1 front, 2 back, 3 bevel]
→ Mesh Bevel on face-group boundary edges (all five offsets = radius) → new faces = group 3
→ UVMap (Face Corner, 2D): cap faces planar from XY, band from U = et_u (unfolded by loop length at the seam quad)
   and V(z) = arc length across back bevel, side, front bevel; scaling normalized to the text box or in meters
→ Side/Bevel materials via selection → Shade Smooth + hard edges by angle → remove et_* attributes (optional)
→ Warning nodes (empty text, bevel clamped)
```

Known limits: bevel radius ≥ half the stroke width produces overlaps (like the Bevel modifier without clamp);
overlapping glyphs fill each other out (Even-Odd); true quad cap faces are not included.

## 1. Pipeline

```
Text (String, "\n" allowed)  ──► ET Text Source ──► character instances (curves) + attributes
                                                      │
                                     ET Glyph Mesh:   │  Realize → Fill Curve → Extrude → Mesh Bevel
                                                      │  → Split to Instances (et_char_index)
                                                      ▼
                        character instances (meshes, pivot known) ──► selectors (write et_weight)
                                                      │               ──► animators (read et_weight)
                                                      ▼
                                     Realize → materials → Shade Smooth → output
```

Why Realize before the Fill and Split again afterwards: `Fill Curve` and `Extrude Mesh` work on the
realized mesh in one go (fast, one thread pool), and `Split to Instances` (4.1) restores the
per-character instances via the previously stored `et_char_index`. Instance attributes survive
`Realize Instances` as point attributes, so pivot and indices are preserved. Only at the very end is the
final realize done. This replaces the three Realize steps and the Instance/Realize switch from v2.1.

## 2. Attribute contract

All attributes live on the instance domain of the character instances (after the Fill on the point domain
and after the Split on instances again).

| Attribute | Type | Source | Purpose |
|---|---|---|---|
| `et_char_index` | int | Index of the glyph instance (spaces create no instance) | Basis of every selection, split key |
| `et_word_index` | int | String to Curves "Word" | Selection by words |
| `et_line_index` | int | String to Curves "Line" | Selection by lines |
| `et_char_in_word` | int | Accumulate Field (Leading, Group ID = word) | Stagger within a word |
| `et_char_in_line` | int | Accumulate Field (Leading, Group ID = line) | Stagger within a line |
| `et_char_count`, `et_word_count`, `et_line_count` | int (uniform) | Attribute Statistic (Max + 1) | Percent units in selectors |
| `et_pivot` | vector | instance Position + String to Curves "Pivot Point" | Rotation/scale around the glyph pivot (built) |
| `et_weight` | float 0..1 | Selectors | Strength of the animation per element; default 1 |
| `et_time` | float | ET Time | local, normalized time 0..1 per element |

The Python shaping path (v3.1) delivers the same attributes plus `et_glyph_id`; the animators
remain unchanged.

## 3. Group inventory

| Group | Catalog | Phase | Content |
|---|---|---|---|
| `Easy Text` | Easy Text | 1 (built) | Control panel in the node editor, the v3 of the v2.1 GUI: three settings nodes with every control as a widget (Text Lines, Text Settings, Mesh Generation) in the frames Text Input, Font Settings, Mesh Settings; a note with the export hint. |
| `ET Text Mesh` | Text | 1 (built) | Main modifier for the properties editor: inputs as panels (Text, Typography, Outline, Shape, Material, UV, Output); inside the same three nodes as the panel. From Phase 2 an animation panel with preset menu. |
| `.ET Mesh Generation` | internal | 1 (built) | "Mesh Generation" on the panel: curves → mesh through Outline Clean, Solid, Bevel, Text UV, Finish; inputs in panels (Outline, Shape with Bevel switch, Material, UV switch, Output). |
| `.ET Text Source` | internal | 1 (built) | "Text Settings" on the panel: String to Curves with the options in panels (Font, Alignment, Spacing, Text Box), `et_char_index`, "No text" warning. |
| `.ET Lines Join` | internal | 1 (built) | 4 string inputs → one string with Line Break, empty lines skipped. |
| `.ET Outline Clean` | internal | 1 (built) | Spline resolution, resample, collinear/duplicate point removal, `et_u` and `et_loop_len`. |
| `.ET Solid` | internal | 1 (built) | Fill (Mode/Fill Rule) → front material → attribute transfer → back copy + extrude → merge; `et_face_group`. |
| `.ET Bevel` | internal | 1 (built) | Radius clamped to half the depth, face-set boundary edges, Mesh Bevel, bevel face group, "limited" warning. |
| `.ET Text UV` | internal | 1 (built) | `UVMap`: planar caps, continuous band for sides and bevel (U = contour length, V = arc length); bypass toggle. |
| `.ET Finish` | internal | 1 (built) | Side/bevel materials, Shade Smooth by Angle. |
| `.ET Plate` | internal | 2 (built) | "Plate" panel: rounded base plate sized from the text (or by hand), thickness, bevelled top rim, optional relief around the letters (Geometry Proximity on a subdivided top), own planar UVMap, material; face group 4, character index -1 so the animation leaves it. Replaces the v2.1 proximity grid. |
| `.ET Animation` | internal | 2 (built) | "Animation" on the panel: local time per letter/word/line (Start, Duration, Stagger, Order, Loop), easing, direction In/Out, move/rotate/scale around the glyph, word, line or text pivot, Hide Before Start, Bounce; removes the `et_*` helpers unless kept. |
| `ET Time` | Animators | 2 | Frame (default input SCENE_FRAME), Start, Duration, Stagger, Order (Index/Random/Reverse/From Center), Easing menu, Loop/Ping-Pong → `et_time`. |
| `ET Select Range` | Selectors | 2 | AE model: Start/End/Offset, Unit (Percent/Index), Basis (Character/Word/Line), Shape, Ease, Random + Seed, Mode → `et_weight`. |
| `ET Select Transition` | Selectors | 2 | Cavalry model: Completion 0..1 + Width + Direction → `et_weight`. Centerpiece of the reveals. |
| `ET Select Field` | Selectors | 2 | Falloff around object (Box/Sphere/Linear), Invert, Strength. |
| `ET Select Noise` | Selectors | 2 | Time/space-dependent noise weight (Wiggly Selector). |
| `ET Select Sound` | Selectors | 2 | Sample Sound Frequencies → weight per band or index. |
| `ET Animate Transform` | Animators | 2 | Position/Rotation/Scale × `et_weight` around `et_pivot`, pivot mode (Character/Word/Line/All). |
| `ET Animate Visibility` | Animators | 2 | Alpha attribute (`et_alpha`) for material, optional Delete Geometry at 0. |
| `ET Animate Tracking` | Animators | 2 | Animated character/line spacing (displacement along the baseline). |
| `ET Typewriter` | Animators | 2 | Visible character count from `et_time`; cursor optional. |
| `ET Scramble` | Animators | 2 | Replace characters with random characters before fading in (string nodes, Index Switch). |
| `ET Plate` (SDF halo) | Mesh | 5 | Optional later variant: plate outline following the letters via Mesh to SDF Grid → Grid to Mesh with offset threshold. |
| `ET Outline` | Mesh | 5 | Outline via Curve to Mesh (profile) or SDF. |
| `ET Light Rig` | Scene | 3 (built) | Modifier for an Empty: instances of key, fill and rim light objects on a sphere around the target's bounds, aimed at the centre; angle, elevation, distance and a switch per light. |
| camera orbit | Scene | 3 (built, Python) | `rigs.add_camera_orbit`: poly-curve arc around the target, Follow Path (fixed location, keyframed offset) + Track To. Plain Blender, no node asset needed; the extension calls the same function. |
| `ET Fit Camera` | Scene | 4 | Operator in the extension: `camera_fit_coords` on the text bounds. |

Presets in `ET Text` are fixed combinations: a preset menu (Menu Switch) selects selector + animator parameters.
Users with a node editor assemble the groups directly.

## 3b. Add-on (Phase 4, built)

| Part | Content |
|---|---|
| `easy_text/ui.py` | Sidebar tab "Easy Text": main panel drawn from the node group interface (panels, toggles, menus as dropdowns, ID searches), font row, presets, camera and light, export. |
| `easy_text/ops.py` | Operators: create_text, set_font (search popup over system fonts), load_font, preset, set_menu/open_menu, add_light_rig, add_camera_orbit, fit_camera, apply_mesh. |
| `easy_text/fonts.py` | Font folders per OS plus Blender's own, cached list, load with `bpy.data.fonts.load`. |
| `easy_text/assets.py` | Append node groups from the bundled `assets/easytext_v3.blend` on first use. |
| `easy_text/rigs.py` | Camera orbit, camera fit, light rig objects, modifier input helpers; also used by the demo build. |
| `blender_manifest.toml` | Extension manifest (5.2, GPL-3.0-or-later code, CC0 assets, files permission for fonts). |

## 4. Modifier UI of `ET Text Mesh` (Phase 1, as built)

```
Text
  Text, Line 2 … Line 4      (String; the extension writes multi-line text with "\n" into Text)
Typography
  Font (font socket), Size, Align X (menu), Align Y (menu), Pivot (menu)
  Character Spacing, Word Spacing, Line Spacing
  Text Box: Box Width, Box Height, Overflow (menu)         [subpanel, closed by default]
Outline
  Resolution, Simplify, Fill Mode, Fill Rule
Shape
  Depth (planned: linear gizmo)
  Bevel [panel toggle]: Bevel Width, Segments, Profile
  Smooth Angle
Material
  Front Material, Side Material, Bevel Material
UV
  UV, Normalize to Text, UV Scale
Output
  Keep Helper Attributes                                    [closed by default]
```

Warnings via `Warning` node: empty text, bevel larger than half the depth (planned: more than 2000 characters).

## 5. Open implementation questions

1. Characters without geometry (spaces): The index runs only over glyphs. For the typewriter the
   extension counts the characters in the string, the group maps via `et_char_index`. To be checked whether 5.2
   really delivers no instance for spaces.
2. Pivot after Split to Instances: the instance origin is then at the world origin; `ET Animate Transform`
   computes rotation/scale explicitly around `et_pivot` (translate → rotate → translate back) via
   Set Instance Transform with matrix nodes.
3. Fill Curve over all glyphs at once: overlapping glyphs (negative tracking) fill each other out with
   Even-Odd. Option: Fill inside a For Each zone per instance (slower) as a switch "Allow overlap".
4. Materials belong as CC0 assets in the same .blend (Front/Side/Bevel with Attribute node for `et_alpha`
   and color gradient by `et_char_index`).
