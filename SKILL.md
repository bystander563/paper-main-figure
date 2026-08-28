---
name: paper-main-figure
description: Create story-bound, scientifically faithful, editable vector main-method figures for research papers. Use for a paper's main method overview, architecture, mechanism, or training/inference pipeline after the scientific story is fixed. Do not use for ordinary data plots or decorative illustrations.
metadata:
  version: "2.4.0"
---

# Paper Main Figure

Create the paper's central method figure as a scientific argument, not a
decorative flowchart. The primary output is an editable vector source and a
verified vector export. Image generation may explore composition, but a
generated bitmap is never the camera-ready master.

## Orchestrated precondition

When called by a paper workflow, require an explicitly approved story packet
and bind the figure contract to its SHA-256. Read the approved thesis,
problem--gap--mechanism chain, contribution hierarchy, explicit non-claims,
method definition, terminology ledger, and venue/placement contract.

If the proposed figure changes the thesis, mechanism, contribution hierarchy,
or evidence interpretation, stop and reopen story approval. A visual
simplification that preserves those facts does not create another user gate.

## 1. Freeze the main-figure contract

Write `MAIN_FIGURE_CONTRACT.md` before drawing. Record:

- exact story-packet identity and source records;
- the one message a reader should understand in three seconds;
- intended manuscript role and placement width;
- required entities, labels, symbols, and canonical edges;
- training-only versus inference-time information;
- forward, update, comparison, and evaluation edge semantics;
- forbidden claims/content;
- output formats and final-size typography target.

Also write `FIGURE_FACTS.md`. Separate source facts from visual
simplifications. Never invent a module, loss, dataset role, output, or arrow to
make the composition look balanced.

## 2. Lock topology before style

Write a canonical node/edge map. For code-backed architectures, inspect the
active execution path rather than inferring it from class names. A label or
group may be simplified for the paper, but the redraw may not add or remove a
scientific dependency.

Explicitly distinguish data flow, supervision/loss consumption, parameter
update, inference flow, and evaluation-only computation. Every loss arrow must
terminate at the component it updates. Privileged training inputs must not
visually feed deployment inference. Metrics must not look like model inputs or
predictions.

## 3. Choose visual grammar from the method

Do not force every method into three equal colored panels. Use stage panels,
parallel lanes, a hierarchy, or a comparison inset only when the verified graph
supports that structure.

For a staged method:

- give the innovation-bearing region the most space;
- align repeated modules to one grid;
- align module centers with their arrow ports;
- keep shared row heights, padding, border weights, and label baselines;
- use one short shared trunk for fan-out/fan-in rather than parallel detours.

When the reference or method calls for a dense stage-board style, treat each
stage as a compact scientific UI rather than one oversized card. Fill the
board with aligned nested modules, header strips, badges, state chips, compact
bars, gauges, or semantic icons that encode real entities. Prefer several
medium modules over a few giant boxes. Keep residual whitespace narrow and
intentional; do not enlarge type or cards merely to occupy space.

Keep badges and chips fully inside their owning header or module. Their bounds
must clear divider lines, borders, titles, and neighboring labels; a badge may
not sit on top of a header separator merely to save space.

Read `references/stage-panel-style.md` when stage panels fit the method. A user
or venue style reference overrides its palette, but never overrides the
scientific graph.

## 4. Enforce connector simplicity

Treat connector complexity as a hard layout constraint:

- prefer direct horizontal or vertical arrows;
- an ordinary connector may use at most one 90-degree elbow;
- if an edge needs more than one elbow, move or resize modules and reroute;
- connect through explicit center-aligned ports;
- use a short shared spine for one-to-many or many-to-one relations;
- avoid crossings, diagonal segments, curves, loops around the canvas, and
  arrows that travel through unrelated modules;
- distinguish update/control edges with dash pattern or label, never color
  alone.

In a dense stage-board figure, connectors are visually subordinate: use lines
and arrowheads lighter/smaller than module borders, keep them short between
adjacent ports, and let panel/card grouping carry most of the hierarchy. Do
not use thick arrows as decorative separators.

