# Easy Text v3 – Target Vision, Platform, Architecture Options

Part 2 of 2 (Part 1: `01-analysis-v2.1.md`). As of: 2026-10-10.
Sources: official Blender release notes 3.3 to 5.3 beta, Blender manual 5.2, Python API changelogs,
Blender source code (`vfont_curve.cc`), GitHub metadata of the projects mentioned (as of 2026-10-10).
Items marked [U] could not be confirmed from a primary source.

## 1. Target platform

| Version | Status (Oct. 2026) | Python | Relevant for v3 |
|---|---|---|---|
| 4.2 LTS | Support ended July 2026 | 3.11 | No longer sensible as a target. |
| 4.5 LTS | Support until July 2027 | 3.11 | Panels, Menu Switch, zones, gizmos, Camera Info, panel toggles. **No font socket.** |
| 5.0 / 5.1 | regular releases | 3.11 / 3.13 | 5.0: bundles, closures, SDF grids official. 5.1: font socket, all String to Curves options as sockets, word index. |
| **5.2 LTS** | current, support until July 2028 | 3.13 | String fields, Trim/Split/Set Case, lists, Mesh Bevel, sound sampling, GN on empties, clean modifier property API. |
| 5.3 | Beta, release Nov. 2026 | 3.13 | Vulkan becomes the default on Windows/Linux. |

Recommendation: **minimum Blender 5.2 LTS.** Reasoning: the font socket (5.1) is the only way to choose the font in the
modifier UI; the string nodes and lists (5.2) spare us the Python crutches for lines/words;
5.2 is LTS until 2028. A 4.5 path would be a second build with limitations (no font picker in the modifier,
no Mesh Bevel, different modifier API) and in my view is not worth the effort.
This is decision 1 (see section 9).

## 2. Which new Geometry Nodes features replace what in v2.1

| Problem in v2.1 | Solution in 5.2 | since |
|---|---|---|
| Headings as fake sockets | Interface panels (nestable), panel description as tooltip, panel toggle (Bool socket in the panel header) | 4.0 / 4.4 / 4.5 |
| No modifier UI | Panels in the modifier, "Single Value" inputs without attribute toggle, node group selector can be hidden, asset modifier in the Add Modifier menu | 4.0 / 4.1 |
| Bool switch cascades (Logic Board) | Menu Switch (dropdown in the modifier), Index Switch | 4.1 |
| 4 fixed lines + Line Combiner | Join Strings + skip empty lines via String Length; alternatively Split String → list; Import Text (text file) | 5.2 / 4.5 |
| Font only in the node editor | Font socket, all String to Curves options as sockets (Align, Overflow, Pivot as menus) | 5.1 |
| No word/line selection | String to Curves delivers line and word index per character, instances are named like their character | 5.1 / 4.5 |
| Animation via hand-made vector | Scene Time or `default_input = SCENE_FRAME` on an input, Simulation Zone, For Each Element zone, closures for exchangeable easings | 3.1 / 5.2 / 3.6 / 4.3 / 5.0 |
| Bevel plate via dense grid + proximity | Mesh to SDF Grid → SDF Grid Offset / Fillet → Grid to Mesh (rounding at constant cost) or Mesh Bevel node; cache the result via Bake node | 5.0 / 5.2 / 4.1 |
| "Danger" labels | Warning node (warning in the modifier panel, sorted by severity) | 4.3 |
| No viewport handles | Linear, Dial, Transform gizmo on group inputs (e.g. text box width, extrusion, plate size) | 4.3 |
| Rotation as Euler vector | Rotation socket, Matrix socket, Set Instance Transform | 4.0 / 4.2 |
| Materials 3.x / legacy EEVEE | Rebuild for EEVEE (4.2+): render method instead of blend mode, no bloom, new shadows | 4.2 |
| Help texts as Text datablocks on frames | Socket and panel descriptions (tooltips), node group description in the asset | 4.0 / 4.3 |

Further building blocks that did not exist in 2022 and that v3 should use:
Sort Elements / Split to Instances (4.1), Set Geometry Name (4.3), Format String / Match String (4.5),
Active Camera (4.1) and Camera Info (4.5) for "align to camera / fit into frame",
Essentials assets Box/Sphere Selection (5.0) as ready-made falloff fields, 3D↔screen-space assets (5.2),
Sample Sound Frequencies (5.2) for sound-driven animation, Grease Pencil strokes from curves (4.3, fills via `fill_id` since 5.1) for 2D typography.

