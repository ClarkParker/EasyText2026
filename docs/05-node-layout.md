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
