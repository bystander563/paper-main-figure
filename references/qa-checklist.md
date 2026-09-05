# Main-figure QA checklist

The completed `MAIN_FIGURE_QA.md` begins with this machine-readable receipt;
the manifest creator and validator reject missing, duplicate, stale, or failed
fields:

```markdown
- Verdict: DRAFT_ONLY | PAPER_READY | CAMERA_READY
- Story packet SHA-256: <64 hex>
- Placement width mm: <number>
- Editable master SHA-256: <64 hex>
- Vector export SHA-256: <64 hex>
- Layout spec SHA-256: <64 hex>
- Layout audit SHA-256: <64 hex>
- Scientific topology: PASS | FAIL
- Connector simplicity: PASS | FAIL
- Final-size typography: PASS | FAIL
- Rendered inspection: PASS | FAIL
- Layout coverage: PASS | FAIL
- Hard alignment: PASS | FAIL
- Internal padding and centering: PASS | FAIL
- Stroke consistency: PASS | FAIL
- Symbol and box semantics: PASS | FAIL
- Soft dispositions: PASS | FAIL
- SVG export equivalence: PASS | FAIL
- Information retention: PASS | FAIL
- Reference comparison: PASS | FAIL | NOT_APPLICABLE
- Composition grid: PASS | FAIL
- Panel occupancy: PASS | FAIL
- Unexplained whitespace: PASS | FAIL
- Optical alignment: PASS | FAIL
- Vector integrity: PASS | FAIL
- Font integrity: PASS | FAIL
- Color accessibility: PASS | FAIL
```

The last three PASS fields are mandatory for `CAMERA_READY`; all earlier
scientific, visual, layout, disposition, and equivalence fields are mandatory
from `PAPER_READY` onward.

## Story and source fidelity

- [ ] Figure contract identifies the exact approved story packet.
- [ ] `MAIN_FIGURE_MANIFEST.json` validates against the exact approved story packet and required verdict.
- [ ] One-message takeaway matches the paper's thesis and contribution order.
- [ ] Every entity, label, symbol, and edge has a source.
- [ ] Visual simplifications are recorded and do not change topology.
- [ ] Forbidden claims and non-claims do not appear.
- [ ] The bounded content-retention contract uses `STORY_ONLY` or
      `REFERENCE_FLOOR` and every unit is anchored in the story or fact pack.
- [ ] A newly drawn figure uses content-contract schema 2, declares its
      schematic route, freezes a near-zero formula budget, and maps every
      visible unit to exactly one macro region.
- [ ] Every schema-2 visible unit declares `VISUAL_OBJECT`, `RELATION`, or
      `SHORT_LABEL`; caption and optional-drop units use matching carriers.
- [ ] Every macro region includes a real visual object or relation and a
      nontrivial wordless skeleton component; no region is a collection of
      labels inside boxes.
- [ ] Every `VISIBLE` unit occurs inside its registered SVG components and
      every `CAPTION` unit occurs in the caption.
- [ ] A reference-bound redesign preserves each reference-present scientific
      unit unless an `OPTIONAL_DROP` rationale is explicit and scientifically
      justified.
- [ ] Every unique visible text node in an SVG reference is dispositioned by a
      content unit or an explicit `reference_omissions` entry; the audit reports
      no unclaimed reference text.
- [ ] Every renamed reference item has an explicit `reference_rewrites` mapping
      to a required visible or caption token.
- [ ] A raster-only reference remains `DRAFT_ONLY`; `PAPER_READY` uses an SVG
      reference with a machine-verifiable exhaustive inventory.

## Scientific topology

- [ ] Data, supervision, update, inference, and evaluation edges are distinct.
- [ ] Losses terminate at their actual consumers/update targets.
- [ ] Training-only information does not feed inference.
- [ ] Evaluation metrics are downstream measurements, not model inputs.
- [ ] The final prediction comes from the correct model and inputs.
- [ ] Every model-input arrow preserves the sourced granularity; a sentence-wise
      classifier is fed by a highlighted or extracted sentence, not by a whole
      document boundary.

