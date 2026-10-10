# Easy Text Geometry Node – Analysis of Version 2.1 (Blender 3.2)

Part 1 of 2 (Part 2: `02-target-v3.md`). As of: 2026-10-10. Basis: the uploaded file `easy-text-geometry-node.blend`
(zstd-compressed, header `BLENDER-v302`, i.e. saved with Blender 3.2 from 2022).
The file was read without Blender using a custom parser
(`tools/dump_blend.py`, raw dumps in `docs/reference/v2.1-dump/`).

## 1. Contents of the file

| Block | Name | Remark |
|---|---|---|
| Scene | `upload` | 1920x1080, 24 fps, frames 1–250, engine `BLENDER_EEVEE` (legacy EEVEE). **No camera, no world, no lights.** |
| Object | `Easy Text Geometry Node` | Mesh `Cube.001` (8 verts, carrier only), scale 0.839. Modifier stack: Geometry Nodes → Bevel → SimpleDeform (disabled). |
| NodeTree | `EasyTextGeometryNodeV2.1` | Main group, 17 nodes. Only one input (Geometry), **no exposed parameters**. |
| NodeTree | `Geo_LineCombinerNodeGroup` | 56 nodes (43 reroutes). Joins up to 4 text lines with a line break. |
| NodeTree | `LogicBoardNodeGroup` | 72 nodes (59 reroutes, 10 switches). Pure Boolean logic board for "1/2/3/4 lines". |
| NodeTree | `Geo_MeshGenerationNodeGroup` | 119 nodes (60 reroutes, 11 switches). 33 group inputs. Mesh, material, animation, bevel plate. |
| NodeTree | `Tex_NoiseNodeGroup` | Shader group (Noise → Bright/Contrast → Mix → Bump). |
| Material | `Text Top`, `Text Side` | Principled BSDF (metallic 1.0) with noise roughness and bump. Red / green. |
| VFont | `Monoton Regular` | packed (Google Fonts, SIL OFL). |
| Text | `EditText`, `ExportMesh` | one usage hint sentence each, attached to frames as a note. |
| Action | `Geo_MeshGenerationNodeGroupAction` | a single keyframe (frame 96) on `Switch.005` in the mesh group. |

Nodes in total: 270 in the geometry groups, of which 166 are reroutes (61 %).

## 2. Data flow (as v2.1 works)

```
String ×4 (fixed: "Easy", "Text", "Geometry", "Node")
   └─> Line Combiner  (4 Bool switches "1/2/3/4 Lines of text" → Logic Board → Join Strings with Line Break)
         └─> String to Curves  (Font Monoton, Size 0.9, Align X = Center, Align Y = Middle, Line Spacing 0.8)
               └─> "Curve Instances" (one instance per character)
                     └─> Mesh Generation
                           ├─ Resample Curve (Evaluated) → Fill Curve (N-Gons) → Extrude Mesh (Faces) → Flip Faces (bottom)
                           ├─ Join → Realize Instances → Set Material (Top / Side) → Merge by Distance → Set Shade Smooth
                           ├─ Animation: Position → Separate XYZ → ×"Animation Driver x|y|z" → Float Curve → Scale Instances (3×) → Rotate Instances
                           └─ Bevel plate: Grid (Subdivision up to 2000²) → Geometry Proximity to the text → Map Range → Set Position (Z) → material shift
                                 └─> Realize Instances → Group Output
   └─> Object modifier: Bevel (edges) → SimpleDeform (off)
```

## 3. What v2.1 can do

- Up to 4 text lines, one font, size, character/word/line spacing, text box width.
- Extrusion with separate top and side materials, Shade Smooth, Merge by Distance.
- A "letter bounce" animation: per axis on/off, invert, strength 0–1, easing via three Float Curves,
  the driver is a vector that the user has to animate by hand ("Animation Driver x|y|z").
- A global rotation of all character instances.
- A "Beveled Plate" (base plate with a bead around the letters) via proximity on a dense grid.

## 4. Weaknesses (sorted by weight)

1. **No modifier UI.** The main group exposes nothing. The note in the file literally says: "To edit your text ... open a Geometry Node Editor." Every parameter is set in the node editor on the group nodes. For users this is the biggest hurdle.
2. **Headings as fake sockets.** Because Blender 3.2 had no panels, 8 of the 33 inputs are empty float sockets with names like `=========General Settings=========` or `^^^^^^^!CAREFULL OVER 1000!^^^^^^^`. This is exactly what interface panels (since 4.0) and the Warning node replace.
3. **Multi-line text is a logic detour.** Four fixed String nodes, four Bool switches and a 72-node "Logic Board" of chained switches just to decide how many lines get joined. With an integer "Lines" or Menu Switch (4.1) plus Join Strings this takes a dozen nodes.
4. **Reroute spaghetti.** 61 % of the nodes are reroutes. The groups are effectively unmaintainable and cannot be diffed.
5. **The bevel plate scales quadratically.** A grid with `Subdivision²` vertices (default 300² = 90,000, allowed up to 2000² = 4 million) plus Geometry Proximity per vertex. Hence the "Danger" labels. Today this is done with SDF volume grids (Mesh to SDF Grid → Grid to Mesh) or Mesh Boolean, and you get a true rounding at constant cost.
6. **Animation is neither time-based nor selective.** No Scene Time, no typewriter, no selection by character/word/line, no offset/stagger, no ease-in/out per character. The user has to keyframe a vector. The "bounce" scaling depends on the world position of the letters (Position → Separate XYZ), not on the character index, so it behaves differently when the object is moved.
7. **Stray keyframe in the node group.** The only keyframe (frame 96) lives as an action on `Geo_MeshGenerationNodeGroup`, i.e. on the group itself. Anyone who appends the group gets this animation along with it.
8. **Font is a node property, not a socket.** In 3.2 `String to Curves` carries the font as a node property; changing the font is not possible in the modifier UI. (A font socket exists only since Blender 5.1, see Part 2.)
9. **Materials are legacy EEVEE / Principled 3.x.** Sockets like `Subsurface Color`, `Specular`, `Clearcoat` have existed differently since 4.0 (versioning catches it, but they should be rebuilt). No world, no light, no camera: rendering is not part of the package, even though it is the goal of v3.
10. **Three Realize Instances steps**, Merge by Distance on the whole mesh and Resample "Evaluated" on all glyphs: works, but costs unnecessarily much for long texts.
11. **Small things.** Typos in socket names (`Bevel With`, `Bevel Hight`), no tooltips/descriptions, no min/max on most floats, `Shade Smooth` has `default_attribute_name = "1"` (random value).

## 5. What should be carried over from v2.1

- The basic principle **"String to Curves → Curve Instances per character → Fill → Extrude → Realize at the end"** is right and remains the core. Instances per character are the basis for any per-character animation.
- Separate top/side material via the `Top`/`Side` selections of Extrude Mesh.
- The idea of easing via Float Curves (in v3 as a menu with fixed easings plus an optional custom curve).
- The idea of a base plate, but built differently.
- The font Monoton (OFL) as the example font.
