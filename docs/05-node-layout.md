# Node layout rules

How the generated node groups are laid out so they stay readable and pleasant in the node editor.
Sources: Blender 5.2 manual, the bundled Essentials node groups (measured), Node Arrange / nodebpy layout,
community practice. See the research notes in the commit history for details.

## Conventions taken from Blender's own assets (5.2 Essentials)

1. Data flows left to right; one Group Output in the last column.
2. Group Input copies sit next to their consumers, one per stage, unused sockets hidden, width 140.
   They are the only custom-coloured nodes: input colour (0.510, 0.208, 0.298), the theme's Input class.
3. Frames per stage, 10–25 nodes each, nested at most two deep, `shrink` on, label size 20, no custom colour.
   Labels are short Title Case stage names ("Transfer Attributes", "Band V"); explanations go into a frame text.
4. Reroutes are bus lines, not decoration: only where a link would cut across other nodes; the first reroute of a
   bus carries the data name as label ("Radius", "Mesh").
5. Only trivial math and logic nodes are collapsed (Math, Vector Math, Compare, Boolean Math); their width fits the text.
   Nodes a user may tweak stay open.
6. Node labels are rare and intentional: constants and intent ("Half Depth", "Is Straight"). Built-in titles otherwise.
7. Utility groups start with "." so they stay out of menus; user-facing names are Title Case without abbreviations.
8. Group appearance is set on the group: `color_tag` by role (GEOMETRY transforms geometry, INPUT provides fields or
   constants, ATTRIBUTE stores or captures attributes, CONVERTER is math utility), a description, and a default node width.
9. Group sockets live in panels; advanced panels default to closed; a panel toggle only where a boolean truly gates the panel.
10. No viewer nodes, no muted nodes, no unused nodes in shipped groups.

## Layout algorithm

The builder lays out every group headless (Blender has not drawn the nodes, so sizes are estimated from the rows a node
draws). The pipeline follows Node Arrange, the add-on the Geometry Nodes team intends to port into Blender:

1. Columns by longest path from the group inputs; sources are pulled next to their consumers.
2. Long links get reroute stations only at bend points (one after the source, one before the target).
3. Order within a column: the geometry trunk first, then by the barycentre of the predecessors.
4. Vertical placement keeps the primary link of every node horizontal (socket to socket), the rest stacks below.
5. Frames are stages: a frame comes after the frames that feed it; independent frames stack vertically.
6. Positions snap to the 20 px node grid.

Theme-level looks (noodle curving, wire colours, dashed field links) are not stored in the asset and are left alone.

## Control panel (Easy Text)

The node-editor front end follows the v2.1 GUI (see `docs/01-analysis-v2.1.md`) and uses what Blender 5.2 draws
itself: frames, group nodes with their input widgets, reroutes and wires.

1. The group nodes are the panels. Every control is an input of one of three nodes, shown as a widget on the node
   (text field, slider, dropdown, checkbox, font and material picker). No value nodes, no wire per control.
2. Reading order is the user's order: `1. Text Input` (four line fields), `2. Font Settings` (font, alignment,
   spacing, text box), `3. Mesh Settings` (shape with bevel, material, UV; outline closed), `4. Animation`
   (animate switch with timing, move, rotate, scale; reveal, bounce and output closed), `Result`.
   Panels inside a node are ordered the same way: what is touched most comes first, advanced panels start closed.
   The pipeline stays inside the nodes; Tab shows it.
3. Headings in the ASCII style of v2.1: panel and frame titles read `-=| Name |=-`, nested panels `-- Name --`
   (`core.heading`, `core.subheading`). In 5.2 they are real panels: collapsible, nested, with a switch in the
   header where a boolean gates the panel (Bevel, UV).
4. Three wires, each with a labelled reroute as a marker between the sections (`text`, `glyphs`, `mesh`). The
   markers sit on the socket level of both ends, so the wires run straight; the node positions are tuned for it.
5. Colours as in v2.1 and used as signals: dark teal outer frame, lighter teal sections, an accent rule under the
   title, the Text Lines node tinted red (the v2.1 string nodes), Text Settings teal, Mesh Generation green,
   Animation amber (motion), purple tip boxes and note. Tips are fixed-size frames with frame text, one per section, text size 14; the export note
   and a small footer are the same element.
6. Panel nodes hide what a user does not need: the data-block selector (`show_options` off), unlinked outputs
   meant for builders (Character Count), the "Named Attributes" overlay. Nothing is selected when the file opens,
   the sidebar is off, the view is framed on the panel. The bevel is on by default because that is the look people
   want first.
7. `ET Text Mesh` is the same three nodes with Group Input copies instead of widgets, so both trees are always
   wired identically; its interface keeps plain panel names for the properties editor.