## 5. Design at final publication size

Resolve the official venue width before drawing. Use the venue's actual
single-column, double-column, or full-width dimensions; do not design at an
arbitrary pixel size and shrink later.

Defaults when the venue does not specify otherwise:

- editable sans-serif text such as Arial or Helvetica;
- at least 7 pt for essential labels at placed size and at least 5 pt for
  genuinely auxiliary UI labels, unless the venue specifies another minimum;
- restrained palette of 2--4 chromatic hues total, excluding neutral text and
  line colors; stage hues count toward this budget;
- dark neutral text, no colored prose;
- no red/green-only distinction, rainbow palette, gradients, or drop shadows;
- no giant paper title or subtitle inside the artwork; use the manuscript
  caption and concise stage headers instead.

Before adding a new hue, state the scientific role it would encode. Do not add
a class color or update color when labels, hollow/filled shapes, or solid/dashed
lines already express the distinction. In a multi-stage board, prefer one hue
family per stage and use only tints of that hue inside the stage; keep
cross-stage connectors neutral unless color is scientifically necessary.

Calculate typography from the vector view box and the intended physical
placement, not from the large PNG preview. For example, a full-width ACL-style
figure placed at 160 mm with an 1800-unit view box needs roughly 20 units for
5 pt text and 28 units for 7 pt text. When text fails the final-size check,
first remove repeated explanations, move qualifications to the caption, and
shorten labels; do not rescue the layout by shrinking below the declared
minimum. Keep the main mechanism, inputs, outputs, and training--inference
boundary in the artwork. Move exact parameter counts, implementation prose,
and redundant restatements to the caption or manuscript unless they are the
figure's scientific message.

Avoid slash-separated prose and UI labels. Write `and`, `or`, `per`, a middle
dot, or a short rephrasing instead. Retain `/` only when it belongs to a
canonical formula, unit, metric name, or established domain term whose meaning
would change if rewritten.

## 6. Explore, then redraw as vectors

If a visual reference would materially help, read and use `$imagegen` to create
a composition draft. Treat it as a reference only. Inspect it against the
canonical edge map before reuse.

Rebuild the selected composition as editable SVG, draw.io, PPTX, or another
venue-acceptable vector source. SVG is the default portable master. Preserve
text as editable text, embed fonts in exports when supported, and keep boxes,
groups, and connectors editable. Export PDF/SVG plus a PNG preview.

If vector redraw is unavailable, report `DRAFT_ONLY`; do not call the generated
PNG camera-ready.

## 7. Write the caption as part of the figure

Create a caption with a short title sentence stating the message; an
explanation of stages/panels; definitions for symbols, line styles, and
abbreviations; and the training/inference boundary when relevant. Move prose,
caveats, and method detail into the caption when they need not be read inside
the artwork.

## 8. Run semantic, visual, and export QA

Read `references/qa-checklist.md`. Inspect the vector master and a render at the
exact intended placement size. Also inspect a thumbnail and grayscale view.

Reject and iterate if any edge is wrong, a training-only input reaches
inference, text is unreadable, modules drift off-grid, a connector needs
multiple elbows, arrows dominate the thumbnail, unexplained empty regions
remain, labels are rasterized, fonts are missing, colors carry meaning alone,
the palette contains unexplained competing hues, or the exported/captioned
figure disagrees with the manuscript.

Make one targeted revision at a time and preserve already-correct topology,
alignment, typography, and connector routing.

## Deliverables and verdict

Return `MAIN_FIGURE_CONTRACT.md`, `FIGURE_FACTS.md`, editable vector source,
PDF/SVG export, PNG preview, final caption, and `MAIN_FIGURE_QA.md` tied to
exact file hashes. Report `DRAFT_ONLY`, `PAPER_READY`, or `CAMERA_READY`.

`CAMERA_READY` requires correct topology, editable vector text/shapes,
venue-sized legibility, embedded/valid fonts, accessible color semantics, and
a rendered inspection of the exact export used by the manuscript.