## 3. Typography: what works natively and what does not

Natively with String to Curves (5.2): multi-line text, text box with wrapping / scale-to-fit / truncate (pass on the rest via "Remainder"),
alignment left/center/right/justify/flush, vertical alignment incl. baselines, 7 pivot modes per character,
character/word/line spacing (one scalar each), line and word index, font change per String to Curves node,
string manipulation (Join, Replace, Slice, Trim, Split, Case, Find, Format), typewriter via Slice/Truncate per frame,
text from file, fill with Fill Rule, extrusion, bevel (Mesh Bevel 5.2 or Curve to Mesh with profile), outline/stroke (Curve to Mesh with circle profile),
rounded/inflated/merged glyphs via SDF grids, text on path (sample curve at accumulated advance).

Not native (verified from the Blender source `vfont_curve.cc`): kerning pairs (GPOS/kern; there is only the manual per-character kern),
ligatures and other OpenType features (ss01, smcp, liga, fractions), shaping/bidi (Arabic, Hebrew, Indic),
variable font axes, color emoji, font or style change **within** one String to Curves node (text objects can do
bold/italic per character, GN cannot), string attributes per character (5.2: "not yet supported").

Approach for "real" typography (this is how the GPL-3 add-on ST2 does it): shaping in Python with `uharfbuzz` (Apache-2.0, wheels for
Windows/macOS/Linux, can be bundled as an extension wheel) and glyph outlines with `fontTools` (MIT) as Bezier splines into Blender;
variable fonts via `fontTools.varLib.instancer`. Output: one curve per glyph (glyph atlas collection) plus a point cloud
with attributes (glyph_id, char_index, word_index, line_index, advance) → Instance on Points. This yields the same
instance structure as with String to Curves, and **the same animator node groups work for both paths**.

## 4. What free code there is to adapt

Result of the research: there is **no** mature open-source kinetic typography system based on Geometry Nodes for Blender.
Everything with After-Effects-style per-character animators is paid (PopText, Quick Motion, Text Improver, TextTools, Type Animator Pro).
The extensions platform returns zero hits for "typography". v3 would be the first free system of this kind.

Usable (GPL-compatible):

| Project | License | As of | What we take over |
|---|---|---|---|
| ST2 (coldtype/st2) | GPL-3 | June 2026 | Shaping pipeline (HarfBuzz/fontTools → Blender curves), variable font handling. Reference for the pro typography path. |
| Text Helper (AIGODLIKE) | GPL-3+ | July 2026, Blender 5.2+ | System font scan (Win/mac/Linux), font picker with preview, viewport HUD. Template for the font UX. |
| writinganimation (Shriinivas) | GPL-3 | 2024 | "Write-on" effect; can be rebuilt in GN as Trim Curve per spline. |
| Add Camera Rigs (extension) | GPL | Feb. 2026, 4.2+ | Dolly/crane/2D rig code for a "text camera" preset. |
| Camera Shakify | GPL-3 (code), CC0 (data) | Feb. 2026, 5.0 fix | Handheld shake as action layer. |
| Tri-Lighting (extension) | GPL | 4.2+ | Smallest three-point light rig with Track To. |
| Light It Up | GPL-3+ | Sept. 2026, 4.2–5.2 | Controller empty with live sliders (intensity, temperature, orbit), "Fit to Subject". Source availability [U]. |
| Extra Lights (jlampel) | GPL-3+ | Nov. 2025 | Photometric light presets. |
| Essentials assets (Blender) | Blender project | 5.0 / 5.2 | Box/Sphere/Normal Selection as falloff fields, screen-space assets. Check the license of the asset repo before copying [U]. |
| MOPs (Houdini, LGPL-3) | LGPL-3 | Sept. 2026 | Concept only: a falloff attribute that selectors write and animators read. |

Not usable or unclear: Gumroad node packs (Typotheque, Two Dancing Clams, menghour) without license information; johnnygizmo/node_repo (no license file);
Erindale Toolkit (GPL, but as of 2023 / Blender 3.x); Animation Nodes and Sverchok (no glyph geometry, too heavy as a dependency).

