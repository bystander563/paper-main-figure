# Paper Main Figure

A reusable Codex skill for creating story-bound, scientifically faithful main
method figures as editable vectors. Current Skill version: **4.0.1**.

The skill is intended for papers whose scientific story is already fixed. It
locks a figure contract and node/edge map before styling, distinguishes
training-only from inference-time information, designs at the venue's physical
placement width, and validates SVG/PDF exports at print size. Dense stage-board
layouts use scientific objects, measured alignment, intentional whitespace, and
short subordinate connectors. V4 adds real-font text measurement, fixed
header/body regions, shared baselines, port checks and independent local
SVG/PDF rendering checks. Geometry passes do not replace visual approval.

## Runtime requirements

The vector helpers require Python with Pillow, fontTools, PyMuPDF and pypdf,
plus the `rsvg-convert` executable from librsvg. Install the exact fonts used
by the figure: missing fonts and missing glyphs fail explicitly instead of
silently falling back. Standard Windows fonts and exact fontconfig matches
are supported; proprietary fonts are not bundled.

See [the measured-layout profile](references/measured-layout.md) for supported
SVG geometry and the header/body component API. Inline CSS and unsupported
transforms must be expanded before auditing.

Run the scoped regression suite after satisfying those requirements:

```shell
python -B -m unittest discover -s scripts -p "test_*.py"
```

## Install

Ask Codex to install the skill from:

<https://github.com/bystander563/paper-main-figure>

Or clone it into the Codex skills directory as `paper-main-figure`, then start
a new Codex task so skill discovery refreshes.

## Outputs

- `MAIN_FIGURE_CONTRACT.md`
- `FIGURE_FACTS.md`
- `FIGURE_LAYOUT_SPEC.json`, soft dispositions and recomputed layout audit
- editable SVG, draw.io, or PPTX source
- vector PDF/SVG export
- placement-size PNG preview
- caption and alt text
- `MAIN_FIGURE_QA.md`
- hash-bound `MAIN_FIGURE_MANIFEST.json`

The skill reports `DRAFT_ONLY`, `PAPER_READY`, or `CAMERA_READY`. Generated
bitmap drafts are never treated as camera-ready masters.
New `PAPER_READY` handoffs require the measured-v1 profile; legacy figures
without that evidence need regeneration. Historical or synthetic test stories
remain `DRAFT_ONLY`, even when their layout tests pass.

## Integration

The skill is also bundled by
[`paper-submission-suite`](https://github.com/bystander563/paper-submission-suite).
There it runs immediately after explicit story approval when the approved
packet plans a central method figure.

## License

MIT.
