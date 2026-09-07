#!/usr/bin/env python3
"""Regression and bypass tests for main_figure_manifest.py schema 2."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from figure_components import Figure, Box
from content_retention_audit import extract_contract


SCRIPT = Path(__file__).with_name("main_figure_manifest.py")
LAYOUT = Path(__file__).with_name("figure_layout_audit.py")
ARTIFACTS = (
    "contract", "facts", "master", "audit_svg", "export", "preview",
    "caption", "qa", "layout_spec", "soft_dispositions", "layout_audit",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MainFigureManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.story = self.base / "story.md"
        self.contract = self.base / "contract.md"
        self.facts = self.base / "facts.md"
        self.caption = self.base / "caption.md"
        self.svg = self.base / "figure.svg"
        self.preview = self.base / "preview.png"
        self.spec = self.base / "layout_spec.json"
        self.dispositions = self.base / "soft_dispositions.json"
        self.audit = self.base / "layout_audit.json"
        self.qa = self.base / "qa.md"
        self.manifest = self.base / "MAIN_FIGURE_MANIFEST.json"
        self.story.write_text("Cards show the approved process.\n", encoding="utf-8")
        self.write_story_only_contract()
        self.facts.write_text("Final text is the only inference input. Training uses sentence examples; inference produces probability bars.\n", encoding="utf-8")
        self.caption.write_text("Two repeated cards summarize the process. Lines depict training sentence examples and inference probability bars, not measured results.\n", encoding="utf-8")
        self.svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="80mm" viewBox="0 0 800 400">
  <g id="background"><rect x="0" y="0" width="800" height="400" fill="#ffffff"/></g>
  <g id="card-a"><rect x="70" y="90" width="300" height="190" rx="12" fill="#f4f8f7" stroke="#087f5b" stroke-width="1.5"/><text x="220" y="180" text-anchor="middle" font-family="Arial" font-size="16" fill="#1f2937">Training</text></g>
  <g id="card-b"><rect x="430" y="90" width="300" height="190" rx="12" fill="#f4f8f7" stroke="#087f5b" stroke-width="1.5"/><text x="580" y="180" text-anchor="middle" font-family="Arial" font-size="16" fill="#1f2937">Inference</text></g>
</svg>\n''', encoding="utf-8")
        # Synthetic mechanism fixture, not an actual paper-ready manuscript.
        # Freeze label frames before measuring; never wrap metadata around ink.
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        tree=ET.parse(self.svg)
        root=tree.getroot()
        root.set("data-layout-profile", "measured-v1")
        figure = Figure(800, 400)
        for group in list(root)[1:]:
            owner = group.get("id")
            left = float(list(group)[0].get("x"))
            old_label = list(group)[1]
            figure.rect(owner, Box(left, 90, 300, 190))
            label = figure.text(owner+"-label", old_label.text,
                                Box(left+20, 110, 260, 40), owner, size=16)
            group.remove(old_label)
            group.append(label)
            for i, length in enumerate((130, 90)):
                ET.SubElement(group, "line", {"x1": str(left+60), "y1": str(205+i*30),
                    "x2": str(left+60+length), "y2": str(205+i*30),
                    "stroke": "#087f5b", "stroke-width": "1.5"})
        tree.write(self.svg,encoding="utf-8")
        spec = {
            "schema_version": 2,
            "protocol_version": "1.0.0",
            "story_packet_sha256": digest(self.story),
            "figure_contract_sha256": digest(self.contract),
            "facts_sha256": digest(self.facts),
            "placement_width_mm": 160,
            "body_font_size_pt": 8,
            "components": [
                {"id": "background", "kind": "background", "semantic_role": "canvas", "source_anchor": "Cards", "alignment_class": "HARD", "box_purpose": "NONE"},
                {"id": "card-a", "kind": "card", "semantic_role": "training", "source_anchor": "Repeated cards", "alignment_class": "HARD", "family": "cards", "box_purpose": "MODULE"},
                {"id": "card-b", "kind": "card", "semantic_role": "inference", "source_anchor": "Repeated cards", "alignment_class": "HARD", "family": "cards", "box_purpose": "MODULE"},
            ],
            "checks": [
                {"id": "equal-cards", "type": "equal_size", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "tolerance_em": 0.05},
                {"id": "top-cards", "type": "align_top", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "tolerance_em": 0.05},
                {"id": "stroke-cards", "type": "stroke_family", "alignment_class": "HARD", "elements": ["card-a", "card-b"], "min_pt": 0.25, "max_pt": 1.0, "max_delta_pt": 0.1},
            ],
            "symbols": [],
        }
        self.spec.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        self.write_dispositions()
        self.render_preview()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_story_only_contract(self) -> None:
        payload = {
            "schema_version": 2,
            "mode": "STORY_ONLY",
            "reference": None,
            "reference_omissions": [],
            "visual_grammar": {
                "route": "SCHEMATIC_OVERVIEW", "formula_budget": 0, "input_bindings": [],
                "macro_regions": [{"id": "method", "role": "Show training examples and predicted probabilities",
                    "unit_ids": ["training-card", "inference-card"],
                    "skeleton_components": ["card-a", "card-b"]}],
            },
            "units": [
                {
                    "id": "training-card",
                    "region": "training",
                    "disposition": "VISIBLE",
                    "visual_carrier": "VISUAL_OBJECT",
                    "source_anchor": "Cards show the approved process.",
                    "required_tokens": ["Training"],
                    "svg_components": ["card-a"],
                    "reference_present": False,
                    "reference_tokens": [],
                    "reference_rewrites": [],
                    "rationale": "Training is a required stage in the approved process.",
                },
                {
                    "id": "inference-card",
                    "region": "inference",
                    "disposition": "VISIBLE",
                    "visual_carrier": "VISUAL_OBJECT",
                    "source_anchor": "Cards show the approved process.",
                    "required_tokens": ["Inference"],
                    "svg_components": ["card-b"],
                    "reference_present": False,
                    "reference_tokens": [],
                    "reference_rewrites": [],
                    "rationale": "Inference is a required stage in the approved process.",
                },
            ],
        }
        self.contract.write_text(
            "Repeated cards share geometry.\n\n"
            "<!-- FIGURE_CONTENT_CONTRACT_BEGIN -->\n"
            "```json\n" + json.dumps(payload, indent=2) + "\n```\n"
            "<!-- FIGURE_CONTENT_CONTRACT_END -->\n",
            encoding="utf-8",
        )

    def refresh_spec_contract_binding(self) -> None:
        spec = json.loads(self.spec.read_text(encoding="utf-8"))
        spec["figure_contract_sha256"] = digest(self.contract)
        self.spec.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        self.write_dispositions()

    def replace_label(self, identifier, value):
        tree=ET.parse(self.svg)
        root=tree.getroot()
        group=next(e for e in root if e.get("id")==identifier)
        rect=group[0]
        left=float(rect.get("x"))
        figure=Figure(800,400)
        figure.rect(identifier,Box(left,90,300,190))
        label=figure.text(identifier+"-label",value,Box(left+20,110,260,40),identifier,size=16)
        old=next(e for e in group if e.get("id")==identifier+"-label")
        index=list(group).index(old)
        group.remove(old);group.insert(index,label)
        tree.write(self.svg,encoding="utf-8")

    def write_reference_floor_contract(self, reference: Path) -> None:
        payload = extract_contract(self.contract)
        payload.update(mode="REFERENCE_FLOOR", reference={"path": reference.name, "sha256": digest(reference)})
        for unit in payload["units"]:
            unit["reference_present"] = True
            unit["reference_tokens"] = list(unit["required_tokens"])
        self.write_contract_payload(payload)

    def write_contract_payload(self, payload):
        self.contract.write_text(
            "Repeated cards share geometry.\n\n"
            "<!-- FIGURE_CONTENT_CONTRACT_BEGIN -->\n```json\n"
            + json.dumps(payload, indent=2) +
            "\n```\n<!-- FIGURE_CONTENT_CONTRACT_END -->\n",
            encoding="utf-8",
        )
        self.refresh_spec_contract_binding()

    def write_dispositions(self) -> None:
        payload = {"schema_version": 1, "protocol_version": "1.0.0", "layout_spec_sha256": digest(self.spec), "dispositions": []}
        self.dispositions.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def render_preview(self) -> None:
        import pymupdf
        document = pymupdf.open(str(self.svg))
        pixmap = document[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        pixmap.save(str(self.preview))
        document.close()

    def run_layout(self, require_pass: bool = True) -> None:
        result = subprocess.run([
            sys.executable, str(LAYOUT), "--svg", str(self.svg),
            "--story-packet", str(self.story), "--figure-contract", str(self.contract),
            "--facts", str(self.facts), "--caption", str(self.caption),
            "--layout-spec", str(self.spec), "--soft-dispositions", str(self.dispositions),
            "--placement-width-mm", "160", "--output", str(self.audit),
        ], text=True, capture_output=True)
        if require_pass:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(self.audit.is_file(), result.stderr + result.stdout)

    def write_qa(self, verdict: str, require_layout_pass: bool = True) -> None:
        self.run_layout(require_layout_pass)
        lines = [
            "# Main Figure QA", "",
            f"- Verdict: {verdict}",
            f"- Story packet SHA-256: {digest(self.story)}",
            "- Placement width mm: 160",
            f"- Editable master SHA-256: {digest(self.svg)}",
            f"- Vector export SHA-256: {digest(self.svg)}",
            f"- Layout spec SHA-256: {digest(self.spec)}",
            f"- Layout audit SHA-256: {digest(self.audit)}",
        ]
        lines.extend(f"- {label}: PASS" for label in (
            "Scientific topology", "Connector simplicity", "Final-size typography",
            "Rendered inspection", "Layout coverage", "Hard alignment",
            "Internal padding and centering", "Stroke consistency",
            "Symbol and box semantics", "Soft dispositions", "SVG export equivalence",
            "Information retention", "Composition grid", "Panel occupancy",
            "Unexplained whitespace", "Optical alignment",
        ))
        reference_mode = '"mode": "REFERENCE_FLOOR"' in self.contract.read_text(encoding="utf-8")
        lines.append(f"- Reference comparison: {'PASS' if reference_mode else 'NOT_APPLICABLE'}")
        if verdict == "CAMERA_READY":
            lines.extend(f"- {label}: PASS" for label in ("Vector integrity", "Font integrity", "Color accessibility"))
        self.qa.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def create(
        self,
        verdict: str = "PAPER_READY",
        overrides: dict[str, Path] | None = None,
        require_layout_pass: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self.write_qa(verdict, require_layout_pass)
        mapping = {
            "contract": self.contract, "facts": self.facts, "master": self.svg,
            "audit_svg": self.svg, "export": self.svg, "preview": self.preview,
            "caption": self.caption, "qa": self.qa, "layout_spec": self.spec,
            "soft_dispositions": self.dispositions, "layout_audit": self.audit,
        }
        mapping.update(overrides or {})
        qa_text = self.qa.read_text(encoding="utf-8")
        qa_text = re.sub(
            r"(?m)^- Editable master SHA-256: .+$",
            f"- Editable master SHA-256: {digest(mapping['master'])}",
            qa_text,
        )
        qa_text = re.sub(
            r"(?m)^- Vector export SHA-256: .+$",
            f"- Vector export SHA-256: {digest(mapping['export'])}",
            qa_text,
        )
        self.qa.write_text(qa_text, encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "create", "--story-packet", str(self.story), "--placement-width-mm", "160", "--verdict", verdict]
        for name in ARTIFACTS:
            command.extend([f"--{name.replace('_', '-')}", str(mapping[name])])
        command.extend(["--alt-text-not-required", "--output", str(self.manifest)])
        return subprocess.run(command, text=True, capture_output=True)

    def validate(self, verdict: str = "PAPER_READY") -> subprocess.CompletedProcess[str]:
        return subprocess.run([
            sys.executable, str(SCRIPT), "validate", "--manifest", str(self.manifest),
            "--story-packet", str(self.story), "--require-verdict", verdict,
        ], text=True, capture_output=True)

    def test_valid_schema_two_manifest(self) -> None:
        self.assertEqual(extract_contract(self.contract)["schema_version"], 2)
        created = self.create()
        self.assertEqual(created.returncode, 0, created.stderr)
        validated = self.validate()
        self.assertEqual(validated.returncode, 0, validated.stderr)
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(set(payload["artifacts"]), set(ARTIFACTS))

    def test_stale_story_is_rejected(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        self.story.write_text("changed story\n", encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)

    def test_mutated_svg_is_rejected(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        self.svg.write_text(self.svg.read_text(encoding="utf-8").replace("Training", "Changed"), encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("master hash mismatch", result.stderr)

    def test_paper_ready_does_not_satisfy_camera_ready(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        result = self.validate("CAMERA_READY")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("below required CAMERA_READY", result.stderr)

    def test_camera_ready_receipt_roundtrip_not_manuscript_certification(self) -> None:
        self.assertEqual(self.create("CAMERA_READY").returncode, 0)
        self.assertEqual(self.validate("CAMERA_READY").returncode, 0)

    def test_paper_ready_receipt_requires_explicit_whitespace_gate(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        self.qa.write_text(
            self.qa.read_text(encoding="utf-8").replace(
                "- Unexplained whitespace: PASS\n", ""
            ),
            encoding="utf-8",
        )
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["artifacts"]["qa"]["sha256"] = digest(self.qa)
        self.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unexplained whitespace", result.stderr)

    def test_legacy_layout_spec_is_draft_only(self) -> None:
        spec = json.loads(self.spec.read_text(encoding="utf-8"))
        spec["schema_version"] = 1
        self.spec.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        self.write_dispositions()
        self.assertEqual(self.create("DRAFT_ONLY").returncode, 0)
        result = self.create("PAPER_READY")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("layout-spec schema 2", result.stderr)

    def test_required_visible_token_in_both_content_modes(self) -> None:
        original = self.svg.read_text(encoding="utf-8")
        reference = self.base / "reference.svg"
        reference.write_text(original, encoding="utf-8")
        for mode in ("STORY_ONLY", "REFERENCE_FLOOR"):
            with self.subTest(mode=mode):
                self.svg.write_text(original, encoding="utf-8")
                self.write_story_only_contract()
                self.refresh_spec_contract_binding()
                if mode == "REFERENCE_FLOOR":
                    self.write_reference_floor_contract(reference)
                positive = self.create()
                self.assertEqual(positive.returncode, 0, positive.stderr)
                # The shorter replacement still fits; only retention is wrong.
                self.replace_label("card-b", "Output")
                result = self.create()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("required visible token is missing", result.stderr)

    def test_reference_floor_rejects_silently_omitted_reference_unit(self) -> None:
        reference = self.base / "reference.svg"
        reference.write_text(self.svg.read_text(encoding="utf-8"), encoding="utf-8")
        self.replace_label("card-b", "Output")
        self.render_preview()
        self.write_reference_floor_contract(reference)
        payload = extract_contract(self.contract)
        payload["units"] = payload["units"][:1]
        payload["visual_grammar"]["macro_regions"][0]["unit_ids"] = ["training-card"]
        self.write_contract_payload(payload)
        result = self.create()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference inventory is incomplete", result.stderr)

    def test_reference_floor_rejects_stale_reference_hash(self) -> None:
        reference = self.base / "reference.svg"
        reference.write_text(self.svg.read_text(encoding="utf-8"), encoding="utf-8")
        self.write_reference_floor_contract(reference)
        self.assertEqual(self.create().returncode, 0)
        contract = extract_contract(self.contract)
        contract["reference"]["sha256"] = "0" * 64
        self.write_contract_payload(contract)
        result = self.create()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference baseline hash mismatch", result.stderr)

    def test_reference_inventory_preserves_symbols_and_duplicate_occurrences(self) -> None:
        reference = self.base / "reference.svg"
        for token in ("#", "Inference"):
            with self.subTest(token=token):
                reference.write_text(self.svg.read_text(encoding="utf-8").replace(
                    "</svg>", f'<text x="400" y="350">{token}</text></svg>'), encoding="utf-8")
                self.write_reference_floor_contract(reference)
                result = self.create()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("reference inventory is incomplete", result.stderr)
                self.assertIn(f"{token} x1", result.stderr)

    def test_forged_layout_audit_is_recomputed_and_rejected(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        audit = json.loads(self.audit.read_text(encoding="utf-8"))
        audit["coverage"]["ratio"] = 0.5
        audit["findings"] = []
        self.audit.write_text(json.dumps(audit), encoding="utf-8")
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["artifacts"]["layout_audit"]["sha256"] = digest(self.audit)
        self.qa.write_text(
            re.sub(
                r"(?m)^- Layout audit SHA-256: .+$",
                f"- Layout audit SHA-256: {digest(self.audit)}",
                self.qa.read_text(encoding="utf-8"),
            ),
            encoding="utf-8",
        )
        manifest["artifacts"]["qa"]["sha256"] = digest(self.qa)
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fresh recomputation", result.stderr)

    def test_legacy_schema_one_manifest_is_rejected(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        payload["schema_version"] = 1
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy main-figure manifest rejected", result.stderr)

    def test_unknown_editable_master_type_is_rejected(self) -> None:
        fake = self.base / "fake-master.txt"
        fake.write_text("Training Inference", encoding="utf-8")
        result = self.create(overrides={"master": fake})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("editable master must be SVG, drawio, or PPTX", result.stderr)

    def break_layout(self):
        self.svg.write_text(
            self.svg.read_text(encoding="utf-8").replace('id="card-b"><rect x="430" y="90" width="300"', 'id="card-b"><rect x="430" y="90" width="260"'),
            encoding="utf-8",
        )

    def test_draft_only_can_bind_a_failed_layout(self) -> None:
        self.break_layout()
        result = self.create("DRAFT_ONLY", require_layout_pass=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(self.audit.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(self.validate("DRAFT_ONLY").returncode, 0)

    def test_paper_ready_rejects_failed_layout_alone(self) -> None:
        self.break_layout()
        result = self.create("PAPER_READY", require_layout_pass=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("layout audit must PASS", result.stderr)

    def test_export_text_mismatch_draft_allowed_ready_rejected(self) -> None:
        different_export = self.base / "different-export.svg"
        different_export.write_text(
            self.svg.read_text(encoding="utf-8").replace("Training", "Draft export"),
            encoding="utf-8",
        )
        self.assertEqual(self.create("DRAFT_ONLY", overrides={"export": different_export}).returncode, 0)
        self.assertEqual(self.validate("DRAFT_ONLY").returncode, 0)
        result = self.create("PAPER_READY", overrides={"export": different_export})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different visible text", result.stderr)
        self.assertEqual(json.loads(self.audit.read_text())["status"], "PASS")

    def test_export_geometry_mismatch_with_identical_text_rejected(self) -> None:
        tree = ET.parse(self.svg)
        root = tree.getroot()
        group = next(e for e in root if e.get("id") == "card-a")
        group.remove(next(e for e in group if e.tag.rsplit("}", 1)[-1] == "line"))
        different_export = self.base / "different-geometry.svg"
        tree.write(different_export, encoding="utf-8")
        result = self.create(overrides={"export": different_export})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Independent component-local render equivalence failed", result.stderr)
        self.assertEqual(json.loads(self.audit.read_text())["status"], "PASS")

    def test_real_pdf_export_roundtrip(self) -> None:
        pdf = self.base / "figure.pdf"
        subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(pdf), str(self.svg)], check=True)
        result = self.create(overrides={"export": pdf})
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def downgrade_content_contract(self):
        payload = extract_contract(self.contract)
        payload["schema_version"] = 1
        payload.pop("visual_grammar")
        for unit in payload["units"]:
            unit.pop("visual_carrier")
        self.write_contract_payload(payload)

    def test_legacy_content_cannot_mint_new_ready_receipts(self) -> None:
        self.downgrade_content_contract()
        self.assertEqual(self.create("DRAFT_ONLY").returncode, 0)
        self.assertEqual(self.validate("DRAFT_ONLY").returncode, 0)
        for verdict in ("PAPER_READY", "CAMERA_READY"):
            with self.subTest(verdict=verdict):
                result = self.create(verdict)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("creation requires content-contract schema 2", result.stderr)

    def test_frozen_legacy_content_receipt_still_revalidates(self) -> None:
        self.downgrade_content_contract()
        self.assertEqual(self.create("DRAFT_ONLY").returncode, 0)
        # Emulate a receipt serialized by the old writer, not a new promotion.
        self.write_qa("PAPER_READY")
        payload = json.loads(self.manifest.read_text())
        payload["verdict"] = "PAPER_READY"
        payload["artifacts"]["qa"]["sha256"] = digest(self.qa)
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(self.validate("CAMERA_READY").returncode, 0)

    def test_new_content_grammar_rejects_text_only_shells(self) -> None:
        tree = ET.parse(self.svg)
        for group in tree.getroot():
            for child in list(group):
                if child.tag.rsplit("}", 1)[-1] == "line":
                    group.remove(child)
        tree.write(self.svg, encoding="utf-8")
        result = self.create()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only a text-card shell", result.stderr)


if __name__ == "__main__":
    unittest.main()
