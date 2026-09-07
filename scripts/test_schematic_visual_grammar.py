#!/usr/bin/env python3
"""Adversarial tests for schema-2 schematic visual carriers."""

from __future__ import annotations

import hashlib
import copy
import json
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

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
  <g id="classifier">
    <rect x="290" y="55" width="150" height="70" fill="#ffffff" stroke="#64748b"/>
    <text x="315" y="95">Classifier</text>
  </g>
  <g id="inference-label">
    <rect x="290" y="160" width="150" height="35" fill="#ffffff" stroke="#64748b"/>
    <text x="315" y="183">Final text</text>
  </g>
  <g id="flow"><line x1="192" y1="82" x2="282" y2="82" stroke="#64748b"/></g>
</svg>\n''',
            encoding="utf-8",
        )
        self.write_spec()
        self.write_contract()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_spec(self) -> None:
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
                "id": "classifier", "kind": "card", "semantic_role": "classifier model",
                "source_anchor": "Trajectory states", "alignment_class": "HARD",
                "noncorrespondence_reason": "Unique classifier trained on state examples", "box_purpose": "MODULE",
            },
            {
                "id": "flow", "kind": "connector",
                "semantic_role": "state information flow", "source_anchor": "Trajectory states",
                "alignment_class": "HARD", "box_purpose": "NONE",
            },
        ]
        symbols = []
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
                        "model_component": "classifier",
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
                    "required_tokens": ["Final text", "Classifier"], "svg_components": ["inference-label", "classifier"],
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

    def assert_audit_pass(self):
        try:
            return self.audit()
        except content_retention_audit.ContentRetentionError as exc:
            self.fail(f"Valid content was rejected: {exc}")

    def test_valid_schematic_contract_passes(self) -> None:
        report = self.assert_audit_pass()
        self.assertEqual(report["contract_schema_version"], 2)
        self.assertEqual(report["visual_grammar"]["formula_component_count"], 0)

    def test_visual_object_cannot_be_a_single_text_card(self) -> None:
        # Same scientific label, five equivalent encodings of an empty shell.
        original=self.svg.read_text(encoding="utf-8")
        for shape in self.shell_shapes():
            with self.subTest(shape=shape):
                self.replace_trajectory_geometry(original, shape)
                with self.assertRaisesRegex(content_retention_audit.ContentRetentionError,
                                            "VISUAL_OBJECT but contains only a text-card shell"):
                    self.audit()

    @staticmethod
    def shell_shapes():
        return ['<rect x="40" y="55" width="150" height="60"/>',
                '<polygon points="40,55 190,55 190,115 40,115"/>',
                '<path d="M40 55 H190 V115 H40 Z"/>',
                '<path d="m40 55 h150 v60 h-150 z"/>',
                '<path d="M40 55 L100 55 190 55 190 115 40 115 40 55"/>']

    def replace_trajectory_geometry(self, original, shape):
        root=ET.fromstring(original)
        group=next(e for e in root if e.get("id")=="trajectory-object")
        for child in list(group):
            if child.tag.rsplit("}",1)[-1]!="text": group.remove(child)
        el=ET.fromstring(shape);el.set("fill","#ffffff");el.set("stroke","#334155")
        group.append(el)
        ET.ElementTree(root).write(self.svg,encoding="utf-8")

    def test_macro_region_cannot_be_all_short_labels(self) -> None:
        payload = self.payload()
        payload["units"][0]["visual_carrier"] = "SHORT_LABEL"
        self.write_contract(payload)
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError, "is text-only"):
            self.audit()

    def test_wordless_skeleton_cannot_be_a_single_text_card(self) -> None:
        original=self.svg.read_text(encoding="utf-8")
        for shape in self.shell_shapes():
            with self.subTest(shape=shape):
                self.replace_trajectory_geometry(original,shape)
                payload=self.payload()
                payload["units"][0]["visual_carrier"]="SHORT_LABEL"
                payload["units"].append({**payload["units"][0],"id":"relation","visual_carrier":"RELATION",
                    "required_tokens":["Trajectory"],"svg_components":["flow","trajectory-object"]})
                payload["visual_grammar"]["macro_regions"][0]["unit_ids"].append("relation")
                self.write_contract(payload)
                with self.assertRaisesRegex(content_retention_audit.ContentRetentionError,"wordless skeleton"):
                    self.audit()

    def test_structured_single_path_is_not_rejected_as_a_plain_frame(self):
        original=self.svg.read_text(encoding="utf-8")
        # Document contour plus two internal sentence marks, encoded in one path.
        self.replace_trajectory_geometry(original,'<path d="M40 55 H170 L190 75 V115 H40 Z M60 80 H155 M60 100 H135"/>')
        self.assertEqual(self.assert_audit_pass()["visual_grammar"]["macro_regions"][0]["skeleton_components"][0]["rich_primitive"],True)

    def test_straight_and_single_elbow_relations_are_not_frames(self):
        original=self.svg.read_text(encoding="utf-8")
        for shape in ['<line x1="192" y1="82" x2="282" y2="82"/>',
                      '<path d="M192 82 H280 V110"/>',
                      '<polyline points="192,82 280,82 280,110"/>']:
            with self.subTest(shape=shape):
                root=ET.fromstring(original)
                flow=next(e for e in root if e.get("id")=="flow")
                flow.clear();flow.set("id","flow")
                line=ET.fromstring(shape);line.set("stroke","#64748b");line.set("fill","none")
                flow.append(line)
                ET.ElementTree(root).write(self.svg,encoding="utf-8")
                payload=self.payload()
                payload["units"][1]["visual_carrier"]="RELATION"
                payload["units"][1]["svg_components"].append("flow")
                self.write_contract(payload)
                self.assert_audit_pass()

    def add_notation(self, token, kind, budget, count=1):
        self.write_spec()
        root=ET.parse(self.svg).getroot()
        spec=json.loads(self.spec.read_text())
        for index in range(count):
            identifier=f"notation-{index}"
            ET.SubElement(root,"text",{"id":identifier,"x":"220","y":str(180+index*20)}).text=token
            if kind:
                spec["components"].append({"id":identifier,"kind":kind,"semantic_role":"source-defined notation",
                    "source_anchor":"Trajectory states","alignment_class":"HARD","box_purpose":"NONE"})
                spec["symbols"].append({"element_id":identifier,"token":token,"meaning":"test notation",
                    "source_anchor":"Trajectory states","caption_label":"Trajectory states"})
        ET.ElementTree(root).write(self.svg,encoding="utf-8")
        self.spec.write_text(json.dumps(spec),encoding="utf-8")
        payload=self.payload();payload["visual_grammar"]["formula_budget"]=budget
        self.write_contract(payload)

    def test_unregistered_notation_requires_typed_registration(self):
        original=self.svg.read_text(encoding="utf-8")
        for token in ("p₁","1/Kᵢ","R_TMR"):
            with self.subTest(token=token):
                self.svg.write_text(original,encoding="utf-8")
                self.add_notation(token,None,0)
                with self.assertRaisesRegex(content_retention_audit.ContentRetentionError,"formula-like text must be registered"):
                    self.audit()

    def test_registered_symbols_do_not_spend_equation_budget(self):
        original=self.svg.read_text(encoding="utf-8")
        for token in ("p₁","R_TMR"):
            with self.subTest(token=token):
                self.svg.write_text(original,encoding="utf-8")
                self.add_notation(token,"symbol",0)
                self.assertEqual(self.assert_audit_pass()["visual_grammar"]["formula_component_count"],0)

    def test_equation_budget_allows_within_budget_and_rejects_excess(self):
        original=self.svg.read_text(encoding="utf-8")
        for token,budget,count in [("L=x",0,1),("L=x",1,1),("L=x",1,2),("1/Kᵢ",1,1)]:
            with self.subTest(token=token,budget=budget,count=count):
                self.svg.write_text(original,encoding="utf-8")
                self.add_notation(token,"formula",budget,count)
                if count<=budget:
                    self.assertEqual(self.assert_audit_pass()["visual_grammar"]["formula_component_count"],count)
                else:
                    with self.assertRaisesRegex(content_retention_audit.ContentRetentionError,"exceed"):
                        self.audit()

    def test_displayed_equation_cannot_be_registered_as_symbol(self):
        self.add_notation("L=x","symbol",1)
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError,"must be registered as formula"):
            self.audit()

    def test_visible_unit_cannot_be_missing_from_macro_regions(self) -> None:
        payload = self.payload()
        payload["visual_grammar"]["macro_regions"][0]["unit_ids"] = ["trajectory"]
        self.write_contract(payload)
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError, "absent from the macro-region map"):
            self.audit()

    def test_visible_unit_cannot_belong_to_two_macro_regions(self):
        payload=self.payload()
        duplicate=copy.deepcopy(payload["visual_grammar"]["macro_regions"][0])
        duplicate["id"]="other"
        payload["visual_grammar"]["macro_regions"].append(duplicate)
        self.write_contract(payload)
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError,"appears in two macro regions"):
            self.audit()

    def test_input_binding_source_anchor_must_name_granularity(self) -> None:
        payload = self.payload()
        payload["visual_grammar"]["input_bindings"][0]["source_anchor"] = "Final text is the only inference input."
        self.write_contract(payload)
        with self.assertRaisesRegex(
            content_retention_audit.ContentRetentionError,
            "source_anchor does not name its state granularity",
        ):
            self.audit()

    def test_input_component_role_must_match_granularity(self):
        spec=json.loads(self.spec.read_text())
        spec["components"][0]["semantic_role"]="document context"
        self.spec.write_text(json.dumps(spec),encoding="utf-8")
        with self.assertRaisesRegex(content_retention_audit.ContentRetentionError,"input component does not preserve state granularity"):
            self.audit()


if __name__ == "__main__":
    unittest.main()
