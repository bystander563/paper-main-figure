#!/usr/bin/env python3
"""Create and validate a hash-bound, recomputed main-figure manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import figure_layout_audit
import content_retention_audit


VERDICT_RANK = {"DRAFT_ONLY": 0, "PAPER_READY": 1, "CAMERA_READY": 2}
SCHEMA_VERSION = 2
REQUIRED_ARTIFACTS = (
    "contract", "facts", "master", "audit_svg", "export", "preview",
    "caption", "qa", "layout_spec", "soft_dispositions", "layout_audit",
)
PAPER_READY_QA = (
    "Scientific topology", "Connector simplicity", "Final-size typography",
    "Rendered inspection", "Layout coverage", "Hard alignment",
    "Internal padding and centering", "Stroke consistency",
    "Symbol and box semantics", "Soft dispositions", "SVG export equivalence",
    "Information retention", "Composition grid", "Panel occupancy",
    "Unexplained whitespace", "Optical alignment",
)


class ManifestError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bound_file(path: Path, label: str) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ManifestError(f"{label} missing: {resolved}")
    return {"path": str(resolved), "sha256": sha256_file(resolved)}


def validate_entry(entry: Any, label: str) -> Path:
    if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
        raise ManifestError(f"{label} must contain exactly path and sha256")
    path = Path(entry["path"])
    if not path.is_file():
        raise ManifestError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != entry["sha256"]:
        raise ManifestError(f"{label} hash mismatch: recorded {entry['sha256']}, actual {actual}")
    return path.resolve()


def bullet_value(text: str, label: str) -> str:
    values = re.findall(rf"^-\s*{re.escape(label)}:\s*(.+?)\s*$", text, re.MULTILINE)
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
    layout_spec_sha256: str,
    layout_audit_sha256: str,
    content_mode: str,
) -> None:
    text = qa_path.read_text(encoding="utf-8")
    expected = {
        "Verdict": verdict,
        "Story packet SHA-256": story_sha256,
        "Placement width mm": f"{placement_width_mm:g}",
        "Editable master SHA-256": master_sha256,
        "Vector export SHA-256": export_sha256,
        "Layout spec SHA-256": layout_spec_sha256,
        "Layout audit SHA-256": layout_audit_sha256,
    }
    for label, value in expected.items():
        if bullet_value(text, label).casefold() != value.casefold():
            raise ManifestError(f"QA receipt {label} does not match the manifest input")
    if VERDICT_RANK[verdict] >= VERDICT_RANK["PAPER_READY"]:
        for label in PAPER_READY_QA:
            if bullet_value(text, label).upper() != "PASS":
                raise ManifestError(f"QA receipt requires {label}: PASS for {verdict}")
        expected_reference = "PASS" if content_mode == "REFERENCE_FLOOR" else "NOT_APPLICABLE"
        if bullet_value(text, "Reference comparison").upper() != expected_reference:
            raise ManifestError(
                f"QA receipt requires Reference comparison: {expected_reference} for {content_mode}"
            )
    if verdict == "CAMERA_READY":
        for label in ("Vector integrity", "Font integrity", "Color accessibility"):
            if bullet_value(text, label).upper() != "PASS":
                raise ManifestError(f"QA receipt requires {label}: PASS for CAMERA_READY")


def canonical_text(value: str) -> str:
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE).casefold()


def svg_metadata(path: Path, placement_width_mm: float) -> tuple[float, str]:
    if path.suffix.casefold() != ".svg":
        raise ManifestError("audit_svg must use the .svg extension")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ManifestError(f"audit_svg is invalid XML: {exc}") from exc
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ManifestError("audit_svg root must be svg")
    if any(element.tag.rsplit("}", 1)[-1] == "image" for element in root.iter()):
        raise ManifestError("SVG artifacts may not contain raster or externally linked images")
    try:
        view = [float(item) for item in root.attrib["viewBox"].replace(",", " ").split()]
        if len(view) != 4 or view[2] <= 0 or view[3] <= 0:
            raise ValueError
    except (KeyError, ValueError) as exc:
        raise ManifestError("audit_svg requires a positive four-number viewBox") from exc
    width = figure_layout_audit.base_audit.physical_mm(root.attrib.get("width"), "width")
    if not math.isclose(width, placement_width_mm, abs_tol=0.2):
        raise ManifestError("audit_svg width does not match placement width")
    visible_text = canonical_text(" ".join(
        "".join(element.itertext()) for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "text"
    ))
    if not visible_text:
        raise ManifestError("audit_svg contains no editable text")
    return view[2] / view[3], visible_text


def validate_editable_master(
    path: Path,
    placement_width_mm: float,
    audit_svg: Path,
    audit_aspect: float,
    audit_text: str,
    require_equivalence: bool,
) -> None:
    suffix = path.suffix.casefold()
    if suffix == ".svg":
        aspect, text = svg_metadata(path, placement_width_mm)
        if require_equivalence and not math.isclose(aspect, audit_aspect, rel_tol=0.005):
            raise ManifestError("editable SVG master and audit_svg aspect ratios differ")
        if require_equivalence and text != audit_text:
            raise ManifestError("editable SVG master and audit_svg expose different visible text")
        if require_equivalence and path.resolve() != audit_svg.resolve():
            distance = render_distance(render(path), render(audit_svg))
            if distance > 0.015:
                raise ManifestError(f"editable SVG master and audit_svg render distance {distance:.4f} exceeds 0.015")
        return

    if suffix == ".drawio":
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise ManifestError(f"editable drawio master is invalid XML: {exc}") from exc
        if root.tag.rsplit("}", 1)[-1] not in {"mxfile", "mxGraphModel"}:
            raise ManifestError("editable drawio master must contain mxfile or mxGraphModel XML")
        cells = [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "mxCell"]
        if any("image" in element.attrib.get("style", "").casefold() for element in cells):
            raise ManifestError("editable drawio master may not be an image-backed placeholder")
        raw_text = " ".join(re.sub(r"<[^>]+>", " ", element.attrib.get("value", "")) for element in cells)
        text = canonical_text(raw_text)
        if not text:
            raise ManifestError("editable drawio master contains no editable text")
    elif suffix == ".pptx":
        if not path.read_bytes().startswith(b"PK"):
            raise ManifestError("editable PPTX master is not a valid ZIP package")
        try:
            with zipfile.ZipFile(path) as package:
                names = package.namelist()
                slide_names = sorted(
                    name for name in names
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                )
                if not slide_names:
                    raise ManifestError("editable PPTX master contains no slide XML")
                if any(name.startswith("ppt/media/") for name in names):
                    raise ManifestError("editable PPTX master may not contain image-backed figure content")
                pieces: list[str] = []
                for name in slide_names:
                    slide = ET.fromstring(package.read(name))
                    pieces.extend(
                        "".join(element.itertext())
                        for element in slide.iter()
                        if element.tag.rsplit("}", 1)[-1] == "t"
                    )
        except zipfile.BadZipFile as exc:
            raise ManifestError(f"editable PPTX master is invalid: {exc}") from exc
        text = canonical_text(" ".join(pieces))
        if not text:
            raise ManifestError("editable PPTX master contains no editable text")
    else:
        raise ManifestError("editable master must be SVG, drawio, or PPTX")

    if require_equivalence and text != audit_text:
        raise ManifestError("editable master and audit_svg expose different visible text")


def render(path: Path) -> Any:
    try:
        from render_quality import render as independent_render
        return independent_render(path)
    except ManifestError:
        raise
    except Exception as exc:
        raise ManifestError(f"failed to render {path.name}: {exc}") from exc


def render_distance(first: Any, second: Any) -> float:
    from PIL import Image, ImageChops, ImageStat
    size = (720, max(1, round(720 * first.height / first.width)))
    first_scaled = first.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    second_scaled = second.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    values = ImageStat.Stat(ImageChops.difference(first_scaled, second_scaled)).rms
    return sum(values) / (3 * 255.0)


def validate_export(path: Path, placement_width_mm: float, svg_aspect: float, require_aspect: bool = True) -> str:
    if path.suffix.casefold() == ".svg":
        aspect, text = svg_metadata(path, placement_width_mm)
        if require_aspect and not math.isclose(aspect, svg_aspect, rel_tol=0.005):
            raise ManifestError("SVG export and audit_svg aspect ratios differ")
        return text
    if path.suffix.casefold() != ".pdf" or not path.read_bytes().startswith(b"%PDF-"):
        raise ManifestError("vector export must be SVG or a real PDF")
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
    except Exception as exc:
        raise ManifestError(f"vector export cannot be parsed: {exc}") from exc
    if len(reader.pages) != 1:
        raise ManifestError("PDF export must contain exactly one page")
    page = reader.pages[0]
    width_pt, height_pt = float(page.mediabox.width), float(page.mediabox.height)
    if not math.isclose(width_pt * 25.4 / 72.0, placement_width_mm, abs_tol=0.5):
        raise ManifestError("PDF export width does not match placement width")
    if require_aspect and not math.isclose(width_pt / height_pt, svg_aspect, rel_tol=0.01):
        raise ManifestError("PDF export and audit_svg aspect ratios differ")
    resources = page.get("/Resources", {}).get_object()
    xobjects = resources.get("/XObject", {}).get_object() if "/XObject" in resources else {}
    for name, reference in xobjects.items():
        if reference.get_object().get("/Subtype") == "/Image":
            raise ManifestError(f"PDF export contains raster image object {name}")
    text = canonical_text(page.extract_text() or "")
    if not text:
        raise ManifestError("PDF export contains no extractable text")
    return text


def validate_preview(path: Path) -> None:
    if path.suffix.casefold() != ".png" or not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ManifestError("preview must be a real PNG")
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if min(image.size) < 200:
                raise ManifestError("preview is too small for inspection")
            gray = image.convert("L")
            extrema = gray.getextrema()
            if extrema[1] - extrema[0] < 8:
                raise ManifestError("preview is visually degenerate")
    except ManifestError:
        raise
    except Exception as exc:
        raise ManifestError(f"preview cannot be decoded: {exc}") from exc


def recompute_layout_audit(paths: dict[str, Path], story: Path, placement_width_mm: float) -> dict[str, Any]:
    return figure_layout_audit.audit_layout(
        paths["audit_svg"], story, paths["contract"], paths["facts"],
        paths["caption"], paths["layout_spec"], paths["soft_dispositions"],
        placement_width_mm, 7.0,
    )


def validate_bundle(
    artifacts: dict[str, dict[str, str]],
    story: Path,
    story_sha256: str,
    placement_width_mm: float,
    verdict: str,
) -> None:
    if not isinstance(artifacts, dict) or set(artifacts) != set(REQUIRED_ARTIFACTS):
        raise ManifestError(f"artifacts must be exactly {list(REQUIRED_ARTIFACTS)}")
    paths = {name: validate_entry(artifacts[name], name) for name in REQUIRED_ARTIFACTS}
    try:
        content_report = content_retention_audit.audit_content_retention(
            paths["contract"], story, paths["facts"], paths["caption"],
            paths["audit_svg"], paths["layout_spec"],
        )
    except content_retention_audit.ContentRetentionError as exc:
        raise ManifestError(f"content retention audit failed: {exc}") from exc
    report = json.loads(paths["layout_audit"].read_text(encoding="utf-8"))
    fresh = recompute_layout_audit(paths, story, placement_width_mm)
    if report != fresh:
        raise ManifestError("layout audit does not match a fresh recomputation")
    if report.get("schema_version") != 2:
        raise ManifestError("layout audit must use schema 2")
    require_ready = VERDICT_RANK[verdict] >= VERDICT_RANK["PAPER_READY"]
    if require_ready and report.get("layout_spec_schema_version") != 2:
        raise ManifestError(
            "PAPER_READY requires main-figure layout-spec schema 2 with panel occupancy gates"
        )
    if (
        require_ready
        and content_report.get("mode") == "REFERENCE_FLOOR"
        and not content_report.get("reference_inventory", {}).get("verifiable")
    ):
        raise ManifestError(
            "PAPER_READY reference-floor figures require an SVG reference with "
            "a machine-verifiable exhaustive text inventory"
        )
    if require_ready and (report.get("status") != "PASS" or report.get("error_count") != 0):
        raise ManifestError("layout audit must PASS without errors for a paper-ready figure")
    if require_ready and report.get("coverage", {}).get("ratio") != 1:
        raise ManifestError("layout audit must establish complete visible-component coverage")
    if require_ready and report.get("micro_layout", {}).get("status") != "PASS":
        raise ManifestError("PAPER_READY requires measured-v1 font, padding and label alignment evidence; legacy artifacts need regeneration")
    aspect, audit_text = svg_metadata(paths["audit_svg"], placement_width_mm)
    validate_editable_master(
        paths["master"], placement_width_mm, paths["audit_svg"], aspect,
        audit_text, require_ready,
    )
    export_text = validate_export(paths["export"], placement_width_mm, aspect, require_ready)
    if require_ready:
        if audit_text != export_text:
            raise ManifestError("audit_svg and vector export expose different visible text")
        from render_quality import compare
        comparison = compare(paths["audit_svg"], paths["export"])
        if comparison["status"] != "PASS":
            raise ManifestError(f"Independent component-local render equivalence failed: {comparison}")
    validate_preview(paths["preview"])
    validate_qa_receipt(
        paths["qa"], verdict, story_sha256, placement_width_mm,
        artifacts["master"]["sha256"], artifacts["export"]["sha256"],
        artifacts["layout_spec"]["sha256"], artifacts["layout_audit"]["sha256"],
        content_report["mode"],
    )


def create_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if args.placement_width_mm <= 0:
        raise ManifestError("placement_width_mm must be positive")
    story = bound_file(args.story_packet, "story_packet")
    preliminary = {
        name: Path(getattr(args, name)).resolve()
        for name in REQUIRED_ARTIFACTS if name != "layout_audit"
    }
    report = recompute_layout_audit(preliminary, Path(story["path"]), args.placement_width_mm)
    args.layout_audit.parent.mkdir(parents=True, exist_ok=True)
    args.layout_audit.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts = {name: bound_file(Path(getattr(args, name)), name) for name in REQUIRED_ARTIFACTS}
    # Reading a frozen legacy receipt and creating a new delivery are different
    # operations. Keep validate_manifest backward-compatible, but never mint a
    # new ready receipt without the current content/visual-grammar contract.
    if VERDICT_RANK[args.verdict] >= VERDICT_RANK["PAPER_READY"]:
        contract = content_retention_audit.extract_contract(preliminary["contract"])
        if contract.get("schema_version") != 2:
            raise ManifestError("New PAPER_READY or CAMERA_READY creation requires content-contract schema 2; legacy content remains readable for revalidation or DRAFT_ONLY")
    validate_bundle(artifacts, Path(story["path"]), story["sha256"], args.placement_width_mm, args.verdict)
    if args.alt_text:
        accessibility: dict[str, Any] = {"alt_text": bound_file(args.alt_text, "alt_text")}
    elif args.alt_text_not_required:
        accessibility = {"alt_text_status": "VENUE_NOT_REQUIRED"}
    else:
        raise ManifestError("provide --alt-text or --alt-text-not-required")
    manifest = {
        "schema_version": SCHEMA_VERSION, "status": "PASS", "verdict": args.verdict,
        "story_packet": story, "placement_width_mm": args.placement_width_mm,
        "artifacts": artifacts, "accessibility": accessibility,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def validate_manifest(path: Path, story_packet: Path, require_verdict: str) -> dict[str, Any]:
    if not path.is_file():
        raise ManifestError(f"manifest missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required_top = {"schema_version", "status", "verdict", "story_packet", "placement_width_mm", "artifacts", "accessibility"}
    if set(manifest) != required_top:
        raise ManifestError(f"manifest fields must be exactly {sorted(required_top)}")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ManifestError("legacy main-figure manifest rejected; regenerate schema_version=2")
    if manifest["status"] != "PASS":
        raise ManifestError("manifest status must be PASS")
    verdict = manifest["verdict"]
    if verdict not in VERDICT_RANK or VERDICT_RANK[verdict] < VERDICT_RANK[require_verdict]:
        raise ManifestError(f"verdict {verdict} is below required {require_verdict}")
    story_path = validate_entry(manifest["story_packet"], "story_packet")
    if story_path != story_packet.resolve():
        raise ManifestError("manifest is bound to a different story packet path")
    if manifest["story_packet"]["sha256"] != sha256_file(story_packet.resolve()):
        raise ManifestError("manifest is stale for the approved story packet")
    width = manifest["placement_width_mm"]
    if not isinstance(width, (int, float)) or width <= 0:
        raise ManifestError("placement_width_mm must be positive")
    validate_bundle(manifest["artifacts"], story_path, manifest["story_packet"]["sha256"], float(width), verdict)
    accessibility = manifest["accessibility"]
    if isinstance(accessibility, dict) and set(accessibility) == {"alt_text"}:
        validate_entry(accessibility["alt_text"], "alt_text")
    elif accessibility != {"alt_text_status": "VENUE_NOT_REQUIRED"}:
        raise ManifestError("accessibility must bind alt_text or declare VENUE_NOT_REQUIRED")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--story-packet", type=Path, required=True)
    create.add_argument("--placement-width-mm", type=float, required=True)
    create.add_argument("--verdict", choices=VERDICT_RANK, required=True)
    for name in REQUIRED_ARTIFACTS:
        create.add_argument(f"--{name.replace('_', '-')}", dest=name, type=Path, required=True)
    alt = create.add_mutually_exclusive_group(required=True)
    alt.add_argument("--alt-text", type=Path)
    alt.add_argument("--alt-text-not-required", action="store_true")
    create.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--story-packet", type=Path, required=True)
    validate.add_argument("--require-verdict", choices=VERDICT_RANK, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = create_manifest(args) if args.command == "create" else validate_manifest(args.manifest, args.story_packet, args.require_verdict)
    except (ManifestError, figure_layout_audit.LayoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {manifest['verdict']} main figure bound to {manifest['story_packet']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
