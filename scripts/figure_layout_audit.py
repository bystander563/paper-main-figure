#!/usr/bin/env python3
"""Recompute a story-bound layout audit for an editable paper-figure SVG."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import svg_layout_audit as base_audit
import micro_layout_audit


PROTOCOL_VERSION = "1.0.0"
POINT_MM = 25.4 / 72.0
VISIBLE_TAGS = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text"}
ALIGN_TYPES = {
    "align_left": 0,
    "align_top": 1,
    "align_right": 2,
    "align_bottom": 3,
    "align_center_x": "center_x",
    "align_center_y": "center_y",
    "align_baseline": "baseline",
}
BOX_PURPOSES = {"MODULE", "STATE", "GROUP", "CHOICE", "INTERACTION", "LEGEND", "INPUT", "OUTPUT"}
STANDALONE_SYMBOL = re.compile(r"^\s*[#?+×÷=↔→←]\s*$")
FORMULA_TEXT = re.compile(
    r"(?:"
    r"[=≤≥≠≈∑∏∫√]|→|←|↔"
    r"|(?<!\w)\d+\s*/\s*[A-Za-zΑ-ω][A-Za-z0-9₀-₉ᵢⱼₖₗₘₙₚᵣₛₜᵤᵥₓ⁰-⁹⁺⁻⁼]*"
    r"|\b[A-Za-zΑ-ω][A-Za-z0-9]*_[A-Za-z0-9]+\b"
    r"|\b[A-Za-zΑ-ω][₀-₉ᵢⱼₖₗₘₙₚᵣₛₜᵤᵥₓ⁰-⁹⁺⁻⁼]+"
    r"|(?<!\w)[A-Za-z](?:_[A-Za-z0-9]+)?\s*\([^)]*\)"
    r")"
)
CORRESPONDENCE_KINDS = {"card", "chip", "panel"}
OCCUPANCY_KINDS = {"card", "chip", "icon", "legend"}


class LayoutError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise LayoutError(f"{label} missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LayoutError(f"invalid {label}: {exc}") from exc


def finding(severity: str, code: str, message: str, check_id: str | None = None) -> dict[str, str]:
    item = {"severity": severity, "code": code, "message": message}
    if check_id:
        item["check_id"] = check_id
    return item


def text_content(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def union_bounds(items: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    if not items:
        raise LayoutError("element has no auditable visible geometry")
    return (
        min(item[0] for item in items),
        min(item[1] for item in items),
        max(item[2] for item in items),
        max(item[3] for item in items),
    )


def clipped_bounds(
    item: tuple[float, float, float, float],
    outer: tuple[float, float, float, float],
) -> tuple[float, float, float, float] | None:
    clipped = (
        max(item[0], outer[0]),
        max(item[1], outer[1]),
        min(item[2], outer[2]),
        min(item[3], outer[3]),
    )
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        return None
    return clipped


def largest_empty_grid_rectangle(
    usable: tuple[float, float, float, float],
    occupied_boxes: list[tuple[float, float, float, float]],
    requested_step: float,
) -> tuple[float, tuple[float, float, float, float], int, int]:
    """Return the largest empty axis-aligned grid rectangle in user units."""
    width = usable[2] - usable[0]
    height = usable[3] - usable[1]
    if width <= 0 or height <= 0 or requested_step <= 0:
        raise LayoutError("panel occupancy has an invalid usable region or grid step")
    columns = max(1, math.ceil(width / requested_step))
    rows = max(1, math.ceil(height / requested_step))
    if columns > 512 or rows > 512:
        raise LayoutError("panel occupancy grid exceeds 512 cells on one axis")
    cell_width = width / columns
    cell_height = height / rows
    occupied = [[False] * columns for _ in range(rows)]
    for row in range(rows):
        cy = usable[1] + (row + 0.5) * cell_height
        for column in range(columns):
            cx = usable[0] + (column + 0.5) * cell_width
            occupied[row][column] = any(
                box[0] <= cx <= box[2] and box[1] <= cy <= box[3]
                for box in occupied_boxes
            )

    heights = [0] * columns
    best_cells = 0
    best = (0, 0, 0, 0)
    for row in range(rows):
        for column in range(columns):
            heights[column] = 0 if occupied[row][column] else heights[column] + 1
        stack: list[int] = []
        for column in range(columns + 1):
            current = heights[column] if column < columns else 0
            while stack and heights[stack[-1]] > current:
                top = stack.pop()
                rectangle_height = heights[top]
                left = stack[-1] + 1 if stack else 0
                rectangle_width = column - left
                area_cells = rectangle_height * rectangle_width
                if area_cells > best_cells:
                    best_cells = area_cells
                    best = (left, row - rectangle_height + 1, column, row + 1)
            stack.append(column)

    left, top, right, bottom = best
    box = (
        usable[0] + left * cell_width,
        usable[1] + top * cell_height,
        usable[0] + right * cell_width,
        usable[1] + bottom * cell_height,
    )
    return best_cells * cell_width * cell_height, box, rows, columns


def visible(element: ET.Element) -> bool:
    tag = base_audit.local(element.tag)
    if tag not in VISIBLE_TAGS:
        return False
    fill = base_audit.color_value(element, "fill", "#000000").casefold()
    stroke = base_audit.color_value(element, "stroke", "none").casefold()
    stroke_visible = False
    if stroke != "none":
        try:
            width_text = element.attrib.get(
                "stroke-width", base_audit.style_map(element).get("stroke-width", "1")
            )
            stroke_visible = base_audit.number(width_text, "stroke-width") > 0
        except ValueError:
            stroke_visible = False
    if tag == "text":
        return bool(text_content(element)) and fill != "none"
    if tag == "line":
        return stroke_visible
    return fill != "none" or stroke_visible


def element_bounds(element: ET.Element) -> tuple[float, float, float, float]:
    tag = base_audit.local(element.tag)
    if tag in VISIBLE_TAGS:
        if not visible(element):
            raise LayoutError("element has no visibly painted geometry")
        bounds=base_audit.geometry_bounds(element)
        if tag in {"line","polyline","path"} and base_audit.color_value(element,"stroke","none")!="none":
            half=base_audit.number(base_audit.color_value(element,"stroke-width","1"),"stroke width")/2
            return bounds[0]-half,bounds[1]-half,bounds[2]+half,bounds[3]+half
        return bounds
    descendant_bounds: list[tuple[float, float, float, float]] = []
    for child in list(element):
        try:
            descendant_bounds.append(element_bounds(child))
        except (ValueError, LayoutError):
            continue
    return union_bounds(descendant_bounds)


def contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float], tolerance: float = 1e-6) -> bool:
    return (
        inner[0] + tolerance >= outer[0]
        and inner[1] + tolerance >= outer[1]
        and inner[2] <= outer[2] + tolerance
        and inner[3] <= outer[3] + tolerance
    )


def panel_header_pair_is_valid(rectangles: list[ET.Element]) -> bool:
    if len(rectangles) != 2:
        return False
    boxes = [(element_bounds(item), item) for item in rectangles]
    boxes.sort(key=lambda item: (item[0][2] - item[0][0]) * (item[0][3] - item[0][1]), reverse=True)
    outer, header = boxes[0][0], boxes[1][0]
    outer_width, outer_height = outer[2] - outer[0], outer[3] - outer[1]
    header_width, header_height = header[2] - header[0], header[3] - header[1]
    if outer_width <= 0 or outer_height <= 0:
        return False
    return (
        contains(outer, header)
        and math.isclose(outer[0], header[0], abs_tol=1e-6)
        and math.isclose(outer_width, header_width, abs_tol=1e-6)
        and math.isclose(outer[1], header[1], abs_tol=max(1e-6, outer_height * 0.02))
        and header_height <= outer_height * 0.45 + 1e-6
    )


def validate_spec_shape(spec: Any) -> None:
    required = {
        "schema_version", "protocol_version", "story_packet_sha256",
        "figure_contract_sha256", "facts_sha256", "placement_width_mm",
        "body_font_size_pt", "components", "checks", "symbols",
    }
    if not isinstance(spec, dict) or set(spec) != required:
        raise LayoutError(f"layout spec fields must be exactly {sorted(required)}")
    if spec["schema_version"] not in {1, 2} or spec["protocol_version"] != PROTOCOL_VERSION:
        raise LayoutError("layout spec requires schema_version 1 or 2 and protocol_version=1.0.0")
    if not isinstance(spec["placement_width_mm"], (int, float)) or spec["placement_width_mm"] <= 0:
        raise LayoutError("layout spec placement_width_mm must be positive")
    if not isinstance(spec["body_font_size_pt"], (int, float)) or spec["body_font_size_pt"] < 5:
        raise LayoutError("layout spec body_font_size_pt must be at least 5")
    for key in ("components", "checks", "symbols"):
        if not isinstance(spec[key], list):
            raise LayoutError(f"layout spec {key} must be a list")
    if not spec["components"]:
        raise LayoutError("layout spec must register at least one component")


def source_contains(anchor: Any, corpus: str) -> bool:
    return isinstance(anchor, str) and bool(anchor.strip()) and anchor.strip() in corpus


def audit_layout(
    svg_path: Path,
    story_path: Path,
    contract_path: Path,
    facts_path: Path,
    caption_path: Path,
    spec_path: Path,
    dispositions_path: Path,
    placement_width_mm: float,
    minimum_text_pt: float,
) -> dict[str, Any]:
    paths = [svg_path, story_path, contract_path, facts_path, caption_path, spec_path, dispositions_path]
    for path in paths:
        if not path.is_file():
            raise LayoutError(f"required input missing: {path}")
    spec = read_json(spec_path, "layout spec")
    validate_spec_shape(spec)
    dispositions = read_json(dispositions_path, "soft dispositions")
    findings: list[dict[str, str]] = []

    bindings = {
        "story_packet_sha256": sha256_file(story_path),
        "figure_contract_sha256": sha256_file(contract_path),
        "facts_sha256": sha256_file(facts_path),
    }
    for key, actual in bindings.items():
        if spec.get(key) != actual:
            findings.append(finding("ERROR", "STALE_BINDING", f"{key} does not match the current source"))
    if not math.isclose(float(spec["placement_width_mm"]), placement_width_mm, abs_tol=1e-6):
        findings.append(finding("ERROR", "PLACEMENT_WIDTH_BINDING", "layout spec and audit placement widths differ"))

    base_report = base_audit.audit(svg_path, placement_width_mm, minimum_text_pt)
    for item in base_report.get("findings", []):
        findings.append(dict(item))

    root = ET.parse(svg_path).getroot()
    elements = list(root.iter())
    by_id: dict[str, ET.Element] = {}
    parents: dict[ET.Element, ET.Element] = {}
    for parent in elements:
        for child in parent:
            parents[child] = parent
        identifier = parent.attrib.get("id")
        if identifier:
            if identifier in by_id:
                findings.append(finding("ERROR", "DUPLICATE_SVG_ID", identifier))
            by_id[identifier] = parent

    # Same-line text collisions are never a legitimate source of density.
    # Restrict the check to nearly coincident vertical centers so deliberate
    # multi-line labels are not treated as collisions.
    visible_text = [
        item for item in elements
        if base_audit.local(item.tag) == "text" and visible(item) and text_content(item)
    ]
    for index, left in enumerate(visible_text):
        left_box = element_bounds(left)
        left_height = left_box[3] - left_box[1]
        left_center_y = (left_box[1] + left_box[3]) / 2
        for right in visible_text[index + 1 :]:
            right_box = element_bounds(right)
            right_height = right_box[3] - right_box[1]
            right_center_y = (right_box[1] + right_box[3]) / 2
            if abs(left_center_y - right_center_y) > 0.35 * min(left_height, right_height):
                continue
            overlap_x = min(left_box[2], right_box[2]) - max(left_box[0], right_box[0])
            overlap_y = min(left_box[3], right_box[3]) - max(left_box[1], right_box[1])
            if overlap_x > 0.5 and overlap_y > 0.5:
                findings.append(finding(
                    "ERROR",
                    "TEXT_TEXT_COLLISION",
                    f"same-line text overlaps: '{text_content(left)}' and '{text_content(right)}'",
                ))

    component_map: dict[str, dict[str, Any]] = {}
    corpus = "\n".join(
        path.read_text(encoding="utf-8") for path in (story_path, contract_path, facts_path)
    )
    allowed_component_keys = {
        "id", "kind", "semantic_role", "source_anchor", "alignment_class",
        "family", "noncorrespondence_reason", "box_purpose",
    }
    for component in spec["components"]:
        if not isinstance(component, dict) or not set(component).issubset(allowed_component_keys):
            findings.append(finding("ERROR", "COMPONENT_SCHEMA", "component contains unsupported fields"))
            continue
        required = {"id", "kind", "semantic_role", "source_anchor", "alignment_class", "box_purpose"}
        if not required.issubset(component):
            findings.append(finding("ERROR", "COMPONENT_SCHEMA", f"component missing {sorted(required - set(component))}"))
            continue
        identifier = str(component["id"])
        if identifier in component_map:
            findings.append(finding("ERROR", "DUPLICATE_COMPONENT", identifier))
            continue
        component_map[identifier] = component
        if identifier not in by_id:
            findings.append(finding("ERROR", "MISSING_COMPONENT", identifier))
            continue
        try:
            bounds = element_bounds(by_id[identifier])
            if bounds[2] - bounds[0] <= 1e-6 or bounds[3] - bounds[1] <= 1e-6:
                findings.append(finding("ERROR", "INVISIBLE_COMPONENT", identifier))
        except (ValueError, LayoutError) as exc:
            findings.append(finding("ERROR", "INVISIBLE_COMPONENT", f"{identifier}: {exc}"))
        if component["alignment_class"] not in {"HARD", "SOFT", "FREE"}:
            findings.append(finding("ERROR", "ALIGNMENT_CLASS", identifier))
        if component["alignment_class"] in {"SOFT", "FREE"}:
            reason = str(component.get("noncorrespondence_reason", "")).strip()
            if len(reason) < 12:
                findings.append(finding("ERROR", "MISSING_NONCORRESPONDENCE_REASON", identifier))
        if not source_contains(component["source_anchor"], corpus):
            findings.append(finding("ERROR", "UNKNOWN_SOURCE_ANCHOR", identifier))

    # Every visible primitive is owned by its nearest registered ancestor. A
    # high-level group may not absorb arbitrary descendant cards: its owned
    # rectangle count must still match its declared component semantics.
    uncovered: list[str] = []
    covered_visible = 0
    total_visible = 0
    owner_by_element: dict[ET.Element, str] = {}
    owned_visible: dict[str, list[ET.Element]] = {}
    for element in elements:
        if not visible(element):
            continue
        total_visible += 1
        cursor: ET.Element | None = element
        owner: str | None = None
        while cursor is not None:
            if cursor.attrib.get("id") in component_map:
                owner = str(cursor.attrib["id"])
                break
            cursor = parents.get(cursor)
        if owner is not None:
            covered_visible += 1
            owner_by_element[element] = owner
            owned_visible.setdefault(owner, []).append(element)
        else:
            uncovered.append(element.attrib.get("id", base_audit.local(element.tag)))
    if uncovered:
        findings.append(finding("ERROR", "UNCOVERED_VISIBLE_GEOMETRY", ", ".join(uncovered[:20])))

    owned_rectangles: dict[str, list[ET.Element]] = {
        identifier: [item for item in items if base_audit.local(item.tag) == "rect"]
        for identifier, items in owned_visible.items()
    }
    for identifier, rectangles in owned_rectangles.items():
        if len(rectangles) <= 1:
            continue
        kind = str(component_map[identifier].get("kind", "")).casefold()
        if kind != "panel" or not panel_header_pair_is_valid(rectangles):
            findings.append(finding(
                "ERROR",
                "SEMANTIC_BOX_OWNERSHIP",
                f"{identifier} owns {len(rectangles)} visible rectangles that require narrower registered components",
            ))

    check_results: list[dict[str, Any]] = []
    seen_check_ids: set[str] = set()
    hard_coverage: dict[str, set[str]] = {}
    view = [float(value) for value in root.attrib["viewBox"].replace(",", " ").split()]
    unit_per_pt = view[2] * POINT_MM / placement_width_mm
    em_units = float(spec["body_font_size_pt"]) * unit_per_pt

    def bound(identifier: str) -> tuple[float, float, float, float]:
        if identifier not in component_map or identifier not in by_id:
            raise LayoutError(f"unknown component {identifier!r}")
        return element_bounds(by_id[identifier])

    def stroke_pt(identifier: str) -> float:
        element = by_id[identifier]
        candidates: list[float] = []
        for item in element.iter():
            if not visible(item):
                continue
            stroke = base_audit.color_value(item, "stroke", "none")
            if stroke.casefold() == "none":
                continue
            width_text = item.attrib.get("stroke-width", base_audit.style_map(item).get("stroke-width", "1"))
            candidates.append(base_audit.number(width_text, "stroke-width") / unit_per_pt)
        if not candidates:
            raise LayoutError(f"component {identifier!r} has no visible stroke")
        return sum(candidates) / len(candidates)

    for check in spec["checks"]:
        check_id = str(check.get("id", "")) if isinstance(check, dict) else ""
        if not check_id or check_id in seen_check_ids:
            findings.append(finding("ERROR", "CHECK_ID", f"missing or duplicate check id {check_id!r}"))
            continue
        seen_check_ids.add(check_id)
        check_type = check.get("type")
        alignment_class = check.get("alignment_class")
        if alignment_class not in {"HARD", "SOFT"}:
            findings.append(finding("ERROR", "CHECK_CLASS", check_id, check_id))
            continue
        tolerance = float(check.get("tolerance_em", 0.08)) * em_units
        passed = False
        delta = math.inf
        referenced: list[str] = []
        hard_coverage_referenced: list[str] = []
        metrics: dict[str, Any] | None = None
        try:
            if check_type in ALIGN_TYPES:
                referenced = list(check.get("elements", []))
                if len(referenced) < 2:
                    raise LayoutError("alignment check needs at least two elements")
                values: list[float] = []
                for identifier in referenced:
                    box = bound(identifier)
                    selector = ALIGN_TYPES[check_type]
                    if selector == "center_x":
                        values.append((box[0] + box[2]) / 2)
                    elif selector == "center_y":
                        values.append((box[1] + box[3]) / 2)
                    elif selector == "baseline":
                        element = by_id[identifier]
                        if base_audit.local(element.tag) != "text":
                            raise LayoutError("baseline checks require text component IDs")
                        values.append(base_audit.number(element.attrib.get("y"), "text y"))
                    else:
                        values.append(box[int(selector)])
                delta = max(values) - min(values)
                passed = delta <= tolerance + 1e-9
            elif check_type == "equal_size":
                referenced = list(check.get("elements", []))
                if len(referenced) < 2:
                    raise LayoutError("equal_size needs at least two elements")
                boxes = [bound(identifier) for identifier in referenced]
                widths = [item[2] - item[0] for item in boxes]
                heights = [item[3] - item[1] for item in boxes]
                delta = max(max(widths) - min(widths), max(heights) - min(heights))
                passed = delta <= tolerance + 1e-9
            elif check_type == "containment":
                container = str(check.get("container", ""))
                contents = list(check.get("contents", []))
                referenced = [container, *contents]
                if not container or not contents:
                    raise LayoutError("containment requires container and contents")
                outer = micro_layout_audit.fixed_bounds(by_id[container])
                minimum = float(check.get("min_padding_em", 0.35)) * em_units
                deficits: list[float] = []
                for identifier in contents:
                    inner = bound(identifier)
                    paddings = [inner[0] - outer[0], inner[1] - outer[1], outer[2] - inner[2], outer[3] - inner[3]]
                    deficits.append(max(0.0, minimum - min(paddings)))
                delta = max(deficits)
                passed = delta <= 1e-9
            elif check_type == "center_in":
                container = str(check.get("container", ""))
                content = str(check.get("content", ""))
                referenced = [container, content]
                outer, inner = micro_layout_audit.fixed_bounds(by_id[container]), bound(content)
                axis = check.get("axis", "both")
                dx = abs((outer[0] + outer[2] - inner[0] - inner[2]) / 2)
                dy = abs((outer[1] + outer[3] - inner[1] - inner[3]) / 2)
                delta = max(([dx] if axis == "x" else []) + ([dy] if axis == "y" else []) + ([dx, dy] if axis == "both" else []))
                passed = delta <= tolerance + 1e-9
            elif check_type == "stroke_family":
                referenced = list(check.get("elements", []))
                if len(referenced) < 2:
                    raise LayoutError("stroke_family needs at least two elements")
                values = [stroke_pt(identifier) for identifier in referenced]
                low = float(check.get("min_pt", 0.25))
                high = float(check.get("max_pt", 1.0))
                allowed_delta = float(check.get("max_delta_pt", 0.15))
                delta = max(values) - min(values)
                passed = min(values) + 1e-9 >= low and max(values) <= high + 1e-9 and delta <= allowed_delta + 1e-9
            elif check_type == "panel_occupancy":
                if spec["schema_version"] != 2:
                    raise LayoutError("panel_occupancy requires layout-spec schema_version=2")
                if alignment_class != "HARD" and not (alignment_class == "SOFT" and root.get("data-layout-profile") == "measured-v1"):
                    raise LayoutError("panel_occupancy must be HARD, or a resolved SOFT diagnostic in measured-v1")
                container = str(check.get("container", ""))
                contents = list(check.get("contents", []))
                references = list(check.get("reference_components", []))
                referenced = list(dict.fromkeys([container, *contents, *references]))
                hard_coverage_referenced = [container]
                if not container or len(contents) < 2 or not references:
                    raise LayoutError(
                        "panel_occupancy requires a container, at least two contents, and reference_components"
                    )
                if component_map.get(container, {}).get("kind") != "panel":
                    raise LayoutError("panel_occupancy container must be a registered panel")
                if not set(references).issubset(contents):
                    raise LayoutError("panel_occupancy reference_components must be a subset of contents")
                for identifier in contents:
                    kind = str(component_map.get(identifier, {}).get("kind", "")).casefold()
                    if kind not in OCCUPANCY_KINDS:
                        raise LayoutError(
                            f"panel_occupancy content {identifier!r} has ineligible kind {kind!r}"
                        )

                insets = check.get("usable_insets_em")
                if not isinstance(insets, dict) or set(insets) != {"top", "right", "bottom", "left"}:
                    raise LayoutError("panel_occupancy usable_insets_em needs top, right, bottom, and left")
                inset_values = {key: float(insets[key]) for key in insets}
                if any(value < 0 for value in inset_values.values()):
                    raise LayoutError("panel_occupancy insets cannot be negative")
                if inset_values["top"] > 4 or any(
                    inset_values[key] > 2 for key in ("right", "bottom", "left")
                ):
                    raise LayoutError("panel_occupancy insets exceed the anti-cropping limits")
                min_span_x = float(check.get("min_span_x_ratio", 0))
                min_span_y = float(check.get("min_span_y_ratio", 0))
                max_blank_ratio = float(check.get("max_blank_to_reference_area", 0))
                grid_step_em = float(check.get("grid_step_em", 0))
                if not (0.75 <= min_span_x <= 1 and 0.75 <= min_span_y <= 1):
                    raise LayoutError("panel_occupancy span ratios must be within [0.75, 1]")
                if not (0 < max_blank_ratio <= 1):
                    raise LayoutError("panel_occupancy blank ratio must be within (0, 1]")
                if not (0.2 <= grid_step_em <= 0.5):
                    raise LayoutError("panel_occupancy grid_step_em must be within [0.2, 0.5]")

                outer = micro_layout_audit.fixed_bounds(by_id[container])
                usable = (
                    outer[0] + inset_values["left"] * em_units,
                    outer[1] + inset_values["top"] * em_units,
                    outer[2] - inset_values["right"] * em_units,
                    outer[3] - inset_values["bottom"] * em_units,
                )
                if usable[2] <= usable[0] or usable[3] <= usable[1]:
                    raise LayoutError("panel_occupancy insets consume the panel body")
                clipped: list[tuple[float, float, float, float]] = []
                for identifier in contents:
                    content_box = bound(identifier)
                    if not contains(outer, content_box, tolerance=1e-4):
                        raise LayoutError(f"panel_occupancy content {identifier!r} leaves its panel")
                    item = clipped_bounds(content_box, usable)
                    if item is None:
                        raise LayoutError(f"panel_occupancy content {identifier!r} misses the usable body")
                    clipped.append(item)
                reference_areas = []
                for identifier in references:
                    item = clipped_bounds(bound(identifier), usable)
                    if item is None:
                        raise LayoutError(f"panel_occupancy reference {identifier!r} misses the usable body")
                    reference_areas.append((item[2] - item[0]) * (item[3] - item[1]))
                reference_area = statistics.median(reference_areas)
                if reference_area <= 0:
                    raise LayoutError("panel_occupancy reference footprint is empty")
                content_union = union_bounds(clipped)
                usable_width = usable[2] - usable[0]
                usable_height = usable[3] - usable[1]
                span_x = (content_union[2] - content_union[0]) / usable_width
                span_y = (content_union[3] - content_union[1]) / usable_height
                blank_area, blank_box, rows, columns = largest_empty_grid_rectangle(
                    usable, clipped, grid_step_em * em_units
                )
                blank_ratio = blank_area / reference_area
                violations = [
                    max(0.0, min_span_x - span_x),
                    max(0.0, min_span_y - span_y),
                    max(0.0, blank_ratio - max_blank_ratio),
                ]
                delta = max(violations)
                tolerance = 0.0
                passed = delta <= 1e-9
                metrics = {
                    "usable_bounds": [round(value, 6) for value in usable],
                    "content_span_x_ratio": round(span_x, 6),
                    "content_span_y_ratio": round(span_y, 6),
                    "largest_blank_bounds": [round(value, 6) for value in blank_box],
                    "largest_blank_area": round(blank_area, 6),
                    "reference_module_area": round(reference_area, 6),
                    "blank_to_reference_area": round(blank_ratio, 6),
                    "grid_rows": rows,
                    "grid_columns": columns,
                }
            else:
                raise LayoutError(f"unsupported check type {check_type!r}")
            if any(component_map[item]["alignment_class"] == "FREE" for item in referenced if item in component_map):
                raise LayoutError("FREE components may not participate in alignment checks")
            if alignment_class == "HARD":
                for identifier in (hard_coverage_referenced or referenced):
                    hard_coverage.setdefault(identifier, set()).add(check_id)
        except (KeyError, TypeError, ValueError, LayoutError) as exc:
            findings.append(finding("ERROR", "CHECK_CONFIGURATION", str(exc), check_id))
            passed = False
        check_result = {
            "id": check_id,
            "type": check_type,
            "alignment_class": alignment_class,
            "passed": passed,
            "delta_user_units": None if math.isinf(delta) else round(delta, 6),
            "tolerance_user_units": round(tolerance, 6),
            "elements": referenced,
        }
        if metrics is not None:
            check_result["metrics"] = metrics
        check_results.append(check_result)
        if not passed and alignment_class == "HARD":
            findings.append(finding("ERROR", "HARD_LAYOUT_MISMATCH", f"{check_type} exceeds tolerance", check_id))

    if spec["schema_version"] == 2:
        occupancy_by_panel: dict[str, list[dict[str, Any]]] = {}
        for check in spec["checks"]:
            if not isinstance(check, dict) or check.get("type") != "panel_occupancy":
                continue
            if check.get("alignment_class") == "HARD" or (root.get("data-layout-profile") == "measured-v1" and check.get("alignment_class") == "SOFT"):
                occupancy_by_panel.setdefault(str(check.get("container", "")), []).append(check)
        for identifier, component in component_map.items():
            if str(component.get("kind", "")).casefold() != "panel":
                continue
            checks = occupancy_by_panel.get(identifier, [])
            if len(checks) != 1:
                findings.append(finding(
                    "ERROR",
                    "PANEL_OCCUPANCY_COVERAGE",
                    f"{identifier} requires exactly one panel_occupancy check; measured-v1 also permits a resolved SOFT diagnostic; found {len(checks)}",
                ))

    families: dict[str, list[str]] = {}
    for identifier, component in component_map.items():
        family = component.get("family")
        if family:
            families.setdefault(str(family), []).append(identifier)
    for family, members in families.items():
        if len(members) < 2:
            continue
        if any(component_map[item]["alignment_class"] == "FREE" for item in members):
            findings.append(finding("ERROR", "FREE_REPEATED_FAMILY", family))
        if any(not hard_coverage.get(item) for item in members):
            findings.append(finding("ERROR", "REPEATED_FAMILY_WITHOUT_HARD_CHECK", f"{family}: {members}"))

    for identifier, component in component_map.items():
        if str(component.get("kind", "")).casefold() not in CORRESPONDENCE_KINDS:
            continue
        family = str(component.get("family", "")).strip()
        reason = str(component.get("noncorrespondence_reason", "")).strip()
        if not family or len(families.get(family, [])) < 2:
            if len(reason) < 12:
                findings.append(finding(
                    "ERROR",
                    "UNDECLARED_COMPONENT_CORRESPONDENCE",
                    f"{identifier} must join a repeated family or explain why it has no corresponding peer",
                ))

    symbol_map: dict[str, dict[str, Any]] = {}
    for symbol in spec["symbols"]:
        if not isinstance(symbol, dict):
            findings.append(finding("ERROR", "SYMBOL_SCHEMA", "symbol record must be an object"))
            continue
        required = {"element_id", "token", "meaning", "source_anchor", "caption_label"}
        if set(symbol) != required:
            findings.append(finding("ERROR", "SYMBOL_SCHEMA", "symbol record fields are incomplete"))
            continue
        identifier = str(symbol["element_id"])
        symbol_map[identifier] = symbol
        if identifier not in by_id:
            findings.append(finding("ERROR", "MISSING_SYMBOL", identifier))
            continue
        actual_text = text_content(by_id[identifier])
        if str(symbol["token"]) not in actual_text:
            findings.append(finding("ERROR", "SYMBOL_TOKEN_MISMATCH", identifier))
        if not source_contains(symbol["source_anchor"], corpus):
            findings.append(finding("ERROR", "UNKNOWN_SYMBOL_ANCHOR", identifier))
        if str(symbol["caption_label"]) not in caption_path.read_text(encoding="utf-8"):
            findings.append(finding("ERROR", "SYMBOL_NOT_IN_CAPTION", identifier))

    for identifier, component in component_map.items():
        element = by_id.get(identifier)
        if element is None:
            continue
        visible_rect = any(base_audit.local(item.tag) == "rect" and visible(item) for item in element.iter())
        if component["kind"] in {"symbol", "formula"}:
            if identifier not in symbol_map:
                findings.append(finding("ERROR", "UNEXPLAINED_SYMBOL", identifier))
            if visible_rect and component["box_purpose"] not in BOX_PURPOSES:
                findings.append(finding("ERROR", "ORNAMENTAL_SYMBOL_BOX", identifier))
        for item in element.iter():
            if base_audit.local(item.tag) == "text" and STANDALONE_SYMBOL.match(text_content(item)):
                item_id = item.attrib.get("id", "")
                if item_id not in symbol_map:
                    findings.append(finding("ERROR", "UNEXPLAINED_STANDALONE_SYMBOL", text_content(item)))

    visible_rectangles = [
        item for item in elements
        if base_audit.local(item.tag) == "rect" and visible(item)
    ]
    for item in elements:
        if base_audit.local(item.tag) != "text" or not visible(item):
            continue
        token = text_content(item)
        if not FORMULA_TEXT.search(token):
            continue
        identifier = item.attrib.get("id", "")
        if not identifier or identifier not in component_map:
            findings.append(finding("ERROR", "UNREGISTERED_FORMULA_TEXT", token))
            continue
        component = component_map[identifier]
        if str(component.get("kind", "")).casefold() not in {"formula", "symbol"}:
            findings.append(finding("ERROR", "FORMULA_KIND_MISMATCH", identifier))
        if identifier not in symbol_map:
            findings.append(finding("ERROR", "UNEXPLAINED_FORMULA", identifier))

        text_box = element_bounds(item)
        enclosing: list[tuple[float, str]] = []
        for rectangle in visible_rectangles:
            box = element_bounds(rectangle)
            if not contains(box, text_box):
                continue
            owner = owner_by_element.get(rectangle)
            if not owner:
                continue
            owner_component = component_map[owner]
            if str(owner_component.get("kind", "")).casefold() == "background":
                continue
            area = (box[2] - box[0]) * (box[3] - box[1])
            enclosing.append((area, owner))
        if enclosing:
            _, box_owner = min(enclosing)
            box_component = component_map[box_owner]
            if box_component.get("box_purpose") not in BOX_PURPOSES:
                findings.append(finding("ERROR", "ORNAMENTAL_FORMULA_BOX", box_owner))
            owner_rectangles = owned_rectangles.get(box_owner, [])
            owner_box = min(
                (element_bounds(rectangle) for rectangle in owner_rectangles),
                key=lambda box: (box[2] - box[0]) * (box[3] - box[1]),
                default=None,
            )
            enclosed_nonformula_text = [
                child for child in elements
                if owner_box is not None
                and base_audit.local(child.tag) == "text"
                and child is not item
                and visible(child)
                and contains(owner_box, element_bounds(child))
                and not FORMULA_TEXT.search(text_content(child))
            ]
            if (
                not enclosed_nonformula_text
                and str(box_component.get("kind", "")).casefold() not in {"formula", "symbol"}
            ):
                findings.append(finding("ERROR", "MISCLASSIFIED_FORMULA_BOX", box_owner))

    spec_hash = sha256_file(spec_path)
    if not isinstance(dispositions, dict) or set(dispositions) != {"schema_version", "protocol_version", "layout_spec_sha256", "dispositions"}:
        findings.append(finding("ERROR", "DISPOSITION_SCHEMA", "soft disposition fields are invalid"))
        disposition_items: list[Any] = []
    else:
        disposition_items = dispositions.get("dispositions", [])
        if dispositions.get("schema_version") != 1 or dispositions.get("protocol_version") != PROTOCOL_VERSION:
            findings.append(finding("ERROR", "DISPOSITION_VERSION", "soft disposition version mismatch"))
        if dispositions.get("layout_spec_sha256") != spec_hash:
            findings.append(finding("ERROR", "STALE_DISPOSITIONS", "soft dispositions are bound to another layout spec"))
    disposition_map: dict[str, dict[str, Any]] = {}
    for item in disposition_items if isinstance(disposition_items, list) else []:
        if not isinstance(item, dict) or set(item) != {"check_id", "status", "reason"}:
            findings.append(finding("ERROR", "DISPOSITION_SCHEMA", "each disposition needs check_id, status, and reason"))
            continue
        disposition_map[str(item["check_id"])] = item
    soft_results = {item["id"]: item for item in check_results if item["alignment_class"] == "SOFT"}
    if set(disposition_map) != set(soft_results):
        findings.append(finding("ERROR", "DISPOSITION_COVERAGE", f"expected {sorted(soft_results)}, got {sorted(disposition_map)}"))
    for check_id, result in soft_results.items():
        disposition = disposition_map.get(check_id)
        if not disposition:
            continue
        expected = "ADJUSTED" if result["passed"] else "KEPT_WITH_REASON"
        if disposition.get("status") != expected:
            findings.append(finding("ERROR", "DISPOSITION_STATUS", f"{check_id} requires {expected}", check_id))
        if len(str(disposition.get("reason", "")).strip()) < 12:
            findings.append(finding("ERROR", "DISPOSITION_REASON", check_id, check_id))
        if not result["passed"]:
            findings.append(finding("WARN", "RESOLVED_SOFT_MISMATCH", str(disposition.get("reason", "")), check_id))

    micro_report = micro_layout_audit.audit(root)
    findings.extend(micro_report["findings"])
    errors = sum(item["severity"] == "ERROR" for item in findings)
    warnings = sum(item["severity"] == "WARN" for item in findings)
    return {
        "schema_version": 2,
        "protocol_version": PROTOCOL_VERSION,
        "layout_spec_schema_version": spec["schema_version"],
        "status": "PASS" if errors == 0 else "FAIL",
        "svg": {"path": str(svg_path.resolve()), "sha256": sha256_file(svg_path)},
        "layout_spec": {"path": str(spec_path.resolve()), "sha256": spec_hash},
        "soft_dispositions": {"path": str(dispositions_path.resolve()), "sha256": sha256_file(dispositions_path)},
        "source_bindings": bindings,
        "placement_width_mm": placement_width_mm,
        "coverage": {"visible_total": total_visible, "visible_registered": covered_visible, "ratio": 0 if total_visible == 0 else covered_visible / total_visible},
        "semantic_ownership": {
            "registered_components": len(component_map),
            "owned_visible_primitives": covered_visible,
            "owners_with_multiple_rectangles": sorted(
                identifier for identifier, items in owned_rectangles.items() if len(items) > 1
            ),
        },
        "base_audit": {"status": base_report.get("status"), "master_sha256": base_report.get("master_sha256")},
        "micro_layout": micro_report,
        "checks": check_results,
        "error_count": errors,
        "warning_count": warnings,
        "findings": findings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--story-packet", type=Path, required=True)
    parser.add_argument("--figure-contract", type=Path, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--caption", type=Path, required=True)
    parser.add_argument("--layout-spec", type=Path, required=True)
    parser.add_argument("--soft-dispositions", type=Path, required=True)
    parser.add_argument("--placement-width-mm", type=float, required=True)
    parser.add_argument("--minimum-text-pt", type=float, default=7.0)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = audit_layout(
            args.svg, args.story_packet, args.figure_contract, args.facts,
            args.caption, args.layout_spec, args.soft_dispositions,
            args.placement_width_mm, args.minimum_text_pt,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (LayoutError, ET.ParseError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"{report['status']}: {report['error_count']} errors, {report['warning_count']} warnings")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