UX models whose terms we should adopt (all share the same scheme: element hierarchy × selector/falloff × animator × time × composition):
- After Effects Range Selector: Start/End/Offset, unit percent/index, basis characters/words/lines, shape (Square, Ramp Up/Down, Triangle, Round, Smooth), Ease High/Low, Randomize + Seed, mode Add/Subtract/Min/Max, Amount. Wiggly Selector as noise weight.
- Cavalry: "Transition Size + Completion" (one slider = progress of the reveal), "Specific Indices" syntax ("0,1:3,last").
- Cinema 4D Fields: falloff objects (box/sphere/linear) as layers with blend modes.
- Kinetic Typography Engine (Lee/Forlizzi/Hudson, UIST 2002): sequence tree phrase→word→letter, time filters (Delay, Speed, Loop, Reverse, PaceInOut), behavior as additive waveforms. This is the cleanest blueprint for the node architecture.
- Kinedit (CHI 2003): "preset first, parameters afterwards" for non-experts.
- Whitepapers on GPU font rendering (Loop-Blinn, Slug, SDF/msdfgen) are not applicable to the Blender pipeline; only the SDF concept ends up in the tool via the 5.0 SDF grid nodes.

## 5. Architecture proposal v3

Layer A: **node group assets** (`easytext_v3.blend` + `blender_assets.cats.txt`, modeled on the Blender Essentials). Works as a modifier without an add-on.
1. Glyph source: `ET Text Source` (String to Curves with font socket, line join, text box, pivot) or `ET Glyph Points` (instances from the Python shaping).
   Contract: instances per character with attributes `char_index`, `word_index`, `line_index`, `pivot`, `advance`, `is_space`.
2. Selectors (write `et_weight` 0..1 onto the instance domain): `Range` (AE model), `Transition` (Cavalry model), `Field` (object falloff, uses Essentials Box/Sphere Selection), `Noise`, `Sound` (5.2).
   Combination via mode (Add/Sub/Mul/Min/Max) by chaining them in series.
3. Animators (read `et_weight`): `Transform` (position/rotation/scale around pivot, per-character 3D), `Opacity/Color` (attribute for the material), `Tracking/Line Spacing`,
   `Typewriter/Reveal`, `Write-on`, `Scramble/Decoder` (string nodes), `Bounce/Oscillate/Jitter` (waveforms, optionally Simulation Zone for physics).
4. Time model (KT Engine): local time per element `t_i = ease((frame − start − stagger·rank_i) / duration)`, rank from index, random or sorting (Sort Elements);
   easing as menu (Linear, Smooth, Elastic, Bounce, Back) plus "Custom" as closure (5.0) or Float Curve.
5. Mesh: Fill → Extrude → Bevel (Mesh Bevel 5.2) → Top/Side/Bevel material → Shade Smooth; plate and outline via SDF grids; Bake node for heavy results.
6. Modifier UI: panels "Text", "Typography", "Shape", "Material", "Animation" (with panel toggle), "Base Plate", "Advanced";
   menus for alignment/preset/easing; gizmos for text box, extrusion, plate size; Warning node for limits.

Layer B: **extension (GPL-3, Blender extensions format)**. Delivers what nodes cannot do:
register the asset library; N-panel "Easy Text" with presets (Kinedit principle); multi-line text editor (Text datablock → string input, because
string sockets in the modifier are single-line); font picker with system scan (Text Helper pattern); operators "Add camera rig" (dolly/crane/orbit, fit-to-text via Camera Info),
"Add light rig" (three-point, softbox, rim, as controller empty with live sliders); pro typography path (uharfbuzz + fontTools as bundled wheels);
export helpers (apply/realize, glTF/USD/Alembic presets). GN can create neither lights nor cameras and GN modifiers exist only on geometry objects
(since 5.2 also on empties), so light/camera necessarily belong in the extension.

## 6. The GPU question, answered honestly

Geometry Nodes are evaluated **on the CPU** (multithreaded), in every version up to and including 5.3 beta. According to the
GN workshop of September 2026, GPU evaluation is a "long-cherished goal" in the design stage: opt-in per node, only attributes/lists/grids, Vulkan/Metal-focused,
with no release target. Volume grids run on the CPU via OpenVDB. So for v3 there is no GPU acceleration of the nodes that one could
use reliably or at all. Custom GPU compute shaders via the Python `gpu` module would be backend-dependent (OpenGL/Vulkan/Metal) and
exactly the opposite of "reliable on all GPUs".

