# Composition-draft prompt template

Use this only when an image-generation draft would materially help explore the
composition. The result is a visual reference, not the editable master. Redraw
the selected topology as SVG, draw.io, PPTX, or another vector format.

```text
Create a publication-style composition draft for [METHOD NAME].

Scientific message:
[ONE SENTENCE THE READER SHOULD UNDERSTAND IN THREE SECONDS]

Approved story identity:
[STORY PACKET ID AND SHA-256]

Placement:
[VENUE, SINGLE OR DOUBLE COLUMN, EXACT PHYSICAL WIDTH]

Canonical stages or regions:
[REGION NAME, SCIENTIFIC ROLE, REQUIRED MODULES]

Canonical edge map:
[SOURCE -> DESTINATION; EDGE TYPE]

Training-only information:
[ITEMS]

Inference-time information:
[ITEMS]

Visible labels:
[EXACT AUTHORITATIVE TERMS]

Visual grammar:
- dense scientific UI with aligned cards and narrow intentional whitespace;
- one restrained hue family per stage and dark neutral text;
- short, thin, neutral arrows that remain weaker than module borders;
- ordinary connectors are straight or use at most one right-angle elbow;
- solid data flow and dashed update or control flow;
- standard sans-serif typography sized for the stated physical placement;
- no title banner, gradients, drop shadows, decorative icons, or colored prose.

Do not add:
[FORBIDDEN CLAIMS, MODULES, LOSSES, METRICS, DATASET ROLES, OR ARROWS]

The draft must preserve the canonical graph. Do not solve layout collisions by
shrinking text below the declared final-size minimum. Do not route a connector
around multiple modules or use color as the only semantic carrier.
```

After generation, compare the draft to the node and edge map before vector
redraw. Discard any attractive element that introduces unsupported science.

