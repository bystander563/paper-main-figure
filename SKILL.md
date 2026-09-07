---
name: paper-main-figure
description: Create story-bound, scientifically faithful, editable vector main-method figures for research papers. Use for a paper's main method overview, architecture, mechanism, or training/inference pipeline after the scientific story is fixed. Do not use for ordinary data plots or decorative illustrations.
metadata:
  version: "4.0.1"
---

# Paper Main Figure

Build a readable scientific schematic from an approved method. Deliver editable
vector source, a verified export and a caption. Geometry checks support visual
judgment; they do not certify scientific abstraction or aesthetics.

## 1. Fix the scientific message

Require an explicitly approved story packet. Bind its exact SHA-256 in
`MAIN_FIGURE_CONTRACT.md`. Read the mechanism, contribution hierarchy,
non-claims, terminology, raw method facts and intended physical placement.
Inspect the active code path when architecture depends on implementation.
Story changes require PI approval; ordinary layout changes that preserve it do not.
Historical figures are references, never authority to revive a superseded method.

Write `FIGURE_FACTS.md` and a canonical node/edge map. Separate facts from
graphical simplifications. Each object and relation must have a scientific
role. Distinguish data, supervision, parameter updates, inference and evaluation.
Preserve input granularity: a sentence classifier receives a sentence, even when
a document is drawn as context. Do not invent losses, layers, measurements,
dependencies or example results to fill space.

Read `references/content-retention-contract.md`. Embed its schema-2 ledger in
the contract. Use `REFERENCE_FLOOR` for a supplied or approved prior figure,
otherwise `STORY_ONLY`. Retain each scientific unit visually or explicitly
relocate explanatory detail to the caption. Record wording rewrites and justified
omissions. A reference is a visual baseline, not authority over approved facts.

## 2. Choose what the reader sees

Read `references/schematic-visual-grammar.md`. Identify the takeaway, principal
objects, indispensable relations and innovation-bearing region before choosing
panels. Stage panels, parallel lanes, a hierarchy or an inset may fit; no fixed
arrangement suits every method.

Preserve a user-approved macro composition when it works. Rebuild interiors
with actual objects and transformations: aligned sequences, states, features,
masks, codebooks, graph relationships, selections or outputs. Repeated marks
must show a supported relation, not decorative texture. Use short object labels;
a large family of prose cards cannot replace the mechanism.

For panels, read `references/composition-grid-and-whitespace.md`. Derive sizes
from readable content and spacing. Align comparable rows and edges; allow
different internal arrangements for different processes. Whitespace may separate
groups or carry a route. Do not fill it with invented objects, inflate shells,
or delete method content to obtain an occupancy score.

Ordinary flow arrows should be short, quiet and straight or single-elbow, with
explicit ports. Internal graph edges and necessary feedback paths have different
semantics; do not remove them to obey a blanket shape rule. Verify exceptions
against the source graph and inspect readability.

When stage panels fit, `references/stage-panel-style.md` supplies style guidance.
Use consistent semantic colors, neutral prose, redundant labels and line styles.
An attractive paper's palette is an example, not a venue mandate. Avoid
slash-separated prose unless the slash belongs to established notation.

## 3. Construct measured vectors

Read `references/figure-layout-protocol.md` for generic registration and
`references/measured-layout.md` for the main-figure implementation profile.
Freeze `FIGURE_LAYOUT_SPEC.json` before styling. Register real components and
their HARD, SOFT or FREE relationships; do not add invisible geometry or broaden
containers after seeing the audit.

Use `scripts/figure_components.py` or an equivalent implementation meeting the
same measurements. Row, column, header/body, text, tag, icon-label and port
helpers compute layout before emitting editable SVG. Declare independent fixed
owners, content regions and typography roles. Never derive a containing box by
unioning it with overflowing text. Bind a real header band with `header_card`;
center within its declared body region, not the entire header-plus-body card.
Center icon-label groups as a whole. Expand CSS into explicit effective
attributes; inline style overrides are not accepted by the measured profile.

Select actual font files and weights. Measure glyph bounds and advances; never
use character count to estimate width. Missing fonts or glyphs stop export for
correction. Multi-line labels have explicit baselines. Wrap, reflow, widen modules
or shorten sourced wording before reducing type size. Default essential labels
to at least 7 pt at the actual placement; the exact author kit overrides this
floor if it specifies otherwise. Keep repeated roles consistent. A suitable
mathematical font is allowed for real notation.

Keep equations subordinate. Standard identifiers and subscripts are sourced
symbol labels, not automatically full equations. Ordinary overview routes
default to no displayed equation; one may be justified by the approved message.
Long objectives belong in the caption or method. FORMULA_CORE is for a genuinely
mathematical visual argument, not a way to bypass readability.

Image generation may explore composition using `references/prompt-template.md`
and the imagegen Skill when useful. It cannot replace the editable vector master.
SVG is the default. Other editable masters need an audit SVG and equivalent
formal export; unavailable vector equivalence limits the artifact to DRAFT_ONLY.

## 4. Caption, audit and inspect

Write the caption with the figure: takeaway, objects, stages, notation and line
meanings, training/inference boundary and graphical simplifications. Illustrative
examples or probability bars must not masquerade as measured data.

Read `references/qa-checklist.md`. Run `scripts/figure_layout_audit.py` with the
SVG, spec, story, contract, facts, caption and `SOFT_DISPOSITIONS.json`.
Measured-v1 checks actual text containment, intended centering, same-role
typography and declared ports. General audits cover registration, source anchors,
repeated geometry and content retention. Declare applicable relations; stroke
consistency alone does not prove alignment.

Inspect thumbnail, wordless view, placement-size render, grayscale and local
200% crops. Check information, scan order, optical centering, padding, font weight,
arrows and intentional whitespace separately. Compare independent SVG and PDF
renders component by component; one engine can repeat the same outline defect.

For feedback revisions, record the relationship, fixed anchor and allowed
moving objects in the existing QA note. Verify its before/after gap or alignment
and inspect the crop. Moving both endpoints together does not change their
spacing. Preserve already-correct regions.

## 5. Deliver a bounded result

Return contract, facts, spec, dispositions, computed audit, editable master and
audit SVG, vector export, PNG preview, caption and `MAIN_FIGURE_QA.md`.
Use `scripts/main_figure_manifest.py create` for the hash-bound schema-2 handoff.
New ready receipts also require content-contract schema 2; reading an existing
legacy receipt is not permission to create or promote one under old rules.
CLI and manifest fields remain compatible with the orchestrator. Its validator
recomputes evidence; never hand-edit an audit PASS.

PAPER_READY requires measured-v1 evidence, scientific retention and clean
applicable visual/export checks. Legacy figures without micro-layout evidence
remain readable as DRAFT_ONLY evidence and need regeneration before a new
PAPER_READY handoff. CAMERA_READY additionally requires exact manuscript
placement, embedded valid fonts and final venue QA by paper-compile-layout-qa.
An unapproved test story or schematic fixture is never a submission-ready paper.

For redesigns, show old and new figures at the same physical width with relevant
local crops. Do not replace an approved manuscript figure before the user
confirms the new render. Report what was tested and what still needs judgment;
do not promise universal perfection or publish implicitly.
