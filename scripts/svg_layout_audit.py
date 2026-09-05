#!/usr/bin/env python3
"""Audit deterministic, machine-checkable SVG motivation-figure properties."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from font_metrics import text_bounds as measured_text_bounds


POINT_MM = 25.4 / 72.0
ALIGNMENT_TOLERANCE = 0.5
HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{6})$")
PLACEHOLDER = re.compile(r"\b(?:TBD|TODO|PLACEHOLDER)\b", re.IGNORECASE)
ALLOWED_TAGS = {
    "svg",
    "g",
    "defs",
    "marker",
    "title",
    "desc",
    "rect",
    "circle",
    "ellipse",
    "polygon",
    "polyline",
    "line",
    "path",
    "text",
    "tspan",
}
FORBIDDEN_PRESENTATION = {"opacity", "fill-opacity", "stroke-opacity", "display", "visibility", "clip-path"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def number(value: str | None, label: str) -> float:
    if value is None:
        raise ValueError(f"missing {label}")
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*", value)
    if not match:
        raise ValueError(f"{label} must be a plain number, got {value!r}")
    return float(match.group(1))


def physical_mm(value: str | None, label: str) -> float:
    if value is None:
        raise ValueError(f"missing {label}")
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)mm\s*", value)
    if not match:
        raise ValueError(f"{label} must use mm units, got {value!r}")
    return float(match.group(1))


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def style_map(element: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in element.attrib.get("style", "").split(";"):
        if ":" in item:
            key, value = item.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def color_value(element: ET.Element, name: str, default: str) -> str:
    return element.attrib.get(name, style_map(element).get(name, default)).strip()


def srgb_channel(value: int) -> float:
    normalized = value / 255.0
    return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float | None:
    match = HEX_COLOR.fullmatch(color)
    if not match:
        return None
    digits = match.group(1)
    red, green, blue = (int(digits[index : index + 2], 16) for index in (0, 2, 4))
    return 0.2126 * srgb_channel(red) + 0.7152 * srgb_channel(green) + 0.0722 * srgb_channel(blue)


def contrast_ratio(foreground: str, background: str = "#ffffff") -> float | None:
    first, second = luminance(foreground), luminance(background)
    if first is None or second is None:
        return None
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def parse_points(value: str) -> list[tuple[float, float]]:
    numbers = [float(item) for item in re.findall(r"-?\d+(?:\.\d+)?", value)]
    if len(numbers) < 4 or len(numbers) % 2:
        raise ValueError("points must contain at least two x,y pairs")
    return list(zip(numbers[0::2], numbers[1::2]))


def in_view(x: float, y: float, view: list[float]) -> bool:
    min_x, min_y, width, height = view
    return min_x <= x <= min_x + width and min_y <= y <= min_y + height


def contains_bounds(container: tuple[float, float, float, float], bounds: tuple[float, float, float, float]) -> bool:
    return (
        container[0] <= bounds[0]
        and container[1] <= bounds[1]
        and container[2] >= bounds[2]
        and container[3] >= bounds[3]
    )


def intersects_bounds(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    return first[0] < second[2] and first[2] > second[0] and first[1] < second[3] and first[3] > second[1]


def segment_intersects_bounds(
    start: tuple[float, float],
    end: tuple[float, float],
    bounds: tuple[float, float, float, float],
) -> bool:
    """Return whether a line segment reaches a closed axis-aligned rectangle."""
    left, top, right, bottom = bounds
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    lower, upper = 0.0, 1.0
    for coefficient, offset in (
        (-dx, x1 - left),
        (dx, right - x1),
        (-dy, y1 - top),
        (dy, bottom - y1),
    ):
        if abs(coefficient) < 1e-12:
            if offset < 0:
                return False
            continue
        ratio = offset / coefficient
        if coefficient < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return False
    return True


def text_bounds(element: ET.Element, font_size: float) -> tuple[float, float, float, float]:
    return measured_text_bounds(element, font_size)


def stroke_segments(element):
    tag=local(element.tag)
    if tag=="rect":
        x,y,w,h=(number(element.get(k,"0"),k) for k in ("x","y","width","height"))
        points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
    elif tag=="line":
        points=[(number(element.get("x1"),"x1"),number(element.get("y1"),"y1")),(number(element.get("x2"),"x2"),number(element.get("y2"),"y2"))]
    elif tag in {"polygon","polyline"}:
        points=parse_points(element.get("points",""))
        if tag=="polygon" and points[-1]!=points[0]: points.append(points[0])
    elif tag=="path":
        data=element.get("d","")
        if set(re.findall(r"[A-Za-z]",data)) - set("MLHVZmlhvzeE"):
            raise ValueError("Expand curved paths into tested primitives before geometry audit")
        tokens=re.findall(r"[MLHVZmlhvz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",data)
        index=0; command=None; current=(0.,0.); start=None; segments=[]
        while index<len(tokens):
            if tokens[index].isalpha():
                command=tokens[index];index+=1
            if command is None: raise ValueError("Path lacks a command")
            op=command.upper();relative=command.islower()
            if op=="Z":
                if start is None: raise ValueError("Close before move")
                segments.append((current,start));current=start;command=None;continue
            count=2 if op in {"M","L"} else 1
            if index+count>len(tokens): raise ValueError("Incomplete path command")
            values=list(map(float,tokens[index:index+count]));index+=count
            if op in {"M","L"}: target=(values[0]+(current[0] if relative else 0),values[1]+(current[1] if relative else 0))
            elif op=="H": target=(values[0]+(current[0] if relative else 0),current[1])
            elif op=="V": target=(current[0],values[0]+(current[1] if relative else 0))
            else: raise ValueError("Unsupported path command")
            if op=="M": start=target;command="l" if relative else "L"
            else: segments.append((current,target))
            current=target
        return segments
    else: return []
    return list(zip(points,points[1:]))


def geometry_bounds(element: ET.Element) -> tuple[float, float, float, float]:
    tag = local(element.tag)
    if tag == "path":
        points=[p for segment in stroke_segments(element) for p in segment]
        if not points: raise ValueError("Path has no explicit auditable segments")
        return min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)
    if tag == "rect":
        x = number(element.attrib.get("x", "0"), "rect x")
        y = number(element.attrib.get("y", "0"), "rect y")
        width = number(element.attrib.get("width"), "rect width")
        height = number(element.attrib.get("height"), "rect height")
        return x, y, x + width, y + height
    if tag == "circle":
        center_x = number(element.attrib.get("cx"), "circle cx")
        center_y = number(element.attrib.get("cy"), "circle cy")
        radius = number(element.attrib.get("r"), "circle r")
        return center_x - radius, center_y - radius, center_x + radius, center_y + radius
    if tag == "ellipse":
        center_x = number(element.attrib.get("cx"), "ellipse cx")
        center_y = number(element.attrib.get("cy"), "ellipse cy")
        radius_x = number(element.attrib.get("rx"), "ellipse rx")
        radius_y = number(element.attrib.get("ry"), "ellipse ry")
        return center_x - radius_x, center_y - radius_y, center_x + radius_x, center_y + radius_y
    if tag == "line":
        x1 = number(element.attrib.get("x1"), "line x1")
        y1 = number(element.attrib.get("y1"), "line y1")
        x2 = number(element.attrib.get("x2"), "line x2")
        y2 = number(element.attrib.get("y2"), "line y2")
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
    if tag in {"polygon", "polyline"}:
        points = parse_points(element.attrib.get("points", ""))
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs), max(ys)
    if tag == "text":
        return text_bounds(element, number(element.attrib.get("font-size"), "text font-size"))
    raise ValueError(f"alignment annotations are unsupported on {tag}")


def append_group(groups: dict[str, list[tuple[Any, str]]], name: str, value: Any, label: str) -> None:
    if not name.strip():
        raise ValueError("alignment group name cannot be empty")
    groups.setdefault(name, []).append((value, label))


def visibly_painted(
    element: ET.Element,
    bounds: tuple[float, float, float, float],
    background: str,
) -> bool:
    tag = local(element.tag)
    left, top, right, bottom = bounds
    span_x, span_y = right - left, bottom - top
    if tag in {"line", "polyline"}:
        if max(span_x, span_y) <= ALIGNMENT_TOLERANCE:
            return False
    elif span_x <= ALIGNMENT_TOLERANCE or span_y <= ALIGNMENT_TOLERANCE:
        return False

    colors: list[str] = []
    if tag == "text":
        colors.append(color_value(element, "fill", "#000000"))
    elif tag in {"line", "polyline"}:
        stroke = color_value(element, "stroke", "none")
        if stroke.casefold() != "none":
            try:
                if number(element.attrib.get("stroke-width", "1"), "stroke width") > 0:
                    colors.append(stroke)
            except ValueError:
                return False
    else:
        fill = color_value(element, "fill", "#000000")
        stroke = color_value(element, "stroke", "none")
        if fill.casefold() != "none":
            colors.append(fill)
        if stroke.casefold() != "none":
            try:
                if number(element.attrib.get("stroke-width", "1"), "stroke width") > 0:
                    colors.append(stroke)
            except ValueError:
                return False

    for color in colors:
        ratio = contrast_ratio(color, background)
        if ratio is not None and ratio >= 1.1:
            return True
    return False


def audit(svg_path: Path, placement_width_mm: float, minimum_text_pt: float = 7.0) -> dict[str, Any]:
    root = ET.parse(svg_path).getroot()
    findings: list[dict[str, str]] = []
    elements = list(root.iter())
    parents = {child: parent for parent in elements for child in parent}

    try:
        view = [float(value) for value in root.attrib["viewBox"].replace(",", " ").split()]
        if len(view) != 4 or view[2] <= 0 or view[3] <= 0:
            raise ValueError("viewBox requires four values with positive width and height")
        min_x, min_y, width, height = view
    except (KeyError, ValueError) as exc:
        return {
            "status": "FAIL",
            "file": str(svg_path.resolve()),
            "master_sha256": sha256_file(svg_path),
            "findings": [{"severity": "ERROR", "code": "VIEWBOX", "message": str(exc)}],
        }

    try:
        declared_width = physical_mm(root.attrib.get("width"), "width")
        declared_height = physical_mm(root.attrib.get("height"), "height")
        if not math.isclose(declared_width, placement_width_mm, abs_tol=0.2):
            findings.append({"severity": "ERROR", "code": "PLACEMENT_WIDTH", "message": f"declared width {declared_width:g} mm differs from requested {placement_width_mm:g} mm"})
        expected_height = placement_width_mm * height / width
        if not math.isclose(declared_height, expected_height, abs_tol=0.2):
            findings.append({"severity": "ERROR", "code": "ASPECT_RATIO", "message": f"declared height {declared_height:g} mm differs from viewBox ratio {expected_height:g} mm"})
    except ValueError as exc:
        findings.append({"severity": "ERROR", "code": "PHYSICAL_SIZE", "message": str(exc)})

    unit_mm = placement_width_mm / width
    painted_shapes: list[tuple[int, float, float, float, float, str]] = []
    painted_strokes: list[tuple[list[tuple[tuple[float, float], tuple[float, float]]], float, str]] = []
    for order, element in enumerate(elements):
        tag = local(element.tag)
        try:
            fill = color_value(element, "fill", "#000000")
            if tag == "rect" and fill.casefold() != "none":
                x = number(element.attrib.get("x", "0"), "rect x")
                y = number(element.attrib.get("y", "0"), "rect y")
                shape_width = number(element.attrib.get("width"), "rect width")
                shape_height = number(element.attrib.get("height"), "rect height")
                painted_shapes.append((order, x, y, x + shape_width, y + shape_height, fill))
            elif tag == "circle" and fill.casefold() != "none":
                center_x = number(element.attrib.get("cx"), "circle cx")
                center_y = number(element.attrib.get("cy"), "circle cy")
                radius = number(element.attrib.get("r"), "circle r")
                painted_shapes.append((order, center_x - radius, center_y - radius, center_x + radius, center_y + radius, fill))
            elif tag == "ellipse" and fill.casefold() != "none":
                center_x = number(element.attrib.get("cx"), "ellipse cx")
                center_y = number(element.attrib.get("cy"), "ellipse cy")
                radius_x = number(element.attrib.get("rx"), "ellipse rx")
                radius_y = number(element.attrib.get("ry"), "ellipse ry")
                painted_shapes.append((order, center_x - radius_x, center_y - radius_y, center_x + radius_x, center_y + radius_y, fill))
            elif tag in {"polygon", "polyline"} and fill.casefold() != "none":
                points = parse_points(element.attrib.get("points", ""))
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                painted_shapes.append((order, min(xs), min(ys), max(xs), max(ys), fill))
        except ValueError:
            pass
        if tag in {"line", "polyline", "polygon", "rect", "path"}:
            try:
                stroke = color_value(element, "stroke", "none")
                stroke_width = number(element.attrib.get("stroke-width", "1"), "stroke width")
                if stroke.casefold() == "none" or stroke_width <= 0:
                    continue
                segments = stroke_segments(element)
                painted_strokes.append((segments, stroke_width / 2, element.attrib.get("id", tag)))
            except ValueError as exc:
                findings.append({"severity":"ERROR","code":"STROKE_GEOMETRY_UNAUDITED","message":str(exc)})
    slash_text: list[str] = []
    minimum_seen = math.inf
    text_count = 0
    connector_count = 0
    left_groups: dict[str, list[tuple[Any, str]]] = {}
    right_groups: dict[str, list[tuple[Any, str]]] = {}
    center_x_groups: dict[str, list[tuple[Any, str]]] = {}
    center_y_groups: dict[str, list[tuple[Any, str]]] = {}
    bottom_groups: dict[str, list[tuple[Any, str]]] = {}
    baseline_groups: dict[str, list[tuple[Any, str]]] = {}
    equal_size_groups: dict[str, list[tuple[Any, str]]] = {}
    balance_x_groups: dict[str, list[tuple[Any, str]]] = {}

    for order, element in enumerate(elements):
        tag = local(element.tag)
        styles = style_map(element)
        if styles:
            findings.append({"severity":"ERROR","code":"INLINE_STYLE_NOT_AUDITED","message":"Expand inline CSS into explicit presentation attributes before auditing"})
        if tag not in ALLOWED_TAGS:
            findings.append({"severity": "ERROR", "code": "UNSUPPORTED_ELEMENT", "message": f"unsupported SVG element: {tag}"})
        presentation_keys = FORBIDDEN_PRESENTATION.intersection(set(element.attrib) | set(styles))
        if presentation_keys:
            findings.append({"severity": "ERROR", "code": "PRESENTATION_NOT_AUDITED", "message": f"expand visibility and clipping instead of using {sorted(presentation_keys)} on {tag}"})
        if tag in {"linearGradient", "radialGradient", "filter", "pattern", "mask"}:
            findings.append({"severity": "ERROR", "code": "DECORATIVE_EFFECT", "message": f"disallowed SVG element: {tag}"})
        if tag in {"image", "foreignObject", "script", "style", "use"}:
            findings.append({"severity": "ERROR", "code": "RASTER_OR_EXTERNAL_CONTENT", "message": f"SVG master may not contain {tag} elements"})
        if tag == "path" and color_value(element, "fill", "#000000").casefold() != "none":
            ancestor = parents.get(element)
            inside_defs = False
            while ancestor is not None:
                if local(ancestor.tag) == "defs":
                    inside_defs = True
                    break
                ancestor = parents.get(ancestor)
            if not inside_defs:
                findings.append({"severity": "ERROR", "code": "FILLED_PATH_UNAUDITED", "message": "convert filled paths to audited primitive shapes"})
        if "transform" in element.attrib or "transform" in style_map(element):
            findings.append({"severity": "ERROR", "code": "TRANSFORM_NOT_AUDITED", "message": f"expand geometry instead of using transform on {tag}"})

        alignment_attributes = {
            "data-align-left",
            "data-align-right",
            "data-align-center-x",
            "data-align-center-y",
            "data-align-bottom",
            "data-align-baseline",
            "data-equal-size",
            "data-balance-center-x",
        }.intersection(element.attrib)
        if alignment_attributes:
            label = element.attrib.get("id", tag)
            try:
                left, top, right, bottom = geometry_bounds(element)
                geometry_box = (left, top, right, bottom)
                containers = [
                    item
                    for item in painted_shapes
                    if item[0] < order
                    and contains_bounds((item[1], item[2], item[3], item[4]), geometry_box)
                ]
                background = max(containers, key=lambda item: item[0])[5] if containers else "#ffffff"
                if not visibly_painted(element, geometry_box, background):
                    raise ValueError("alignment annotations require visible nonzero geometry distinct from its background")
                if "data-align-left" in alignment_attributes:
                    append_group(left_groups, element.attrib["data-align-left"], left, label)
                if "data-align-right" in alignment_attributes:
                    append_group(right_groups, element.attrib["data-align-right"], right, label)
                if "data-align-center-x" in alignment_attributes:
                    append_group(center_x_groups, element.attrib["data-align-center-x"], (left + right) / 2, label)
                if "data-align-center-y" in alignment_attributes:
                    append_group(center_y_groups, element.attrib["data-align-center-y"], (top + bottom) / 2, label)
                if "data-align-bottom" in alignment_attributes:
                    append_group(bottom_groups, element.attrib["data-align-bottom"], bottom, label)
                if "data-align-baseline" in alignment_attributes:
                    if tag != "text":
                        raise ValueError("data-align-baseline is valid only on text elements")
                    append_group(baseline_groups, element.attrib["data-align-baseline"], number(element.attrib.get("y"), "text y"), label)
                if "data-equal-size" in alignment_attributes:
                    append_group(equal_size_groups, element.attrib["data-equal-size"], (right - left, bottom - top), label)
                if "data-balance-center-x" in alignment_attributes:
                    append_group(balance_x_groups, element.attrib["data-balance-center-x"], (left + right) / 2, label)
            except ValueError as exc:
                findings.append({"severity": "ERROR", "code": "ALIGNMENT_GEOMETRY", "message": f"{label}: {exc}"})

        if tag == "text":
            text_count += 1
            text_value = " ".join("".join(element.itertext()).split())
            compact_text = re.sub(r"[\W_]+", "", text_value, flags=re.UNICODE)
            if PLACEHOLDER.search(text_value) or PLACEHOLDER.search(compact_text):
                findings.append({"severity": "ERROR", "code": "PLACEHOLDER_TEXT", "message": text_value})
            if "/" in text_value and element.attrib.get("data-slash-ok") != "true":
                slash_text.append(text_value)
            try:
                for child in element:
                    child_tag = local(child.tag)
                    if child_tag != "tspan":
                        findings.append({"severity": "ERROR", "code": "TEXT_STRUCTURE_UNAUDITED", "message": f"unsupported {child_tag} inside text {text_value!r}"})
                        continue
                    forbidden_overrides = {"font-size", "fill", "font-family", "font-weight", "transform", "style"}.intersection(child.attrib)
                    if forbidden_overrides:
                        findings.append({"severity": "ERROR", "code": "TSPAN_STYLE_OVERRIDE", "message": f"split styled tspan into a separate audited text element: {sorted(forbidden_overrides)}"})
                    if list(child):
                        findings.append({"severity": "ERROR", "code": "NESTED_TSPAN", "message": f"nested text spans are not auditable in {text_value!r}"})
                size = number(element.attrib.get("font-size"), "text font-size")
                size_pt = size * unit_mm / POINT_MM
                minimum_seen = min(minimum_seen, size_pt)
                if size_pt + 1e-6 < minimum_text_pt:
                    findings.append({"severity": "ERROR", "code": "FONT_TOO_SMALL", "message": f"text {text_value!r} is {size_pt:.2f} pt; minimum is {minimum_text_pt:g} pt"})
                left, top, right, bottom = text_bounds(element, size)
                if left < min_x or top < min_y or right > min_x + width or bottom > min_y + height:
                    findings.append({"severity": "ERROR", "code": "TEXT_BOUNDS_OUTSIDE", "message": f"estimated bounds leave viewBox for {text_value!r}"})
                fill = color_value(element, "fill", "#000000")
                center_x, center_y = (left + right) / 2, (top + bottom) / 2
                text_box = (left, top, right, bottom)
                containers = [
                    item
                    for item in painted_shapes
                    if item[0] < order
                    and contains_bounds((item[1], item[2], item[3], item[4]), text_box)
                ]
                background = max(containers, key=lambda item: item[0])[5] if containers else "#ffffff"
                ratio = contrast_ratio(fill, background)
                if ratio is None:
                    findings.append({"severity": "ERROR", "code": "TEXT_COLOR_UNAUDITED", "message": f"use explicit six-digit hex text and background fills for {text_value!r}"})
                elif ratio + 1e-6 < 4.5:
                    findings.append({"severity": "ERROR", "code": "LOW_TEXT_CONTRAST", "message": f"text {text_value!r} has {ratio:.2f}:1 contrast against {background}"})
                occluders = [
                    item
                    for item in painted_shapes
                    if item[0] > order
                    and intersects_bounds((item[1], item[2], item[3], item[4]), text_box)
                ]
                if occluders:
                    findings.append({"severity": "ERROR", "code": "TEXT_COVERED", "message": f"a later filled shape overlaps text {text_value!r}"})
                stroke_collisions = []
                for segments, half_width, label in painted_strokes:
                    expanded_text_box = (
                        text_box[0] - half_width,
                        text_box[1] - half_width,
                        text_box[2] + half_width,
                        text_box[3] + half_width,
                    )
                    if any(segment_intersects_bounds(start, end, expanded_text_box) for start, end in segments):
                        stroke_collisions.append(label)
                if stroke_collisions:
                    findings.append({
                        "severity": "ERROR",
                        "code": "TEXT_STROKE_COLLISION",
                        "message": f"stroked line {stroke_collisions[0]!r} overlaps estimated bounds of text {text_value!r}",
                    })
            except ValueError as exc:
                findings.append({"severity": "ERROR", "code": "TEXT_METADATA", "message": f"{text_value!r}: {exc}"})

        is_connector = tag in {"line", "polyline", "path"} and (
            "marker-end" in element.attrib or element.attrib.get("data-connector") == "true"
        )
        if is_connector:
            connector_count += 1
            try:
                if tag == "path":
                    findings.append({"severity": "ERROR", "code": "PATH_CONNECTOR", "message": "use a line or a polyline with at most one elbow"})
                elif tag == "line":
                    points = [
                        (number(element.attrib.get("x1"), "line x1"), number(element.attrib.get("y1"), "line y1")),
                        (number(element.attrib.get("x2"), "line x2"), number(element.attrib.get("y2"), "line y2")),
                    ]
                else:
                    points = parse_points(element.attrib.get("points", ""))
                    if len(points) > 3:
                        findings.append({"severity": "ERROR", "code": "TOO_MANY_ELBOWS", "message": element.attrib.get("id", "polyline")})
                if tag != "path" and any(not in_view(x, y, view) for x, y in points):
                    findings.append({"severity": "ERROR", "code": "CONNECTOR_OUTSIDE", "message": element.attrib.get("id", tag)})
            except ValueError as exc:
                findings.append({"severity": "ERROR", "code": "CONNECTOR_GEOMETRY", "message": str(exc)})

        if tag == "rect":
            try:
                x = number(element.attrib.get("x", "0"), "rect x")
                y = number(element.attrib.get("y", "0"), "rect y")
                rect_width = number(element.attrib.get("width"), "rect width")
                rect_height = number(element.attrib.get("height"), "rect height")
                if x < min_x or y < min_y or x + rect_width > min_x + width or y + rect_height > min_y + height:
                    findings.append({"severity": "ERROR", "code": "RECT_OUTSIDE", "message": element.attrib.get("id", "rect")})
            except ValueError as exc:
                findings.append({"severity": "ERROR", "code": "RECT_GEOMETRY", "message": str(exc)})

    if slash_text:
        findings.append({"severity": "ERROR", "code": "SLASH_PROSE", "message": " | ".join(slash_text)})
    if text_count == 0:
        findings.append({"severity": "ERROR", "code": "NO_TEXT", "message": "SVG contains no editable text"})

    def check_scalar_groups(groups: dict[str, list[tuple[Any, str]]], code: str, label: str) -> None:
        for name, values in groups.items():
            if len(values) < 2:
                findings.append({"severity": "ERROR", "code": "ALIGNMENT_GROUP_TOO_SMALL", "message": f"{label} group {name!r} needs at least two elements"})
                continue
            numbers = [float(value) for value, _ in values]
            if max(numbers) - min(numbers) > ALIGNMENT_TOLERANCE:
                findings.append({"severity": "ERROR", "code": code, "message": f"{label} group {name!r} spans {min(numbers):g} to {max(numbers):g}"})

    check_scalar_groups(left_groups, "ALIGN_LEFT_MISMATCH", "left-edge")
    check_scalar_groups(right_groups, "ALIGN_RIGHT_MISMATCH", "right-edge")
    check_scalar_groups(center_x_groups, "ALIGN_CENTER_X_MISMATCH", "x-center")
    check_scalar_groups(center_y_groups, "ALIGN_CENTER_Y_MISMATCH", "y-center")
    check_scalar_groups(bottom_groups, "ALIGN_BOTTOM_MISMATCH", "bottom-edge")
    check_scalar_groups(baseline_groups, "ALIGN_BASELINE_MISMATCH", "text-baseline")

    for name, values in equal_size_groups.items():
        if len(values) < 2:
            findings.append({"severity": "ERROR", "code": "ALIGNMENT_GROUP_TOO_SMALL", "message": f"equal-size group {name!r} needs at least two elements"})
            continue
        widths = [float(value[0]) for value, _ in values]
        heights = [float(value[1]) for value, _ in values]
        if max(widths) - min(widths) > ALIGNMENT_TOLERANCE or max(heights) - min(heights) > ALIGNMENT_TOLERANCE:
            findings.append({"severity": "ERROR", "code": "EQUAL_SIZE_MISMATCH", "message": f"equal-size group {name!r} has inconsistent width or height"})

    for name, values in balance_x_groups.items():
        anchors = center_x_groups.get(name, [])
        if not anchors:
            findings.append({"severity": "ERROR", "code": "ALIGNMENT_GROUP_MISSING_CENTER", "message": f"balanced x-group {name!r} has no matching data-align-center-x anchor"})
            continue
        if len(values) < 2 or len(values) % 2:
            findings.append({"severity": "ERROR", "code": "BALANCE_CENTER_X_MISMATCH", "message": f"balanced x-group {name!r} requires an even number of at least two elements"})
            continue
        target = sum(float(value) for value, _ in anchors) / len(anchors)
        offsets = sorted(float(value) - target for value, _ in values)
        if any(abs(offsets[index] + offsets[-1 - index]) > ALIGNMENT_TOLERANCE for index in range(len(offsets) // 2)):
            findings.append({"severity": "ERROR", "code": "BALANCE_CENTER_X_MISMATCH", "message": f"balanced x-group {name!r} is not symmetric around {target:g}"})

    errors = sum(item["severity"] == "ERROR" for item in findings)
    warnings = sum(item["severity"] == "WARN" for item in findings)
    return {
        "schema_version": 1,
        "status": "PASS" if errors == 0 else "FAIL",
        "file": str(svg_path.resolve()),
        "master_sha256": sha256_file(svg_path),
        "placement_width_mm": placement_width_mm,
        "view_box": view,
        "text_count": text_count,
        "connector_count": connector_count,
        "alignment_group_count": len(set(left_groups) | set(right_groups) | set(center_x_groups) | set(center_y_groups) | set(bottom_groups) | set(baseline_groups) | set(equal_size_groups) | set(balance_x_groups)),
        "minimum_text_pt": None if math.isinf(minimum_seen) else round(minimum_seen, 3),
        "required_minimum_text_pt": minimum_text_pt,
        "error_count": errors,
        "warning_count": warnings,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--placement-width-mm", type=float, required=True)
    parser.add_argument("--minimum-text-pt", type=float, default=7.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.svg, args.placement_width_mm, args.minimum_text_pt)
    except (ET.ParseError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
