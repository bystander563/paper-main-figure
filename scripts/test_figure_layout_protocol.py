#!/usr/bin/env python3
"""Adversarial regression tests for the shared figure layout protocol."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from figure_components import Figure, Box


SCRIPT = Path(__file__).with_name("figure_layout_audit.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FigureLayoutProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.story = self.base / "story.md"
        self.contract = self.base / "contract.md"
        self.facts = self.base / "facts.md"
        self.caption = self.base / "caption.md"
        self.svg = self.base / "figure.svg"
        self.spec = self.base / "layout.json"
        self.dispositions = self.base / "dispositions.json"
        self.report = self.base / "report.json"
        self.story.write_text("Cards show the approved process.\n", encoding="utf-8")
        self.contract.write_text("Repeated cards share geometry. label k is a state index.\n", encoding="utf-8")
        self.facts.write_text("Final text is used at inference.\n", encoding="utf-8")
        self.caption.write_text("Cards; k denotes the state index.\n", encoding="utf-8")
        self.write_svg()
        self.write_spec()
        self.write_dispositions([])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_svg(
        self,
        *,
        card_b_x: int = 410,
        card_b_width: int = 300,
        card_b_height: int = 190,
        label_b_y: int = 155,
        label_b_x: int = 560,
        stroke_b: float = 1.5,
        extra: str = "",
    ) -> None:
        self.svg.write_text(
            f'''<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="80mm" viewBox="0 0 800 400">
  <g id="background"><rect id="background-shape" x="0" y="0" width="800" height="400" fill="#ffffff"/></g>
  <g id="card-a"><rect x="70" y="90" width="300" height="190" rx="12" fill="#f4f8f7" stroke="#087f5b" stroke-width="1.5"/><text id="label-a" x="220" y="155" text-anchor="middle" font-family="Microsoft YaHei" font-size="16" fill="#1f2937">标签一</text></g>
  <g id="card-b"><rect x="{card_b_x}" y="90" width="{card_b_width}" height="{card_b_height}" rx="12" fill="#f4f8f7" stroke="#087f5b" stroke-width="{stroke_b}"/><text id="label-b" x="{label_b_x}" y="{label_b_y}" text-anchor="middle" font-family="Arial" font-size="16" fill="#1f2937">label two</text></g>
  {extra}
</svg>\n''',
            encoding="utf-8",
        )

    def base_spec(self) -> dict:
        return {
            "schema_version": 1,
            "protocol_version": "1.0.0",
            "story_packet_sha256": digest(self.story),
            "figure_contract_sha256": digest(self.contract),
            "facts_sha256": digest(self.facts),
            "placement_width_mm": 160,
            "body_font_size_pt": 8,
            "components": [
                {"id": "background", "kind": "background", "semantic_role": "canvas", "source_anchor": "Cards", "alignment_class": "HARD", "box_purpose": "NONE"},
                {"id": "card-a", "kind": "card", "semantic_role": "first card", "source_anchor": "Repeated cards", "alignment_class": "HARD", "family": "cards", "box_purpose": "MODULE"},
                {"id": "card-b", "kind": "card", "semantic_role": "second card", "source_anchor": "Repeated cards", "alignment_class": "HARD", "family": "cards", "box_purpose": "MODULE"},
            ],
            "checks": [
                {"id": "cards-equal", "type": "equal_size", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "tolerance_em": 0.05},
                {"id": "cards-top", "type": "align_top", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "tolerance_em": 0.05},
                {"id": "card-strokes", "type": "stroke_family", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "min_pt": 0.25, "max_pt": 1.0, "max_delta_pt": 0.1},
            ],
            "symbols": [],
        }

    def write_spec(self, spec: dict | None = None) -> None:
        self.spec.write_text(json.dumps(spec or self.base_spec(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def write_dispositions(self, items: list[dict]) -> None:
        payload = {
            "schema_version": 1,
            "protocol_version": "1.0.0",
            "layout_spec_sha256": digest(self.spec),
            "dispositions": items,
        }
        self.dispositions.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def run_audit(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable, str(SCRIPT), "--svg", str(self.svg),
                "--story-packet", str(self.story), "--figure-contract", str(self.contract),
                "--facts", str(self.facts), "--caption", str(self.caption),
                "--layout-spec", str(self.spec), "--soft-dispositions", str(self.dispositions),
                "--placement-width-mm", "160", "--minimum-text-pt", "7",
                "--output", str(self.report),
            ],
            text=True,
            capture_output=True,
        )

    def panel_spec(self, *, include_lower_card: bool = True) -> dict:
        lower = (
            '<g id="card-c"><rect x="70" y="220" width="660" height="100" '
            'rx="12" fill="#ffffff" stroke="#087f5b" stroke-width="1.5"/>'
            '<text x="400" y="275" text-anchor="middle" font-family="Arial" '
            'font-size="16">shared process</text></g>'
            if include_lower_card else ""
        )
        self.svg.write_text(
            f'''<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="80mm" viewBox="0 0 800 400">
  <g id="background"><rect x="0" y="0" width="800" height="400" fill="#ffffff"/></g>
  <g id="panel"><rect x="50" y="50" width="700" height="300" rx="14" fill="#f4f8f7" stroke="#087f5b" stroke-width="1.5"/><text x="70" y="82" font-family="Arial" font-size="16">process</text></g>
  <g id="card-a"><rect x="70" y="100" width="300" height="100" rx="12" fill="#ffffff" stroke="#087f5b" stroke-width="1.5"/><text x="220" y="155" text-anchor="middle" font-family="Arial" font-size="16">first</text></g>
  <g id="card-b"><rect x="430" y="100" width="300" height="100" rx="12" fill="#ffffff" stroke="#087f5b" stroke-width="1.5"/><text x="580" y="155" text-anchor="middle" font-family="Arial" font-size="16">second</text></g>
  {lower}
</svg>\n''',
            encoding="utf-8",
        )
        components = [
            {"id": "background", "kind": "background", "semantic_role": "canvas", "source_anchor": "Cards", "alignment_class": "HARD", "box_purpose": "NONE"},
            {"id": "panel", "kind": "panel", "semantic_role": "process panel", "source_anchor": "Cards", "alignment_class": "HARD", "noncorrespondence_reason": "Only macro process panel", "box_purpose": "GROUP"},
            {"id": "card-a", "kind": "card", "semantic_role": "first card", "source_anchor": "Repeated cards", "alignment_class": "HARD", "family": "cards", "box_purpose": "MODULE"},
            {"id": "card-b", "kind": "card", "semantic_role": "second card", "source_anchor": "Repeated cards", "alignment_class": "HARD", "family": "cards", "box_purpose": "MODULE"},
        ]
        contents = ["card-a", "card-b"]
        if include_lower_card:
            components.append({"id": "card-c", "kind": "card", "semantic_role": "shared process", "source_anchor": "Cards", "alignment_class": "HARD", "noncorrespondence_reason": "Full-width shared process row", "box_purpose": "MODULE"})
            contents.append("card-c")
        return {
            "schema_version": 2,
            "protocol_version": "1.0.0",
            "story_packet_sha256": digest(self.story),
            "figure_contract_sha256": digest(self.contract),
            "facts_sha256": digest(self.facts),
            "placement_width_mm": 160,
            "body_font_size_pt": 8,
            "components": components,
            "checks": [
                {"id": "cards-equal", "type": "equal_size", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "tolerance_em": 0.05},
                {"id": "cards-top", "type": "align_top", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "tolerance_em": 0.05},
                {
                    "id": "panel-space", "type": "panel_occupancy", "alignment_class": "HARD",
                    "container": "panel", "contents": contents,
                    "reference_components": ["card-a", "card-b"],
                    "usable_insets_em": {"top": 3.0, "right": 1.0, "bottom": 1.0, "left": 1.0},
                    "min_span_x_ratio": 0.75, "min_span_y_ratio": 0.75,
                    "max_blank_to_reference_area": 1.0, "grid_step_em": 0.25,
                },
            ],
            "symbols": [],
        }

    def codes(self) -> set[str]:
        payload = json.loads(self.report.read_text(encoding="utf-8"))
        return {item["code"] for item in payload["findings"]}

    def test_good_fixture_passes_with_chinese_text(self) -> None:
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(report["coverage"]["ratio"], 1)

    def test_dense_panel_occupancy_passes(self) -> None:
        self.write_spec(self.panel_spec())
        self.write_dispositions([])
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        metric = next(item["metrics"] for item in report["checks"] if item["type"] == "panel_occupancy")
        self.assertLessEqual(metric["blank_to_reference_area"], 1.0)

    def test_explicit_hard_occupancy_rejects_residual_void(self) -> None:
        self.write_spec(self.panel_spec(include_lower_card=False))
        self.write_dispositions([])
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HARD_LAYOUT_MISMATCH", self.codes())

    def test_schema_two_panel_cannot_omit_occupancy_gate(self) -> None:
        spec = self.panel_spec()
        spec["checks"] = [item for item in spec["checks"] if item["type"] != "panel_occupancy"]
        self.write_spec(spec)
        self.write_dispositions([])
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PANEL_OCCUPANCY_COVERAGE", self.codes())

    def test_label_cannot_count_as_panel_occupancy(self) -> None:
        spec = self.panel_spec()
        next(item for item in spec["components"] if item["id"] == "card-c")["kind"] = "label"
        self.write_spec(spec)
        self.write_dispositions([])
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CHECK_CONFIGURATION", self.codes())

    def test_historical_occupancy_diagnostic_scale_is_not_redefined(self) -> None:
        spec = self.panel_spec()
        next(item for item in spec["checks"] if item["type"] == "panel_occupancy")["max_blank_to_reference_area"] = 1.5
        self.write_spec(spec)
        self.write_dispositions([])
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CHECK_CONFIGURATION", self.codes())

    def test_invisible_card_cannot_count_as_panel_occupancy(self) -> None:
        spec = self.panel_spec(include_lower_card=False)
        raw = self.svg.read_text(encoding="utf-8")
        self.svg.write_text(
            raw.replace(
                "</svg>",
                '<g id="ghost-card"><rect x="70" y="210" width="660" height="110" '
                'fill="none" stroke="none"/></g>\n</svg>',
            ),
            encoding="utf-8",
        )
        spec["components"].append({
            "id": "ghost-card", "kind": "card", "semantic_role": "invisible proxy",
            "source_anchor": "Cards", "alignment_class": "HARD", "box_purpose": "MODULE",
            "noncorrespondence_reason": "Adversarial occupancy proxy",
        })
        occupancy = next(item for item in spec["checks"] if item["type"] == "panel_occupancy")
        occupancy["contents"].append("ghost-card")
        self.write_spec(spec)
        self.write_dispositions([])
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("INVISIBLE_COMPONENT", self.codes())
        self.assertIn("CHECK_CONFIGURATION", self.codes())

    def test_declared_label_baseline_misalignment_is_hard_failure(self) -> None:
        self.write_svg(label_b_y=172)
        spec = self.base_spec()
        spec["components"].extend([
            {"id": "label-a", "kind": "label", "semantic_role": "first tag", "source_anchor": "Cards", "alignment_class": "HARD", "family": "labels", "box_purpose": "NONE"},
            {"id": "label-b", "kind": "label", "semantic_role": "second tag", "source_anchor": "Cards", "alignment_class": "HARD", "family": "labels", "box_purpose": "NONE"},
        ])
        spec["checks"].append({"id": "label-baseline", "type": "align_baseline", "alignment_class": "HARD", "elements": ["label-a", "label-b"], "tolerance_em": 0.05})
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("HARD_LAYOUT_MISMATCH", self.codes())

    def test_right_edge_padding_violation_is_hard_failure(self) -> None:
        self.write_svg(label_b_x=696)
        spec = self.base_spec()
        spec["components"].append({"id": "label-b", "kind": "label", "semantic_role": "final text label", "source_anchor": "Final text", "alignment_class": "HARD", "box_purpose": "NONE"})
        spec["checks"].append({"id": "card-b-padding", "type": "containment", "alignment_class": "HARD", "container": "card-b", "contents": ["label-b"], "min_padding_em": 1.0})
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("HARD_LAYOUT_MISMATCH", self.codes())

    def test_unexplained_hash_symbol_is_rejected(self) -> None:
        self.write_svg(extra='<g id="hash"><rect x="370" y="300" width="60" height="60" fill="#ffffff" stroke="#087f5b" stroke-width="2"/><text x="400" y="340" text-anchor="middle" font-family="Arial" font-size="24" fill="#1f2937">#</text></g>')
        spec = self.base_spec()
        spec["components"].append({"id": "hash", "kind": "symbol", "semantic_role": "unexplained index", "source_anchor": "state index", "alignment_class": "HARD", "box_purpose": "STATE"})
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("UNEXPLAINED_SYMBOL", self.codes())

    def test_vertical_centering_violation_is_hard_failure(self) -> None:
        self.write_svg(label_b_y=120)
        spec = self.base_spec()
        spec["components"].append({"id": "label-b", "kind": "label", "semantic_role": "final text label", "source_anchor": "Final text", "alignment_class": "HARD", "box_purpose": "NONE"})
        spec["checks"].append({"id": "label-center", "type": "center_in", "alignment_class": "HARD", "container": "card-b", "content": "label-b", "axis": "y", "tolerance_em": 0.2})
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("HARD_LAYOUT_MISMATCH", self.codes())

    def test_inconsistent_border_weight_is_hard_failure(self) -> None:
        self.write_svg(stroke_b=6)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("HARD_LAYOUT_MISMATCH", self.codes())

    def test_ornamental_formula_box_is_rejected(self) -> None:
        self.write_svg(extra='<g id="formula"><rect x="330" y="310" width="140" height="50" fill="#ffffff" stroke="#087f5b" stroke-width="2"/><text x="400" y="344" text-anchor="middle" font-family="Arial" font-size="16" fill="#1f2937">k = h(e,i)</text></g>')
        spec = self.base_spec()
        spec["components"].append({"id": "formula", "kind": "formula", "semantic_role": "state sampling rule", "source_anchor": "state index", "alignment_class": "HARD", "box_purpose": "NONE"})
        spec["symbols"].append({"element_id": "formula", "token": "k", "meaning": "state index", "source_anchor": "state index", "caption_label": "k"})
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("ORNAMENTAL_SYMBOL_BOX", self.codes())

    def test_all_free_repeated_family_cannot_bypass_alignment(self) -> None:
        spec = self.base_spec()
        for component in spec["components"]:
            if component.get("family") == "cards":
                component["alignment_class"] = "FREE"
                component["noncorrespondence_reason"] = "The cards intentionally encode unrelated quantities."
        spec["checks"] = []
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("FREE_REPEATED_FAMILY", self.codes())

    def test_missing_component_registration_is_rejected(self) -> None:
        spec = self.base_spec()
        spec["components"] = [item for item in spec["components"] if item["id"] != "card-b"]
        spec["checks"] = []
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("UNCOVERED_VISIBLE_GEOMETRY", self.codes())

    def test_root_group_cannot_claim_independent_cards(self) -> None:
        raw = self.svg.read_text(encoding="utf-8")
        self.svg.write_text(raw.replace("<svg ", '<svg id="root" ', 1), encoding="utf-8")
        spec = self.base_spec()
        spec["components"] = [
            {
                "id": "root", "kind": "group", "semantic_role": "entire figure",
                "source_anchor": "Cards", "alignment_class": "HARD", "box_purpose": "GROUP",
            }
        ]
        spec["checks"] = []
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("SEMANTIC_BOX_OWNERSHIP", self.codes())

    def test_cards_must_declare_family_or_noncorrespondence(self) -> None:
        spec = self.base_spec()
        for component in spec["components"]:
            component.pop("family", None)
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("UNDECLARED_COMPONENT_CORRESPONDENCE", self.codes())

    def test_formula_box_cannot_be_disguised_as_generic_card(self) -> None:
        self.write_svg(extra='<g id="formula-box"><rect x="330" y="310" width="140" height="50" fill="#ffffff" stroke="#087f5b" stroke-width="2"/><text id="formula-text" x="400" y="344" text-anchor="middle" font-family="Arial" font-size="16" fill="#1f2937">k = h(e,i)</text></g>')
        spec = self.base_spec()
        spec["components"].extend([
            {
                "id": "formula-box", "kind": "card", "semantic_role": "state sampling rule",
                "source_anchor": "state index", "alignment_class": "HARD", "box_purpose": "MODULE",
                "noncorrespondence_reason": "This notation has no peer component in the diagram.",
            },
            {
                "id": "formula-text", "kind": "formula", "semantic_role": "state sampling equation",
                "source_anchor": "state index", "alignment_class": "HARD", "box_purpose": "NONE",
            },
        ])
        spec["symbols"].append({
            "element_id": "formula-text", "token": "k", "meaning": "state index",
            "source_anchor": "state index", "caption_label": "k",
        })
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("MISCLASSIFIED_FORMULA_BOX", self.codes())

    def test_unregistered_subscript_notation_is_not_a_generic_card(self) -> None:
        self.write_svg(extra='<g id="formula-box"><rect x="330" y="310" width="140" height="50" fill="#ffffff" stroke="#087f5b" stroke-width="2"/><text id="formula-text" x="400" y="344" text-anchor="middle" font-family="Times New Roman" font-size="16" fill="#1f2937">p₁</text></g>')
        spec = self.base_spec()
        spec["components"].append({
            "id": "formula-box", "kind": "card", "semantic_role": "generic card",
            "source_anchor": "Cards", "alignment_class": "HARD",
            "noncorrespondence_reason": "Unique claimed method object",
            "box_purpose": "MODULE",
        })
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("UNREGISTERED_FORMULA_TEXT", self.codes())

    def test_same_line_heading_collision_is_hard_failure(self) -> None:
        self.write_svg(extra='<g id="colliding-headings"><text x="320" y="340" font-family="Arial" font-size="24" font-weight="700">equal slot mass</text><text x="455" y="340" font-family="Arial" font-size="24" font-weight="700">equal state mass</text></g>')
        spec = self.base_spec()
        spec["components"].append({
            "id": "colliding-headings", "kind": "label",
            "semantic_role": "paired measure headings", "source_anchor": "Cards",
            "alignment_class": "HARD", "box_purpose": "NONE",
        })
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("TEXT_TEXT_COLLISION", self.codes())

    def test_text_crossing_thick_line_is_hard_failure(self) -> None:
        self.write_svg(extra='<g id="stroke-collision"><text x="300" y="340" font-family="Arial" font-size="24" fill="#1f2937">human</text><line id="loss-bar" x1="365" y1="333" x2="500" y2="333" stroke="#2563eb" stroke-width="12"/></g>')
        spec = self.base_spec()
        spec["components"].append({
            "id": "stroke-collision", "kind": "icon",
            "semantic_role": "labeled training bar", "source_anchor": "Cards",
            "alignment_class": "HARD", "box_purpose": "STATE",
            "noncorrespondence_reason": "Unique training indicator",
        })
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("TEXT_STROKE_COLLISION", self.codes())

    def test_nearby_thick_line_with_clear_gap_passes(self) -> None:
        self.write_svg(extra='<g id="clear-stroke"><text x="300" y="340" font-family="Arial" font-size="24" fill="#1f2937">human</text><line id="loss-bar" x1="395" y1="333" x2="500" y2="333" stroke="#2563eb" stroke-width="12"/></g>')
        spec = self.base_spec()
        spec["components"].append({
            "id": "clear-stroke", "kind": "icon",
            "semantic_role": "labeled training bar", "source_anchor": "Cards",
            "alignment_class": "HARD", "box_purpose": "STATE",
            "noncorrespondence_reason": "Unique training indicator",
        })
        self.write_spec(spec)
        self.write_dispositions([])
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertNotIn("TEXT_STROKE_COLLISION", self.codes())

    def test_changed_spec_invalidates_dispositions(self) -> None:
        spec = self.base_spec()
        spec["checks"].append({"id": "soft-bottom", "type": "align_bottom", "alignment_class": "SOFT", "elements": ["card-a", "card-b"], "tolerance_em": 0.05})
        self.write_spec(spec)
        self.write_dispositions([{"check_id": "soft-bottom", "status": "ADJUSTED", "reason": "The two outer bottoms were aligned."}])
        spec["body_font_size_pt"] = 8.5
        self.write_spec(spec)
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("STALE_DISPOSITIONS", self.codes())

    def test_unresolved_soft_warning_is_rejected(self) -> None:
        self.write_svg(card_b_height=170)
        spec = self.base_spec()
        spec["checks"][0]["tolerance_em"] = 3.0
        spec["checks"].append({"id": "soft-bottom", "type": "align_bottom", "alignment_class": "SOFT", "elements": ["card-a", "card-b"], "tolerance_em": 0.05})
        self.write_spec(spec)
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode, 0)
        self.assertIn("DISPOSITION_COVERAGE", self.codes())

    def test_legitimate_soft_asymmetry_with_reason_passes(self) -> None:
        self.write_svg(card_b_height=170)
        spec = self.base_spec()
        spec["checks"][0]["tolerance_em"] = 3.0
        spec["checks"].append({"id": "soft-bottom", "type": "align_bottom", "alignment_class": "SOFT", "elements": ["card-a", "card-b"], "tolerance_em": 0.05})
        self.write_spec(spec)
        self.write_dispositions([{"check_id": "soft-bottom", "status": "KEPT_WITH_REASON", "reason": "The right card is shorter because it contains one fewer scientific stage."}])
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("RESOLVED_SOFT_MISMATCH", self.codes())

    def prepare_measured_panel(self, include_lower_card=False):
        spec=self.panel_spec(include_lower_card=include_lower_card)
        tree=ET.parse(self.svg);root=tree.getroot()
        root.set("data-layout-profile","measured-v1")
        figure=Figure(800,400)
        for group in root:
            if group.get("id")=="background": continue
            rect=group[0];owner=group.get("id")
            b=Box(*(float(rect.get(k)) for k in ("x","y","width","height")))
            figure.rect(owner,b)
            frame=Box(70,60,200,30) if owner=="panel" else b.inset(10)
            original=group[1]
            label=figure.text(owner+"-label",original.text,frame,owner,size=16)
            group.remove(original);group.append(label)
        tree.write(self.svg,encoding="utf-8")
        next(c for c in spec["checks"] if c["id"]=="panel-space")["alignment_class"]="SOFT"
        self.write_spec(spec)
        return spec

    def test_measured_occupancy_allows_resolved_space_without_filler(self):
        for dense in (False,True):
            with self.subTest(dense=dense):
                self.prepare_measured_panel(dense)
                self.write_dispositions([{"check_id":"panel-space",
                    "status":"ADJUSTED" if dense else "KEPT_WITH_REASON",
                    "reason":"The open lower region separates the parallel upper objects from downstream routing."}])
                result=self.run_audit()
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                report=json.loads(self.report.read_text(encoding="utf-8"))
                self.assertEqual(report["micro_layout"]["status"],"PASS")
                check=next(c for c in report["checks"] if c["id"]=="panel-space")
                self.assertEqual(check["passed"],dense)
                self.assertEqual(check["alignment_class"],"SOFT")

    def test_soft_occupancy_does_not_waive_missing_disposition(self):
        self.prepare_measured_panel()
        self.write_dispositions([])
        self.assertNotEqual(self.run_audit().returncode,0)
        self.assertIn("DISPOSITION_COVERAGE",self.codes())

    def test_resolved_soft_occupancy_does_not_waive_text_alignment(self):
        self.prepare_measured_panel()
        self.write_dispositions([{"check_id":"panel-space","status":"KEPT_WITH_REASON",
            "reason":"Lower whitespace preserves separation for downstream routing."}])
        tree=ET.parse(self.svg)
        label=next(e for e in tree.getroot().iter() if e.get("id")=="card-a-label")
        label.set("x",str(float(label.get("x"))+20))
        tree.write(self.svg,encoding="utf-8")
        self.assertNotEqual(self.run_audit().returncode,0)
        self.assertIn("TEXT_HORIZONTAL_ALIGNMENT",self.codes())


if __name__ == "__main__":
    unittest.main()
