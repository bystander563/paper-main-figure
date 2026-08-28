#!/usr/bin/env python3
"""Regression and bypass tests for main_figure_manifest.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("main_figure_manifest.py")
ARTIFACTS = ("contract", "facts", "master", "export", "preview", "caption", "qa")


class MainFigureManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.story = self.base / "story.md"
        self.story.write_text("approved story\n", encoding="utf-8")
        for name in ARTIFACTS:
            (self.base / f"{name}.dat").write_text(f"{name}\n", encoding="utf-8")
        self.manifest = self.base / "MAIN_FIGURE_MANIFEST.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def create(self, verdict: str = "PAPER_READY") -> subprocess.CompletedProcess[str]:
        self.write_qa_receipt(verdict)
        command = [sys.executable, str(SCRIPT), "create", "--story-packet", str(self.story),
                   "--placement-width-mm", "160", "--verdict", verdict]
        for name in ARTIFACTS:
            command.extend([f"--{name}", str(self.base / f"{name}.dat")])
        command.extend(["--alt-text-not-required", "--output", str(self.manifest)])
        return subprocess.run(command, text=True, capture_output=True)

    def write_qa_receipt(self, verdict: str) -> None:
        story_hash = hashlib.sha256(self.story.read_bytes()).hexdigest()
        master_hash = hashlib.sha256((self.base / "master.dat").read_bytes()).hexdigest()
        export_hash = hashlib.sha256((self.base / "export.dat").read_bytes()).hexdigest()
        lines = [
            "# Main Figure QA",
            "",
            f"- Verdict: {verdict}",
            f"- Story packet SHA-256: {story_hash}",
            "- Placement width mm: 160",
            f"- Editable master SHA-256: {master_hash}",
            f"- Vector export SHA-256: {export_hash}",
            "- Scientific topology: PASS",
            "- Connector simplicity: PASS",
            "- Final-size typography: PASS",
            "- Rendered inspection: PASS",
        ]
        if verdict == "CAMERA_READY":
            lines.extend(
                (
                    "- Vector integrity: PASS",
                    "- Font integrity: PASS",
                    "- Color accessibility: PASS",
                )
            )
        (self.base / "qa.dat").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def validate(self, verdict: str = "PAPER_READY") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "validate", "--manifest", str(self.manifest),
             "--story-packet", str(self.story), "--require-verdict", verdict],
            text=True, capture_output=True,
        )

    def test_valid_paper_ready_manifest(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["artifacts"]), set(ARTIFACTS))

    def test_stale_story_is_rejected(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        self.story.write_text("changed story\n", encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)

    def test_mutated_vector_master_is_rejected(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        (self.base / "master.dat").write_text("mutated\n", encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("master hash mismatch", result.stderr)

    def test_paper_ready_does_not_satisfy_camera_ready(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        result = self.validate("CAMERA_READY")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("below required CAMERA_READY", result.stderr)

    def test_complete_camera_ready_receipt_passes(self) -> None:
        created = self.create("CAMERA_READY")
        self.assertEqual(created.returncode, 0, created.stderr)
        validated = self.validate("CAMERA_READY")
        self.assertEqual(validated.returncode, 0, validated.stderr)

    def test_forged_manifest_cannot_hide_failed_qa_receipt(self) -> None:
        self.assertEqual(self.create().returncode, 0)
        qa = self.base / "qa.dat"
        qa.write_text(
            qa.read_text(encoding="utf-8").replace(
                "- Connector simplicity: PASS", "- Connector simplicity: FAIL"
            ),
            encoding="utf-8",
        )
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["artifacts"]["qa"]["sha256"] = hashlib.sha256(qa.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Connector simplicity: PASS", result.stderr)


if __name__ == "__main__":
    unittest.main()