## Alignment and connector simplicity

- [ ] `FIGURE_LAYOUT_SPEC.json` was frozen before drawing and is bound to the
      current story, contract, facts, width, and body font size.
- [ ] New candidates use layout-spec schema 2 and measured-v1. Every visible
      macro panel has exactly one `panel_occupancy` diagnostic with eligible
      scientific contents and ordinary reference modules. A SOFT finding needs
      a rendered, substantive disposition; it cannot silently become PASS.
- [ ] Every visible semantic primitive is owned by its nearest registered
      semantic component; no broad group owns multiple independent boxes and
      coverage is exactly 100 percent.
- [ ] Every card, chip, and panel either joins a multi-member family or records
      a substantive reason why no corresponding peer exists.
- [ ] Repeated families are not marked `FREE` and every member participates in
      a `HARD` check.
- [ ] Every `SOFT` check has exactly one `ADJUSTED` or `KEPT_WITH_REASON`
      disposition; no soft mismatch is silently ignored.
- [ ] Every `FREE` component has a pre-drawing scientific noncorrespondence
      reason.
- [ ] Stage boundaries, module edges, centers, and repeated rows share a grid.
- [ ] Repeated tags share baselines; repeated cards and cells share size,
      padding, border weight, and intended edge anchors.
- [ ] Labels are centered within their owning regions on the declared axis;
      right, left, top, and bottom padding all clear the minimum.
- [ ] Ports are aligned to module centerlines.
- [ ] Every ordinary arrow is straight or has at most one 90-degree elbow.
- [ ] Fan-out/fan-in uses a short shared trunk.
- [ ] No connector crosses or traverses an unrelated module.
- [ ] Ordinary flow uses straight or single-elbow routes. Necessary graph edges
      and feedback exceptions are source-grounded, typed and visually inspected;
      this rule must not delete a real dependency.
- [ ] Connectors and arrowheads are visually weaker than module borders.
- [ ] At thumbnail size, grouping comes from panels/cards rather than arrows.

## Density and component grammar

- [ ] Dense references are matched with scientific micro-objects such as
      documents, sentence or token strips, states, codebooks, model structures,
      selection marks, output marks, or schedules—not repeated prose cards.
- [ ] Geometry was not improved by collapsing several reference scientific
      blocks into one generic card or by deleting comparison and deployment
      constraints.
- [ ] Useful content occupies the panel without unexplained large blank zones.
- [ ] Large panel backgrounds remain comfortable. Comparable lanes share rails;
      distinct processes may use different internal layouts.
- [ ] Large blank-region diagnostics were inspected for missing content,
      unbalanced rails or a legitimate grouping/route purpose. Their ratio is
      not a universal aesthetic threshold and does not justify filler.
- [ ] Labels, connectors, formulas, symbols, outlines, panel backgrounds, and
      invisible geometry do not count as occupancy.
- [ ] No reference-present unit was deleted, no distinct roles were merged,
      and no box was inflated merely to satisfy the occupancy gate.
- [ ] Macro panels establish the first scan; micro modules carry local detail;
      the innovation-bearing region has the most area or structural richness.
- [ ] Repeated documents, state strips, tokens, nodes, cards, header bands,
      bars, and icons use a consistent grid.
- [ ] Every icon or micro-visual encodes a supported entity or state.
- [ ] Ignoring prose leaves the input, mechanism, output, major object types,
      and training--inference boundary recognizable.
- [ ] A `VISUAL_OBJECT` contains real painted structure rather than one rounded
      rectangle plus text; a `RELATION` contains connector geometry.
- [ ] Standalone symbols and formulas have authoritative meanings and caption
      definitions; unexplained `#` or decorative notation is absent.