What runs on the GPU and works on all supported GPUs: EEVEE (OpenGL, Vulkan, Metal), Workbench, GPU subdivision, the viewport compositor,
Cycles (CUDA/OptiX/HIP/Metal/oneAPI). Consequence for v3:
- Design the GN side for CPU efficiency: keep instances as long as possible, realize only at the end, no dense grids, limit SDF resolution, Bake node for plate/outline, For Each zones only where fields are not enough.
- Keep the render side backend-neutral: materials without legacy EEVEE tricks, no backend-specific shaders; 5.3 makes Vulkan the default on Windows/Linux, macOS has been Metal-only since 4.0, removal of OpenGL is being discussed for 6.0 (not decided).
- Adopt the hardware minimum requirement like Blender 5.2 itself (2 GB VRAM, OpenGL 4.3 / Vulkan 1.3; 5.3 lowers it to Vulkan 1.1).

## 7. Versioning in Git (node trees as code)

Blender has no official text/JSON format for node trees and does not plan one; the official distribution unit is the node group asset in a .blend with a catalog file.
For a repo this means:

| Tool | License | As of | Role |
|---|---|---|---|
| nodebpy (Brady Johnston) | GPL-3+ | PyPI 520.35.1, Oct. 2026, follows Blender 5.2, Python ≥ 3.13 | Python builder, typed, very active. Candidate for the source of truth. |
| plain `bpy` (`interface.new_socket/new_panel`, `nodes.new`) | – | – | Alternative without dependency, more boilerplate. |
| NodeToPython | GPL-3 | v4.2.0, Aug. 2026, 4.2–5.2 | For bootstrapping only: prototype in the editor, export to Python, transfer into the builder. |
| Tree Clipper | GPL-3 | v0.1.12, Sept. 2026, 5.0 | JSON snapshots for diffs/reviews; vendor the core instead of an add-on dependency. |
| geometry-script, geonodes, NodeKit, pynodes | mixed | 2025 / no license / immature / archived | Do not use. |

Proposal: `src/nodegroups/*.py` (one builder per group) → `blender -b --python build_assets.py` produces `assets/easytext_v3.blend` + catalog + JSON snapshots as a
CI artifact. The .blend is never edited by hand. Headless build in CI via the `bpy` wheel from PyPI (5.2 needs Python 3.13) or a Blender download in GitHub Actions.
Note: this cloud session runs Python 3.13; whether the `bpy` 5.2 wheel can be installed here (size, proxy) I have not yet checked. If so, we can build and test
node groups directly here, without you having to open Blender every time.

## 8. Breaking changes that affect us in the rebuild

- 4.0: `tree.inputs/outputs` → `tree.interface` with panels; `socket_type` is the base type (`NodeSocketFloat`), set the subtype afterwards.
- 4.1: dynamic sockets (Switch, Store Named Attribute) → in Python only via socket identifier, never via index. Rotate Euler → Rotate Rotation.
- 4.2: modifier inputs statically typed; EEVEE material properties renamed.
- 4.5: Curve to Mesh gets a "Scale" input instead of an implicit radius (behavior change).
- 5.0: files readable only from 4.5 onwards, Random Value returns different integers, `material.use_nodes` always True.
- 5.1: node tools need unique operator IDs (re-save), Python 3.13, user site-packages no longer loaded.
- 5.2: `modifier["Input_x"]` → `modifier.properties.inputs.<identifier>.value`; Compare/Random Value identifiers changed; re-save node tool assets.
Consequence: v2.1 is not migrated but rebuilt; v2.1 serves only as a behavior reference (the dumps are in `docs/reference/v2.1-dump/`).

## 9. Decisions with a reasoned proposal

