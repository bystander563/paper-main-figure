#!/usr/bin/env python3
"""Create and validate a hash-bound main-figure manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


VERDICT_RANK = {"DRAFT_ONLY": 0, "PAPER_READY": 1, "CAMERA_READY": 2}
REQUIRED_ARTIFACTS = ("contract", "facts", "master", "export", "preview", "caption", "qa")


class ManifestError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bound_file(path: Path, label: str) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ManifestError(f"{label} missing: {resolved}")
    return {"path": str(resolved), "sha256": sha256_file(resolved)}


def _bullet_value(text: str, label: str) -> str:
    import re

    values = re.findall(
        rf"^-\s*{re.escape(label)}:\s*(.+?)\s*$", text, re.MULTILINE
    )
    if len(values) != 1:
        raise ManifestError(f"QA receipt must contain exactly one '- {label}:' line")
    return values[0].strip()


def validate_qa_receipt(
    qa_path: Path,
    verdict: str,
    story_sha256: str,
    placement_width_mm: float,
    master_sha256: str,
    export_sha256: str,
) -> None:
    text = qa_path.read_text(encoding="utf-8")
    expected = {
        "Verdict": verdict,
        "Story packet SHA-256": story_sha256,
        "Placement width mm": f"{placement_width_mm:g}",
        "Editable master SHA-256": master_sha256,
        "Vector export SHA-256": export_sha256,
    }
    for label, value in expected.items():
        if _bullet_value(text, label).casefold() != value.casefold():
            raise ManifestError(f"QA receipt {label} does not match the manifest input")
    if VERDICT_RANK[verdict] >= VERDICT_RANK["PAPER_READY"]:
        for label in (
            "Scientific topology",
            "Connector simplicity",
            "Final-size typography",
            "Rendered inspection",
        ):
            if _bullet_value(text, label).upper() != "PASS":
                raise ManifestError(f"QA receipt requires {label}: PASS for {verdict}")
    if verdict == "CAMERA_READY":
        for label in ("Vector integrity", "Font integrity", "Color accessibility"):
            if _bullet_value(text, label).upper() != "PASS":
                raise ManifestError(f"QA receipt requires {label}: PASS for CAMERA_READY")


def create_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if args.placement_width_mm <= 0:
        raise ManifestError("placement_width_mm must be positive")
    if args.verdict not in VERDICT_RANK:
        raise ManifestError(f"unknown verdict: {args.verdict}")
    artifacts = {
        name: _bound_file(getattr(args, name), name)
        for name in REQUIRED_ARTIFACTS
    }
    story = _bound_file(args.story_packet, "story_packet")
    validate_qa_receipt(
        Path(artifacts["qa"]["path"]),
        args.verdict,
        story["sha256"],
        args.placement_width_mm,
        artifacts["master"]["sha256"],
        artifacts["export"]["sha256"],
    )
    if args.alt_text:
        accessibility: dict[str, Any] = {"alt_text": _bound_file(args.alt_text, "alt_text")}
    elif args.alt_text_not_required:
        accessibility = {"alt_text_status": "VENUE_NOT_REQUIRED"}
    else:
        raise ManifestError("provide --alt-text or --alt-text-not-required")
    manifest = {
        "schema_version": 1,
        "status": "PASS",
        "verdict": args.verdict,
        "story_packet": story,
        "placement_width_mm": args.placement_width_mm,
        "artifacts": artifacts,
        "accessibility": accessibility,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def _validate_entry(entry: Any, label: str) -> None:
    if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
        raise ManifestError(f"{label} must contain exactly path and sha256")
    path = Path(entry["path"])
    if not path.is_file():
        raise ManifestError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != entry["sha256"]:
        raise ManifestError(f"{label} hash mismatch: recorded {entry['sha256']}, actual {actual}")


def validate_manifest(path: Path, story_packet: Path, require_verdict: str) -> dict[str, Any]:
    if require_verdict not in VERDICT_RANK:
        raise ManifestError(f"unknown required verdict: {require_verdict}")
    if not path.is_file():
        raise ManifestError(f"manifest missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required_top = {"schema_version", "status", "verdict", "story_packet", "placement_width_mm", "artifacts", "accessibility"}
    if set(manifest) != required_top:
        raise ManifestError(f"manifest fields must be exactly {sorted(required_top)}")
    if manifest["schema_version"] != 1 or manifest["status"] != "PASS":
        raise ManifestError("manifest must have schema_version=1 and status=PASS")
    verdict = manifest["verdict"]
    if verdict not in VERDICT_RANK:
        raise ManifestError(f"invalid manifest verdict: {verdict}")
    if VERDICT_RANK[verdict] < VERDICT_RANK[require_verdict]:
        raise ManifestError(f"verdict {verdict} is below required {require_verdict}")
    if not isinstance(manifest["placement_width_mm"], (int, float)) or manifest["placement_width_mm"] <= 0:
        raise ManifestError("placement_width_mm must be positive")

    _validate_entry(manifest["story_packet"], "story_packet")
    expected_story = story_packet.resolve()
    if Path(manifest["story_packet"]["path"]).resolve() != expected_story:
        raise ManifestError("manifest is bound to a different story packet path")
    actual_story_hash = sha256_file(expected_story)
    if manifest["story_packet"]["sha256"] != actual_story_hash:
        raise ManifestError("manifest is stale for the approved story packet")

    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != set(REQUIRED_ARTIFACTS):
        raise ManifestError(f"artifacts must be exactly {list(REQUIRED_ARTIFACTS)}")
    for name in REQUIRED_ARTIFACTS:
        _validate_entry(artifacts[name], name)
    validate_qa_receipt(
        Path(artifacts["qa"]["path"]),
        verdict,
        manifest["story_packet"]["sha256"],
        float(manifest["placement_width_mm"]),
        artifacts["master"]["sha256"],
        artifacts["export"]["sha256"],
    )

    accessibility = manifest["accessibility"]
    if not isinstance(accessibility, dict):
        raise ManifestError("accessibility must be an object")
    if "alt_text" in accessibility and len(accessibility) == 1:
        _validate_entry(accessibility["alt_text"], "alt_text")
    elif accessibility == {"alt_text_status": "VENUE_NOT_REQUIRED"}:
        pass
    else:
        raise ManifestError("accessibility must bind alt_text or declare VENUE_NOT_REQUIRED")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="write a manifest from verified artifacts")
    create.add_argument("--story-packet", type=Path, required=True)
    create.add_argument("--placement-width-mm", type=float, required=True)
    create.add_argument("--verdict", choices=VERDICT_RANK, required=True)
    for name in REQUIRED_ARTIFACTS:
        create.add_argument(f"--{name}", type=Path, required=True)
    alt = create.add_mutually_exclusive_group(required=True)
    alt.add_argument("--alt-text", type=Path)
    alt.add_argument("--alt-text-not-required", action="store_true")
    create.add_argument("--output", type=Path, required=True)

    validate = sub.add_parser("validate", help="verify all bound hashes and verdict")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--story-packet", type=Path, required=True)
    validate.add_argument("--require-verdict", choices=VERDICT_RANK, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "create":
            manifest = create_manifest(args)
        else:
            manifest = validate_manifest(args.manifest, args.story_packet, args.require_verdict)
    except (ManifestError, json.JSONDecodeError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {manifest['verdict']} main figure bound to {manifest['story_packet']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
