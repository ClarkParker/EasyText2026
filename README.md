# Easy Text 2026 (v3)

Geometry Nodes typography and text animation for **Blender 5.2 LTS**: node-group assets
(work as a modifier without any add-on) plus an optional extension for a font picker,
multi-line text, presets, and camera and light rigs.

Status: Phase 1, first node group `ET Text Mesh` (text → clean mesh with extrusion, bevel, materials, UVs).
Analysis of the previous version: `docs/01-analysis-v2.1.md`, target picture: `docs/02-target-v3.md`,
development rules and API pitfalls: `docs/03-development.md`, architecture: `docs/04-architecture-v3.md`,
node layout rules: `docs/05-node-layout.md`.

## Testing in Blender (5.2 LTS)

1. Download `assets/easytext_v3_demo.blend` (from the repo or the CI artifact) and open it: a text object with the
   modifier, a camera and two area lights are already set up, and the properties editor opens on the modifier tab.
2. For your own file: File → Append → `easytext_v3.blend` → NodeTree → `ET Text Mesh`.
   Alternatively register the `assets/` folder as an asset library in the Preferences; the group then shows up in
   the Add Modifier menu under "Easy Text".
3. Add a Geometry Nodes modifier to any mesh object (or, since 5.2, an empty) and pick `ET Text Mesh`.
4. Modifier panels: Text (4 lines), Typography (font socket, size, alignment, spacing, text box),
   Outline (resolution, simplify, fill), Shape (depth, bevel, smooth angle), Material, UV, Output.

What the group guarantees (verified headless): a closed, manifold mesh without duplicate vertices; caps as n-gons or
triangles; sides and bevel as quads; a `UVMap` with planar caps and one continuous, undistorted UV band for sides and
bevel (U = contour length, V = arc length over back bevel, side, front bevel); materials in the slots Front/Side/Bevel;
warnings for empty text and a bevel that is too wide.

## Layout

| Path | Content |
|---|---|
| `src/easytext_build/` | Builder: generates every node group from scripts (source of truth). |
| `src/easytext_build/groups/` | One file per node group. |
| `assets/easytext_v3.blend` | Built asset library (never edit by hand). |
| `assets/easytext_v3_demo.blend` | Demo scene for a quick look. |
| `assets/blender_assets.cats.txt` | Asset catalog. |
| `assets/snapshots/*.json` | Text snapshots of the node groups for diffs and reviews. |
| `tools/dump_blend.py` | Reads a .blend without Blender (for reference files). |
| `docs/` | Analysis, target picture, development rules, architecture, reference dumps of v2.1. |

## Building

Requires Python 3.13 (like Blender 5.2). The `bpy` wheel is Blender as a Python module (~400 MB), pinned to 5.2.0.

```bash
python -m pip install -e ".[dev,bpy]"
python -m easytext_build.build     # builds assets/easytext_v3.blend, the demo, catalog and snapshots
python -m easytext_build.smoke     # loads the file, attaches the modifier, checks the result
pytest                             # tests without Blender
```

Alternatively with a Blender installation:

```bash
blender -b --python-expr "import sys; sys.path.insert(0, 'src'); import easytext_build.build as b; b.main()"
```

## License

Code (builder, extension, tools): GPL-3.0-or-later, see `LICENSE`.
Node assets and example scenes under `assets/`: CC0 1.0, see `assets/LICENSE`.
