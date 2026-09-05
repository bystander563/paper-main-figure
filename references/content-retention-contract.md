# Main-figure content-retention contract

This contract prevents a visually tidy redesign from deleting the scientific
argument. Embed exactly one JSON object between the following markers in
`MAIN_FIGURE_CONTRACT.md`:

````markdown
<!-- FIGURE_CONTENT_CONTRACT_BEGIN -->
```json
{
  "schema_version": 2,
  "mode": "STORY_ONLY",
  "reference": null,
  "reference_omissions": [],
  "visual_grammar": {
    "route": "SCHEMATIC_OVERVIEW",
    "formula_budget": 0,
    "input_bindings": [],
    "macro_regions": [
      {
        "id": "method",
        "role": "Show the input, core mechanism, and output",
        "unit_ids": ["core-method"],
        "skeleton_components": ["registered-method-component"]
      }
    ]
  },
  "units": [
    {
      "id": "core-method",
      "region": "method",
      "disposition": "VISIBLE",
      "visual_carrier": "VISUAL_OBJECT",
      "source_anchor": "Exact wording from the story or fact pack.",
      "required_tokens": ["Authoritative visible term"],
      "svg_components": ["registered-method-component"],
      "reference_present": false,
      "reference_tokens": [],
      "reference_rewrites": [],
      "rationale": "This unit carries the main scientific mechanism."
    }
  ]
}
```
<!-- FIGURE_CONTENT_CONTRACT_END -->
````

Use `STORY_ONLY` for a new composition with no supplied or previously approved
version. Use `REFERENCE_FLOOR` when redesigning an existing figure. In that
mode, `reference` contains `path` and lowercase SHA-256. `PAPER_READY` requires
an editable SVG reference: the audit extracts every unique visible text node
and rejects any text not dispositioned by a unit or `reference_omissions`.
A raster reference remains useful for side-by-side iteration, but its inventory
cannot be proved exhaustive and therefore remains `DRAFT_ONLY`.

Schema 2 is required for newly drawn figures. Schema 1 remains readable only so
previously frozen artifacts can still be revalidated; do not use it for a new
contract.

The `visual_grammar` block has exactly these fields:

- `route`: `SCHEMATIC_OVERVIEW`, `SYSTEM_PIPELINE`,
  `LAYERED_ARCHITECTURE`, or `FORMULA_CORE`;
- `formula_budget`: maximum number of displayed-equation components, registered
  as `formula`. Every route except `FORMULA_CORE` has a hard maximum of one.
  Use zero unless the approved message needs an equation. Automatically detected
  notation must still live inside a registered `formula` or `symbol`
  component. Ordinary identifiers such as indexed states may use `symbol`
  without spending an equation slot; an equation cannot evade the budget by
  being relabeled as a symbol. All notation must have an authoritative meaning;
- `input_bindings`: zero or more machine-checkable model-input records. Each
  record names a model component, the actual input component, an optional
  coarser context component, one of `document`, `sentence`, `token`, `span`,
  `batch`, or `state`, an authoritative source anchor that names that
  granularity, and the connector component. The input component semantic role
  must name the same granularity and must belong to a visible content unit;
- `macro_regions`: the small set of scientific regions that define the first
  scan. Each region declares an `id`, a substantive `role`, all visible
  `unit_ids` it owns, and one or more `skeleton_components` whose painted
  geometry remains meaningful when labels are ignored.

Every visible unit must belong to exactly one macro region. Each region must
contain at least one `VISUAL_OBJECT` or `RELATION`; a region made only of short
labels fails. A skeleton component made from one rectangle and text also
fails. This is the machine-checkable boundary between an information-rich
scientific schematic and a prose-card board.

Each schema-2 `units` item has exactly these fields:

- `id`: stable lowercase identifier;
- `region`: human-readable stage or region;
- `disposition`: `VISIBLE`, `CAPTION`, or `OPTIONAL_DROP`;
- `visual_carrier`: `VISUAL_OBJECT`, `RELATION`, or `SHORT_LABEL` for a
  `VISIBLE` unit; `CAPTION` for a caption unit; `OPTIONAL_DROP` for an omitted
  unit;
- `source_anchor`: exact paper or fact-pack wording that supports the unit;
- `required_tokens`: authoritative words or notation that must occur in the
  chosen destination;
- `svg_components`: registered layout-component IDs carrying a `VISIBLE` unit;
- `reference_present`: exactly whether `reference_tokens` is non-empty;
- `reference_tokens`: exact visible text nodes owned by this unit in the bound
  reference;
- `reference_rewrites`: explicit mappings from renamed reference text to one of
  this unit's `required_tokens`, each with a substantive rationale;
- `rationale`: concise explanation, mandatory and substantive for
  `OPTIONAL_DROP`.

`VISUAL_OBJECT` means that the registered component contains real painted
structure such as sentence strips, tokens, documents, users, codebooks,
networks, distributions, masks, state sequences, or output marks. One rounded
rectangle plus text is not a visual object. `RELATION` requires actual
connector geometry. `SHORT_LABEL` may name an adjacent object but cannot carry
an entire macro region by itself.

At the contract root, `reference_omissions` lists visible reference text that
is intentionally excluded because it is non-scientific chrome or redundant
wording. Each entry contains exactly `reference_text` and a substantive
`rationale`. Do not use this list to hide a mechanism, input, output,
comparison, training-deployment boundary, or inferential constraint.

Example unit:

```json
{
  "id": "matched-comparison-contract",
  "region": "training",
  "disposition": "VISIBLE",
  "visual_carrier": "RELATION",
  "source_anchor": "same source roster, backbone initialization, optimizer-update count, and parameter count",
  "required_tokens": ["Same updates", "Same parameters", "Same inference"],
  "svg_components": ["comparison-contract"],
  "reference_present": true,
  "reference_tokens": ["Matched comparison contract", "Same updates", "Same parameters", "Same inference"],
  "reference_rewrites": [],
  "rationale": "The matched-compute claim is part of the main scientific argument."
}
```

The manifest validator rejects missing source anchors, missing visible or
caption tokens, unregistered SVG components, stale reference hashes,
incomplete SVG-reference inventories, renamed items without a visible
destination, text-only macro regions, false visual-object declarations,
non-geometric relations, broken wordless skeletons, and formulas beyond the
frozen budget. A reference-present unit may be `OPTIONAL_DROP` only with a
substantive reason and rendered human review; the ledger is not permission to
relabel inconvenient science as decoration.

Do not use raw word count, object count, or occupancy as the retention target.
Those are diagnostic signals only. The release condition is preservation of
the story-bound scientific units and their readable relationships. High
information density is welcome when scientific objects and topology carry it;
adding prose cards merely to retain wording is not.