1. **Minimum version: Blender 5.2 LTS only.** The font socket (5.1) is the only way to choose the font in the modifier; string fields, Split/Trim, lists and Mesh Bevel (5.2) spare us Python crutches; the modifier property API was reshaped in 5.2, and for 4.5 the extension would have to maintain a second code path. 5.2 is LTS until July 2028, 4.5 ends July 2027, i.e. before v3 is mature. A 4.5 build would be a second product with half the feature set.
2. **Package form: node assets plus optional extension.** The assets alone must work as a modifier and render in any file without an add-on (principle of the Blender Essentials; colleagues and render farms need to install nothing). The extension delivers only what nodes cannot do: font scan, multi-line text editor, presets, camera/light rigs, shaping. Rule: the extension produces exclusively native Blender data, never runtime dependencies in the scene.
3. **Pro typography in v3.1, interface in v3.0.** Shaping (uharfbuzz, fontTools, three platform wheels, variable fonts) is the largest single risk block and is only useful once the core and animation are in place. In 3.0 the attribute contract (char/word/line index, pivot, advance, weight) is fixed so that the shaping source can later be plugged in without changes to the animators. An intermediate step for 3.0 is possible: precompute kerning pairs with fontTools (pure Python, MIT) and apply them as an X offset per instance.
4. **Presets for 3.0: eight of them, all from the same five animators.** Typewriter, Pop (scale/fade-in), Drop (fall with bounce easing), Wave, Slide per word, Line reveal, Scramble/Decoder, Bounce (legacy from v2.1). Plus the sound selector (Sample Sound Frequencies, 5.2), because it is just another selector. Write-on needs a stroke pipeline (Trim Curve before Fill) and moves to 3.1. Reasoning: the value lies in the selector and time model; once that is in place, a preset costs an hour, not a day. The Opacity animator needs the material hook (attribute → alpha) from the start, otherwise fade effects are missing in every preset.
5. **Light/camera in 3.0: minimal, but included.** A "Light rig" operator with three presets (three-point, softbox/product, rim/dramatic) as a controller empty with live sliders (intensity, color temperature, orbit) following the pattern of Light It Up/Tri-Lighting. A "Camera" operator with three presets (frontal with fit-to-text via the bounding box, turntable/orbit, dolly-in). Camera shake (Shakify data, CC0) in 3.1. Reasoning: a title without a camera shot is only half the result, and three presets cover most title shots. All as native data, the file renders without the extension.
6. **Builder: plain bpy with our own thin helper layer, not nodebpy.** The builder is the source of truth for years; a third-party library with its own release cadence (nodebpy 520.x) brings API drift into the build chain. A helper of about 200 lines (create node, set inputs, draw links, auto-layout, panels) delivers most of the convenience without a dependency, and NodeToPython exports land directly in this style. nodebpy remains plan B if the helper grows beyond about 500 lines.
7. **Grease Pencil / 2D output: not in 3.0, architecture keeps the door open.** The GP fills were changed in 5.1 (`fill_id`), the curve-to-GP conversion is not lossless according to the release notes, and the goal of v3 is 3D typography with light and camera. Since the glyphs exist as curves before the fill, a later GP output is a separate end node, not a rebuild.
8. **Distribution: GitHub releases first, extensions platform once 3.0 is stable.** GitHub allows quick betas and pre-releases without a review cycle. The extensions platform brings discoverability and auto-updates inside Blender, but requires GPL, no network access and a review per version; bundled wheels are allowed, so nothing stands in the way of the shaping path.
9. **License: GPL-3.0-or-later for code, CC0 1.0 for assets and example scenes.** GPL is mandatory for the extension anyway and allows taking over code from Add Camera Rigs, Tri-Lighting, Camera Shakify, ST2 and Text Helper. CC0 for the node groups removes any uncertainty for users when they embed the groups in their own or commercial files. Consequence: Essentials node groups (license unclear) are not copied but rebuilt ourselves; the example font Monoton stays under its OFL.

## 10. Proposed roadmap (after the discussion)

0. Infrastructure: repo layout, builder skeleton, headless build (bpy wheel or Blender in CI), snapshot export, smoke test (file loads, modifier evaluates).
1. Core: glyph source, layout, mesh (Fill/Extrude/Bevel), materials (EEVEE/Cycles-neutral), modifier UI with panels/menus/gizmos/warnings.
2. Animation: attribute contract, selectors, animators, time model, 8–10 presets.
3. Scene: extension with N-panel, presets, multi-line text editor, font picker, camera and light rigs.
4. Pro typography: shaping path, variable fonts.
5. Polish: base plate/outline via SDF, bake, export helpers, docs, extension package.
