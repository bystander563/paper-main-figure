#!/usr/bin/env python3
"""Adversarial tests for schema-2 schematic visual carriers."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import content_retention_audit


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SchematicVisualGrammarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.story = self.base / "story.md"
        self.facts = self.base / "facts.md"
        self.caption = self.base / "caption.md"
        self.svg = self.base / "figure.svg"
        self.contract = self.base / "contract.md"
        self.spec = self.base / "layout.json"
        self.story.write_text(
            "Trajectory states provide privileged training evidence. "
            "Final text is the only inference input.\n",
            encoding="utf-8",
        )
        self.facts.write_text(
            "Trajectory states provide privileged training evidence.\n",
            encoding="utf-8",
        )
        self.caption.write_text(
            "Trajectory states are used only for training; final text is the only inference input.\n",
            encoding="utf-8",
        )
        self.svg.write_text(
            '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 220">
  <g id="trajectory-object">
    <line x1="40" y1="70" x2="130" y2="70" stroke="#334155"/>
    <line x1="40" y1="95" x2="155" y2="95" stroke="#334155"/>
    <circle cx="175" cy="82" r="15" fill="#dbeafe" stroke="#2563eb"/>
    <text x="40" y="45">Trajectory</text>
  </g>
  <g id="inference-label">
    <rect x="290" y="55" width="150" height="70" fill="#ffffff" stroke="#64748b"/>
    <text x="315" y="95">Final text</text>
  </g>
  <g id="flow"><line x1="192" y1="82" x2="282" y2="82" stroke="#64748b"/></g>
</svg>\n''',
            encoding="utf-8",
        )
        self.write_spec()
        self.write_contract()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_spec(self, *, formula: bool = False) -> None:
        components = [
            {
                "id": "trajectory-object", "kind": "icon",
                "semantic_role": "trajectory state schematic",
                "source_anchor": "Trajectory states", "alignment_class": "HARD",
                "box_purpose": "STATE",
            },
            {
                "id": "inference-label", "kind": "card",
                "semantic_role": "final text label", "source_anchor": "Final text",
                "alignment_class": "HARD", "noncorrespondence_reason": "Unique deployment input",
                "box_purpose": "INPUT",
            },
            {
                "id": "flow", "kind": "connector",
                "semantic_role": "state information flow", "source_anchor": "Trajectory states",
                "alignment_class": "HARD", "box_purpose": "NONE",
            },
        ]
        symbols = []
        if formula:
            components.append(
                {
                    "id": "formula", "kind": "formula", "semantic_role": "objective",
                    "source_anchor": "Trajectory states", "alignment_class": "HARD",
                    "box_purpose": "NONE",
                }
            )
            symbols.append(
                {
                    "element_id": "formula", "token": "L=x", "meaning": "training objective",
                    "source_anchor": "Trajectory states", "caption_label": "Trajectory states",
                }
            )
        payload = {
            "schema_version": 1,
            "protocol_version": "1.0.0",
            "story_packet_sha256": digest(self.story),
            "figure_contract_sha256": "0" * 64,
            "facts_sha256": digest(self.facts),
            "placement_width_mm": 160,
            "body_font_size_pt": 8,
            "components": components,
            "checks": [],
            "symbols": symbols,
        }
        self.spec.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "mode": "STORY_ONLY",
            "reference": None,
            "reference_omissions": [],
            "visual_grammar": {
                "route": "SCHEMATIC_OVERVIEW",
                "formula_budget": 0,
                "input_bindings": [
                    {
                        "id": "state-input",
                        "model_component": "inference-label",
                        "input_component": "trajectory-object",
                        "context_component": None,
                        "granularity": "state",
                        "source_anchor": "Trajectory states provide privileged training evidence.",
                        "connector_component": "flow",
                    }
                ],
                "macro_regions": [
                    {
                        "id": "method",
                        "role": "Show training evidence and deployment input",
                        "unit_ids": ["trajectory", "final-text"],
                        "skeleton_components": ["trajectory-object"],
                    }
                ],
            },
            "units": [
                {
                    "id": "trajectory", "region": "training", "disposition": "VISIBLE",
                    "visual_carrier": "VISUAL_OBJECT",
                    "source_anchor": "Trajectory states provide privileged training evidence.",
                    "required_tokens": ["Trajectory"], "svg_components": ["trajectory-object"],
                    "reference_present": False, "reference_tokens": [],
                    "reference_rewrites": [],
                    "rationale": "The sentence-state schematic carries the privileged evidence.",
                },
                {
                    "id": "final-text", "region": "inference", "disposition": "VISIBLE",
                    "visual_carrier": "SHORT_LABEL",
                    "source_anchor": "Final text is the only inference input.",
                    "required_tokens": ["Final text"], "svg_components": ["inference-label"],
                    "reference_present": False, "reference_tokens": [],
                    "reference_rewrites": [],
                    "rationale": "The label names the deployment input beside the trajectory object.",
                },
            ],
        }

    def write_contract(self, payload: dict[str, object] | None = None) -> None:
        value = payload or self.payload()
        self.contract.write_text(
            "# Contract\n\n<!-- FIGURE_CONTENT_CONTRACT_BEGIN -->\n```json\n"
            + json.dumps(value, indent=2)
            + "\n```\n<!-- FIGURE_CONTENT_CONTRACT_END -->\n",
            encoding="utf-8",
        )
        spec = json.loads(self.spec.read_text(encoding="utf-8"))
        spec["figure_contract_sha256"] = digest(self.contract)
        self.spec.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

    def audit(self) -> dict[str, object]:
        return content_retention_audit.audit_content_retention(
            self.contract, self.story, self.facts, self.caption, self.svg, self.spec
        )

    def test_valid_schematic_contract_passes(self) -> None:
        report = self.audit()
        self.assertEqual(report["contract_schema_version"], 2)
        self.assertEqual(report["visual_grammar"]["formula_component_count"], 0)

    def test_visual_object_cannot_be_a_single_text_card(self) -> None:
        payload = self.payload()
        payload["units"][0]["svg_components"] = ["inference-label"]
        self.write_contract(payload)
        with self.assertRaisesRegex(
            content_retention_audit.ContentRetentionError,
            "VISUAL_OBJECT but contains only a text-card shell",
        ):
            self.audit()

    def test_macro_region_cannot_be_all_short_labels(self) -> None:
        payload = self.payload()
        payload["units"][0]["visual_carrier"] = "SHORT_LABEL"
        self.write_contract(payload)
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError, "is text-only"):
            self.audit()

    def test_wordless_skeleton_cannot_be_a_single_text_card(self) -> None:
        payload = self.payload()
        payload["visual_grammar"]["macro_regions"][0]["skeleton_components"] = ["inference-label"]
        self.write_contract(payload)
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError, "wordless skeleton"):
            self.audit()

    def test_formula_budget_rejects_registered_formula(self) -> None:
        self.svg.write_text(
            self.svg.read_text(encoding="utf-8").replace(
                "</svg>", '<text id="formula" x="220" y="180">L=x</text>\n</svg>'
            ),
            encoding="utf-8",
        )
        self.write_spec(formula=True)
        self.write_contract()
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError, "exceed"):
            self.audit()

    def assert_unregistered_formula_rejected(self, token: str) -> None:
        self.svg.write_text(
            self.svg.read_text(encoding="utf-8").replace(
                "</svg>", f'<text x="220" y="180">{token}</text>\n</svg>'
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            content_retention_audit.ContentRetentionError,
            "formula-like text must be registered",
        ):
            self.audit()

    def test_unicode_subscript_formula_cannot_bypass_budget(self) -> None:
        self.assert_unregistered_formula_rejected("p₁")

    def test_fraction_formula_cannot_bypass_budget(self) -> None:
        self.assert_unregistered_formula_rejected("1/Kᵢ")

    def test_underscore_formula_cannot_bypass_budget(self) -> None:
        self.assert_unregistered_formula_rejected("R_TMR")

    def test_visible_unit_must_belong_to_one_macro_region(self) -> None:
        payload = self.payload()
        payload["visual_grammar"]["macro_regions"][0]["unit_ids"] = ["trajectory"]
        self.write_contract(payload)
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError, "absent from the macro-region map"):
            self.audit()

    def test_input_binding_rejects_changed_granularity(self) -> None:
        payload = self.payload()
        payload["visual_grammar"]["input_bindings"][0]["granularity"] = "sentence"
        self.write_contract(payload)
        with self.assertRaisesRegex(
            content_retention_audit.ContentRetentionError,
            "source_anchor does not name its sentence granularity",
        ):
            self.audit()


if __name__ == "__main__":
    unittest.main()
