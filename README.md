# Paper Main Figure

A reusable Codex skill for creating story-bound, scientifically faithful main
method figures as editable vectors.

The skill is intended for papers whose scientific story is already fixed. It
locks a figure contract and node/edge map before styling, distinguishes
training-only from inference-time information, designs at the venue's physical
placement width, and validates SVG/PDF exports at print size. Dense stage-board
layouts use aligned UI-like modules, narrow intentional whitespace, and short
subordinate connectors rather than decorative arrows.

## Install

Ask Codex to install the skill from:

<https://github.com/bystander563/paper-main-figure>

Or clone it into the Codex skills directory as `paper-main-figure`, then start
a new Codex task so skill discovery refreshes.

## Outputs

- `MAIN_FIGURE_CONTRACT.md`
- `FIGURE_FACTS.md`
- editable SVG, draw.io, or PPTX source
- vector PDF/SVG export
- placement-size PNG preview
- caption and alt text
- `MAIN_FIGURE_QA.md`

The skill reports `DRAFT_ONLY`, `PAPER_READY`, or `CAMERA_READY`. Generated
bitmap drafts are never treated as camera-ready masters.

## Integration

The skill is also bundled by
[`paper-submission-suite`](https://github.com/bystander563/paper-submission-suite).
There it runs immediately after explicit story approval when the approved
packet plans a central method figure.

## License

MIT.
