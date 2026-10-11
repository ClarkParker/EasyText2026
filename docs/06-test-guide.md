# Test guide (first round, Blender 5.2 LTS)

Everything below was verified here with Blender 5.2.0 (headless builds, Cycles renders, and real windows on a
virtual display). What cannot be checked here: the feel on your monitor, your system fonts, EEVEE in the
viewport, and the K-Cycles build. That is what this round is for.

## What to download

| File | Where | What for |
|---|---|---|
| `easytext_v3_demo.blend` | repo `assets/` or CI artifact `easytext_v3-assets` | Opens in the workspace "Easy Text": camera view, control panel, light rig, orbit. |
| `easytext_v3.blend` | same | Asset library with every node group; append or register as asset library. |
| `easy_text-3.0.0.zip` | CI artifact `easy_text-addon` or `python -m easytext_build.package` | The add-on: Preferences → Get Extensions → ⌄ → Install from Disk. |

## 1. Demo file (5 minutes)

1. Open `easytext_v3_demo.blend`. Expected: workspace "Easy Text", camera view on top with the text on a plate,
   the control panel below, properties on the modifier tab, nothing selected.
2. Press Space. Expected: the letters rise and turn into place one after the other, the camera travels around
   the text, the plate stays put. Frame range 1–120.
3. In the control panel, type into **1. Text Input**, change the font in **2. Font Settings** (the font picker is
   the "F" field), Depth and Bevel in **3. Mesh Settings**, Order and Easing in **4. Animation**.
4. Switch the viewport to Material Preview and Rendered (EEVEE and Cycles). Expected: three lights from the rig,
   the plate dark, the letters light, the bevel golden.

Tell me: zoom level and node widths at opening, readability of the ASCII headings, anything that feels in the
wrong place.

## 2. Mesh quality (10 minutes)

1. Select the text, Tab into Edit Mode on a mesh copy (sidebar → Export → Mesh Copy for Export, or apply the
   modifier on a duplicate). Expected: closed manifold, quads on sides and bevel, n-gon caps, no doubles
   (Select → Select All by Trait → Non Manifold finds nothing).
2. UV Editor with the copy. Expected: planar caps in 0..1 and one continuous band for sides and bevel; no
   stretching along the contour. Try "Normalize to Text" off and UV Scale 2.
3. Bevel Width larger than half the Depth. Expected: the bevel is capped and the modifier shows an info note.
4. Empty text. Expected: a warning on the modifier, no crash.
5. Your own fonts: load a heavy script font and a thin one, Resolution 6 and 24, Simplify 0 and 2. Expected:
   clean fills even with overlapping outlines (Fill Rule Even-Odd vs Non-Zero).

## 3. Add-on (10 minutes)

1. Install the zip, enable it, open the sidebar (N) → tab **Easy Text**.
2. **Create Text**. Expected: an upright text at the cursor, the panel fills with Text, Typography, Shape,
   Material, UV, Plate, Animate, Outline, Output. Menus are dropdowns, materials and fonts are pickers.
3. **System Font** → search popup lists your installed fonts; pick one. **Load Font File** for a file.
4. **Presets**: Headline, Sign, Reveal, Typewriter, Bounce. Play after Reveal and Typewriter.
5. **Camera and Light**: Add Light Rig, Add Camera Orbit, then Fit Camera to Text on a camera without an orbit.
6. **Export**: Mesh Copy for Export, then File → Export → glTF. Expected: UVMap and material slots in the export.

Tell me: missing controls, wrong order, labels you would name differently, anything that needs a tooltip.

## 4. Known limits in this round

- No kerning or OpenType shaping beyond what Blender's String to Curves does (planned as v3.1 with Python
  shaping).
- The light rig instances share one light data-block per role (key, fill, rim); colour and power are set on
  those three source lights in the hidden collection "Easy Text Light Sources".
- A camera that follows the orbit cannot be fitted; remove the Orbit constraint first.
- The control-panel tree has no modifier inputs by design; the sidebar shows a hint and offers a new text with
  sidebar controls.

## How to report

A screenshot and one line per finding is enough. For mesh issues the text and font name; for add-on issues the
line from Window → Toggle System Console (Windows) or the terminal.
