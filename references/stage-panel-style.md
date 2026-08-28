# Stage-panel visual grammar

Use this grammar only when the method genuinely has stages or responsibility
levels. Panel count and widths follow the verified topology, not a fixed
three-panel template.

## Grid and alignment

- Establish a common baseline/grid before placing modules.
- Align stage tops/bottoms and repeated row heights.
- Align module edges and centers across related rows.
- Put input/output ports on module centerlines.
- Keep inner padding, corner radius, and border width consistent.
- Let the innovation-bearing stage occupy the most width, without creating
  mostly empty neighboring panels.
- For a dense stage-board reference, target roughly 85--95% useful occupancy
  inside each panel. Use nested cards and compact rows to carry information;
  do not create occupancy by inflating one box or the stage title.

## Dense scientific UI components

- Use small header bands to make module ownership obvious.
- Keep header badges clear of title text, separator rules, and the header
  border; a visible gap must remain on every side.
- Use aligned state cards, tags, probability bars, gauges, token strips, or
  semantic icons when they encode a real object already in the fact pack.
- Repeat one component grammar across comparable modules.
- Keep the largest blank region smaller than a normal module footprint unless
  it has an explicit grouping or separation purpose.
- Icons support recognition but never replace canonical scientific labels.
- Avoid `/` as a compact substitute for ordinary words in visible labels;
  preserve it only in canonical notation or established terminology.

## Connectors

- Direct horizontal/vertical arrow first.
- At most one 90-degree elbow for an ordinary edge.
- More than one elbow means the layout must be changed.
- Fan-out/fan-in uses one short shared trunk with aligned branches.
- Use solid arrows for forward flow and a dashed arrow for update/control.
- Do not use diagonal routes, curves, canvas-spanning loops, or arrows through
  unrelated modules.
- Keep connectors thinner and arrowheads smaller than primary module borders.
  At thumbnail size, the panels and cards—not the arrows—must define the
  composition.

## Typography and color

- Default to Arial/Helvetica-compatible sans serif.
- Design at the official physical placement size; essential labels should be
  at least 7 pt unless the venue explicitly specifies another minimum.
- Use dark neutral text and 2--4 chromatic hues total. Stage hues count toward
  the total; neutral text and connector colors do not.
- Use one hue family plus light tints inside each stage. Do not mix global
  human/AI/update colors into a stage when labels, shape fill, or dash pattern
  already conveys those roles.
- Keep ordinary and update connectors neutral; distinguish them by solid versus
  dashed line style and an optional short label.
- Make grouping, labels, borders, and line style carry meaning redundantly.
- Avoid red/green-only distinctions, colored prose, gradients, shadows, and
  icons that do not encode a supported entity.

## Artwork boundary

- Omit a large paper title or subtitle inside the figure by default.
- Use concise stage/module labels; move explanations to the caption.
- Stage headers may be flat bands or compact chevrons when they clarify
  hierarchy, but they must share a common baseline and height.


