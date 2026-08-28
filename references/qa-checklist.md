# Main-figure QA checklist

## Story and source fidelity

- [ ] Figure contract identifies the exact approved story packet.
- [ ] One-message takeaway matches the paper's thesis and contribution order.
- [ ] Every entity, label, symbol, and edge has a source.
- [ ] Visual simplifications are recorded and do not change topology.
- [ ] Forbidden claims and non-claims do not appear.

## Scientific topology

- [ ] Data, supervision, update, inference, and evaluation edges are distinct.
- [ ] Losses terminate at their actual consumers/update targets.
- [ ] Training-only information does not feed inference.
- [ ] Evaluation metrics are downstream measurements, not model inputs.
- [ ] The final prediction comes from the correct model and inputs.

## Alignment and connector simplicity

- [ ] Stage boundaries, module edges, centers, and repeated rows share a grid.
- [ ] Ports are aligned to module centerlines.
- [ ] Every ordinary arrow is straight or has at most one 90-degree elbow.
- [ ] Fan-out/fan-in uses a short shared trunk.
- [ ] No connector crosses or traverses an unrelated module.
- [ ] No diagonal, curved, serpentine, or canvas-wrapping arrow remains.
- [ ] Connectors and arrowheads are visually weaker than module borders.
- [ ] At thumbnail size, grouping comes from panels/cards rather than arrows.

## Density and component grammar

- [ ] Dense references are matched with nested UI components, not giant cards.
- [ ] Useful content occupies the panel without unexplained large blank zones.
- [ ] Repeated cards, header bands, tags, bars, and icons use a consistent grid.
- [ ] Every icon or micro-visual encodes a supported entity or state.
- [ ] No badge, chip, or label touches or crosses a header separator or border.
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
- [ ] Text uses an editable standard sans-serif font.
- [ ] Text does not overlap boxes, arrows, or other labels.
- [ ] Color is not the only carrier of meaning.
- [ ] Grayscale and color-vision-deficiency checks preserve distinctions.
- [ ] Every non-neutral hue has a stated role; stage hues are included in the
      total palette budget.
- [ ] Class and update semantics do not add redundant competing hues when
      labels, shapes, or dash patterns already suffice.
- [ ] No unsupported icon, gradient, shadow, or colored prose adds noise.

## Vector/export integrity

- [ ] Editable source is present.
- [ ] Text remains text rather than outlines or bitmap pixels.
- [ ] PDF/SVG export uses embedded/valid fonts and no external linked assets.
- [ ] Export is not clipped and matches the editable source.
- [ ] PNG is identified as a preview, not the master.

## Caption and manuscript fit

- [ ] Caption states the message, explains panels, and defines symbols/styles.
- [ ] Figure and caption can be understood without unsupported manuscript text.
- [ ] Figure is cited in the correct section and earns its space.
- [ ] LaTeX/Word uses the intended width without later downscaling.

Any failed scientific-topology, connector, final-size, or vector-integrity item
blocks `CAMERA_READY`.