- [ ] Displayed equations do not exceed the frozen route budget: zero by
      default and at most one for ordinary overviews. Authoritative identifiers
      and subscripts are registered symbols, not automatically equations.
- [ ] Formula-like visible text is detected automatically; Unicode scripts,
      indexed variables, fractions, and objective names cannot hide inside a
      generic card or label.
- [ ] A formula or symbol is boxed only when the box encodes a documented
      module, state, choice, interaction, input, output, group, or legend.
- [ ] No badge, chip, or label touches or crosses a header separator or border.
- [ ] Document and page icons have complete, closed outer contours at final size.
- [ ] Visible `/` characters occur only in canonical notation, units, metrics,
      or established domain terms.

## Final-size typography and accessibility

- [ ] The figure was inspected at its exact manuscript placement size.
- [ ] The minimum font was computed from view-box units and physical placement,
      not judged from an enlarged PNG preview.
- [ ] Essential text meets the venue minimum and is at least 7 pt by default;
      genuinely auxiliary UI labels are at least 5 pt by default.
- [ ] Repeated prose and exact implementation details were moved to the caption
      before any label was reduced below the declared minimum.
- [ ] Text uses one editable paper-compatible family; repeated modules use the
      same family, weight rules, and wrapping behavior.
- [ ] Actual font files and glyph coverage are verified. No character-count
      width estimate, missing-glyph box or unreported font substitution passes.
- [ ] Every label declares a fixed painted owner and an intended content region;
      the measured-v1 audit passes. Containers are not unions with their labels.
- [ ] Body centering excludes headers, repeated tag baselines align, and
      icon-label pairs are centered by their combined visible bounds.
- [ ] Text does not overlap boxes, arrows, other labels, thick bars, or any
      stroked line; the audit expands strokes by half their rendered width.
- [ ] Same-line headings retain positive separation at the declared font and
      physical placement; they do not merge or merely touch.
- [ ] Color is not the only carrier of meaning.
- [ ] Grayscale and color-vision-deficiency checks preserve distinctions.
- [ ] Every non-neutral hue has a stated role; stage hues are included in the
      total palette budget.
- [ ] Class and update semantics do not add redundant competing hues when
      labels, shapes, or dash patterns already suffice.
- [ ] No unsupported icon, gradient, shadow, or colored prose adds noise.
- [ ] A gauge appears only when a sourced threshold or operating point makes
      that shape scientifically meaningful; ordinary probabilities are shown
      on their output object.

## Vector/export integrity

- [ ] Editable source is present.
- [ ] Text remains text rather than outlines or bitmap pixels.
- [ ] PDF/SVG export uses embedded/valid fonts and no external linked assets.
- [ ] Export is not clipped and matches the editable source.
- [ ] PNG is identified as a preview, not the master.
- [ ] Contract, facts, layout spec, dispositions, recomputed layout audit,
      master, audit SVG, export, preview, caption, QA, and accessibility
      decision are all hash-bound in the schema-2 manifest.
- [ ] The audit SVG and formal export expose the same visible text and pass the
      independent-render comparison, including local outlines and text.
      A same-engine screenshot comparison alone is not sufficient.

## Caption and manuscript fit

- [ ] Caption states the message, explains panels, and defines symbols/styles.
- [ ] Figure and caption can be understood without unsupported manuscript text.
- [ ] Figure is cited in the correct section and earns its space.
- [ ] LaTeX/Word uses the intended width without later downscaling.
- [ ] `REFERENCE_FLOOR` reference and candidate renders were compared at the
      same physical width; content retention and scan order both passed.
- [ ] A candidate has not silently replaced a previously user-approved figure.

Scientific topology, retained information, measured text layout, final-size
readability and export integrity must pass before PAPER_READY. Geometry scores
alone never certify aesthetic quality. Resolved SOFT whitespace diagnostics may
be kept with a recorded visual reason; unresolved visual defects block readiness.
An unapproved historical or synthetic test fixture remains DRAFT_ONLY.
