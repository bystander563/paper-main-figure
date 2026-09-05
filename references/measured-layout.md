# Measured main-figure layout profile

This main-figure extension leaves the shared protocol 1.0 file and handoff
schema unchanged. New main figures declare `data-layout-profile="measured-v1"`
on their SVG. Old unmeasured geometry can be inspected, but cannot newly pass
PAPER_READY. Do not copy this profile into another Skill without its approved
compatibility review.

## Dependencies and scope

Python needs Pillow and fontTools for actual glyph metrics. Rendering needs
`rsvg-convert` (librsvg) for SVG, PyMuPDF for PDF, and pypdf for vector/font
inspection. Fonts must be installed explicitly; the helper does not silently
substitute a missing face. Standard Windows font files and exact fontconfig
matches are supported. For another environment add a tested exact font mapping.
Never ship proprietary font files without permission.

The metrics support explicit alphabetic text baselines and flat multi-line
tspans. Inline CSS is rejected: expand it to effective presentation attributes,
because CSS overrides those attributes in a renderer. Expand mixed font runs,
SVG transforms and unsupported spacing into explicit audited geometry.
Missing glyphs, missing fonts and fingerprint drift
are failures. Glyph bounds and text advance are different measurements; neither
alone proves optical balance. Inspect the final export.

## Generator

`figure_components.py` provides `Box`, `row`, `column`, `header_body` and `Figure`.
Figure supports measured `text`, shared-baseline `tags`, combined `icon_label`,
closed `document` icons, shapes and `connect` ports. It raises on overlong text
instead of shrinking it. Example:

```python
from figure_components import Figure, Box
f = Figure(800, 400, placement_mm=160)
outer = Box(50, 50, 300, 180)
header, body = f.header_card("module", outer, 50)
f.text("title", "Input", header.inset(12), "module", size=22, zone="header")
f.text("final", "Final text", body.inset(12), "module", size=22, zone="body")
f.save("figure.svg")
```

Owners are real fixed painted shapes. Text metadata names the owner, the
preplanned x/y/width/height content region, padding, horizontal and vertical
intent, typography role and exact font hash. These are constraints, not invisible
rectangles. Fix them before adjusting text. Do not regenerate them around a
badly placed label to make a test pass.

Same-row labels use a common baseline. Centering is relative to the white body
when a header exists. Use `header_card` to bind its real painted band to the
body; card text requires `zone="header"` or `zone="body"`. The standalone
`header_body` geometry helper alone is not QA evidence.
Icon-label centering measures the entire visible group.
Connector ports derive from module frames and are checked again after moves.
Optical adjustments require a recorded reason and before/after local inspection;
they must not conceal a geometric error.

## Audit and revision

`micro_layout_audit.py --svg figure.svg` recomputes frame containment, centering,
font-role consistency, text collisions and declared connector ports. The full
`figure_layout_audit.py` includes this report and also runs SVG collision,
component-coverage, source and relation checks. Separate repeated geometry still
belongs in the frozen layout spec; text metadata is not a replacement for it.

Containing frames are independent shapes, not unions with descendants.
Unsupported geometry must fail explicitly rather than disappearing from the
check. An occupancy PASS is a heuristic: use a resolved SOFT diagnostic for an
intentional routing/grouping space, never to excuse clipping or lost content.

For feedback, record the two relation endpoints, the fixed anchor, allowed
movable objects, direction and allowed follower connectors in the existing QA
note. `revision_gap` checks measured before/after bounds and rejects unchanged
gaps, moved anchors, wrong direction and unrelated movement. Preserve crop
evidence alongside the note. Pixel difference alone does not prove intent.

## Export

`render_quality.py` renders SVG through librsvg and PDF through the PDF
interpreter, compares whole figures and local components/outline strips. The
manifest uses it from PAPER_READY onward. Lack of the independent renderer
does not authorize fallback to a single-engine comparison.

The tolerance handles small antialiasing differences, not arbitrary font
substitution. Inspect the exact PDF with a second PDF renderer when available,
especially on new environments. Outline, clipping, glyph and arrow defects
remain failures even if the aggregate comparison happens to pass.

References: [SVG text alignment](https://www.w3.org/TR/SVG2/text.html),
[Pillow metrics](https://pillow.readthedocs.io/en/stable/reference/ImageText.html),
[SVG polygon closure](https://www.w3.org/TR/SVG2/shapes.html).
