# Figure Layout Protocol 1.0

This resource is shared, byte for byte, by `paper-main-figure` and
`paper-motivation-figure`. It turns visual alignment from an informal taste
check into a story-bound, machine-recomputed gate.

## Required sequence

1. Freeze the approved story packet and figure contract.
2. Before drawing, write `FIGURE_LAYOUT_SPEC.json`. Register every visible
   semantic component and declare every intended alignment as `HARD`, `SOFT`,
   or `FREE`.
3. Draw an editable SVG audit master. A PPTX or draw.io master is allowed only
   when an equivalent audit SVG is exported and the formal vector export is
   checked against it. Failed or unavailable equivalence limits the artifact to
   `DRAFT_ONLY`.
4. Run `figure_layout_audit.py`. Do not hand-write its result.
5. Resolve every soft finding in `SOFT_DISPOSITIONS.json`, then rerun the audit.
6. Bind the spec, dispositions and computed report into the figure manifest.

## Alignment classes

- `HARD`: geometry that communicates sameness or correspondence. Repeated
  cards, tag rows, matrix cells, parallel headers, shared baselines, equal-size
  modules, internal padding, centered labels and consistent strokes belong
  here. A mismatch blocks release.
- `SOFT`: a cross-region optical anchor that improves reading but is not a
  scientific equivalence. A mismatch is allowed only with an explicit
  `KEPT_WITH_REASON` disposition. If adjusted into tolerance, record
  `ADJUSTED`.
- `FREE`: deliberately unmatched content-driven geometry. It requires a
  scientific noncorrespondence reason written before drawing. A repeated
  family may not use `FREE`.

The second-column lower edge and the neighboring composition matrix in the
HART example are a `SOFT` anchor. Tag rows, repeated cells, internal label
centering, bottom padding, border weights and equal-size modules are `HARD`.

## Coverage and anti-bypass rules

- Register every visible text or painted primitive directly or through its
  nearest semantic component. Ownership is assigned to the nearest registered
  ancestor, so a root group cannot claim several independent cards. A normal
  component may own at most one visible rectangle. A `panel` may additionally
  own one shallow, same-width header rectangle aligned to its outer top edge.
  Backgrounds may use kind `background` but still require registration.
- Every registered component ID must exist in the SVG. Invisible or zero-area
  proxy geometry cannot satisfy a check.
- Every `card`, `chip`, and `panel` must either join a family containing at
  least two members or state a substantive `noncorrespondence_reason`. Merely
  omitting the family field is not evidence that no corresponding peer exists.
- A family used by at least two components requires at least one `HARD` check
  covering every family member. Repeated-family components cannot be `FREE`.
- `SOFT` and `FREE` components require a substantive noncorrespondence reason.
- All spec source anchors must occur verbatim in the approved story packet,
  figure contract, or facts packet. The audit does not infer scientific truth.
- Standalone symbols and automatically detected formula-like text need their
  own SVG ID, a `symbol` or `formula` component registration, and a symbol
  record with token, established meaning, source anchor, and caption label. An
  unexplained `#`, decorative operator, relation, or invented abbreviation
  fails even when a broad ancestor group is registered.
- A visible box around a symbol or formula requires a semantic `box_purpose`.
  A box containing only formula notation must itself be a `symbol` or
  `formula` component; relabeling it as a generic card or module does not pass.
- Changing the SVG, layout spec, dispositions, story, contract, facts, or
  caption invalidates the computed report and therefore the manifest.

## Supported geometric checks

- `align_left`, `align_right`, `align_top`, `align_bottom`
- `align_center_x`, `align_center_y`, `align_baseline`
- `equal_size`
- `containment` with `container`, `contents`, and `min_padding_em`
- `center_in` with `container`, `content`, and `axis`
- `stroke_family` with a final-size point range and maximum difference

Each check has an ID, a class, and a tolerance in `em` unless its own fields
specify point units. One `em` is the declared body font size at final placement.

## Visual acceptance

Numerical PASS is necessary but not sufficient. Inspect the rendered figure at
final placement and at 200 percent. Confirm hierarchy, scan order, whitespace,
connector salience, color meaning, line weight, formula legibility, and whether
any valid asymmetry looks accidental. Compactness must come from removing
redundant chrome, not from shrinking text or padding below the declared limits.

`DRAFT_ONLY` is a recovery receipt, not a quality verdict. It may bind a fresh
failed layout audit or a structurally valid export that is not yet equivalent
to the audit SVG. `PAPER_READY` and stronger verdicts still require a complete
PASS audit and visible-text plus render equivalence.
