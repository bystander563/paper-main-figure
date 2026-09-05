#!/usr/bin/env python3
"""Audit story-bound scientific content retention for a main figure."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any


BEGIN = "<!-- FIGURE_CONTENT_CONTRACT_BEGIN -->"
END = "<!-- FIGURE_CONTENT_CONTRACT_END -->"
MODES = {"STORY_ONLY", "REFERENCE_FLOOR"}
DISPOSITIONS = {"VISIBLE", "CAPTION", "OPTIONAL_DROP"}
VISUAL_CARRIERS = {
    "VISUAL_OBJECT", "RELATION", "SHORT_LABEL", "CAPTION", "OPTIONAL_DROP"
}
SCHEMATIC_ROUTES = {
    "SCHEMATIC_OVERVIEW", "SYSTEM_PIPELINE", "LAYERED_ARCHITECTURE", "FORMULA_CORE"
}
INPUT_GRANULARITIES = {"document", "sentence", "token", "span", "batch", "state"}
GRAPHIC_TAGS = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "image", "use"}
RELATION_TAGS = {"line", "polyline", "polygon", "path"}
FORMULA_SIGNAL = re.compile(
    r"(?:"
    r"[=≤≥≠≈∑∏∫√]"
    r"|(?<!\w)\d+\s*/\s*[A-Za-zΑ-ω][A-Za-z0-9₀-₉ᵢⱼₖₗₘₙₚᵣₛₜᵤᵥₓ⁰-⁹⁺⁻⁼]*"
    r"|\b[A-Za-zΑ-ω][A-Za-z0-9]*_[A-Za-z0-9]+\b"
    r"|\b[A-Za-zΑ-ω][₀-₉ᵢⱼₖₗₘₙₚᵣₛₜᵤᵥₓ⁰-⁹⁺⁻⁼]+"
    r"|(?<!\w)[A-Za-z](?:_[A-Za-z0-9]+)?\s*\([^)]*\)"
    r")"
)
DISPLAY_EQUATION = re.compile(r"[=≤≥≠≈∑∏∫√]|(?<!\w)\d+\s*/\s*[A-Za-zΑ-ω]")


class ContentRetentionError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_text(value: str) -> str:
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE).casefold()


def reference_key(value: str) -> str:
    normalized = canonical_text(value)
    if normalized:
        return normalized
    symbol = " ".join(value.split())
    return f"symbol:{symbol}" if symbol else ""


def text_content(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def extract_contract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ContentRetentionError(
            "MAIN_FIGURE_CONTRACT.md requires exactly one bounded FIGURE_CONTENT_CONTRACT block"
        )
    payload = text.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    if payload.startswith("```json") and payload.endswith("```"):
        payload = payload[len("```json") : -len("```")].strip()
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ContentRetentionError(f"figure content contract is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContentRetentionError("figure content contract must be a JSON object")
    return value


def string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ContentRetentionError(f"{label} must be a list")
    if not allow_empty and not value:
        raise ContentRetentionError(f"{label} must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContentRetentionError(f"{label} must contain non-empty strings")
    return value


def resolve_reference(contract_path: Path, value: Any) -> tuple[Path, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise ContentRetentionError("REFERENCE_FLOOR requires reference path and sha256")
    raw = value["path"]
    expected = value["sha256"]
    if not isinstance(raw, str) or not raw.strip():
        raise ContentRetentionError("reference path must be a non-empty string")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ContentRetentionError("reference sha256 must be 64 lowercase hex characters")
    path = Path(raw)
    if not path.is_absolute():
        path = contract_path.parent / path
    path = path.resolve()
    if not path.is_file():
        raise ContentRetentionError(f"reference baseline is missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ContentRetentionError(
            f"reference baseline hash mismatch: recorded {expected}, actual {actual}"
        )
    return path, actual


def svg_tree(path: Path) -> tuple[ET.Element, dict[str, ET.Element], str, list[str]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ContentRetentionError(f"SVG is invalid XML: {path}: {exc}") from exc
    if local_name(root.tag) != "svg":
        raise ContentRetentionError(f"content audit expects an SVG: {path}")
    by_id: dict[str, ET.Element] = {}
    visible_text: list[str] = []
    for element in root.iter():
        identifier = element.attrib.get("id")
        if identifier:
            if identifier in by_id:
                raise ContentRetentionError(f"duplicate SVG id in content audit: {identifier}")
            by_id[identifier] = element
        if local_name(element.tag) == "text" and text_content(element):
            visible_text.append(text_content(element))
    return root, by_id, canonical_text(" ".join(visible_text)), visible_text


def reference_text_inventory(values: list[str]) -> tuple[dict[str, str], Counter[str]]:
    """Return canonical representatives and the full visible-text multiset."""
    inventory: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for value in values:
        normalized = reference_key(value)
        if normalized:
            inventory.setdefault(normalized, value)
            counts[normalized] += 1
    return inventory, counts


def element_text_inventory(elements: list[ET.Element]) -> set[str]:
    values: set[str] = set()
    for element in elements:
        for descendant in element.iter():
            if local_name(descendant.tag) == "text":
                normalized = reference_key(text_content(descendant))
                if normalized:
                    values.add(normalized)
    return values


def is_visibly_painted(element: ET.Element) -> bool:
    style = element.attrib.get("style", "").replace(" ", "").casefold()
    if element.attrib.get("display", "").casefold() == "none" or "display:none" in style:
        return False
    if element.attrib.get("visibility", "").casefold() == "hidden" or "visibility:hidden" in style:
        return False
    opacity = element.attrib.get("opacity")
    if opacity is not None:
        try:
            if float(opacity) <= 0:
                return False
        except ValueError:
            pass
    fill = element.attrib.get("fill", "").replace(" ", "").casefold()
    stroke = element.attrib.get("stroke", "").replace(" ", "").casefold()
    if fill in {"none", "transparent"} and stroke in {"none", "transparent"}:
        return False
    return True


def structural_profile(elements: list[ET.Element]) -> dict[str, Any]:
    primitive_count = 0
    rich_primitive = False
    relation_count = 0
    for element in elements:
        for descendant in element.iter():
            tag = local_name(descendant.tag)
            if tag not in GRAPHIC_TAGS or not is_visibly_painted(descendant):
                continue
            primitive_count += 1
            if tag in {"image", "use"}:
                rich_primitive = True
            if tag == "path" and len(re.findall(r"[A-Za-z]", descendant.attrib.get("d", ""))) >= 4:
                rich_primitive = True
            if tag in RELATION_TAGS:
                relation_count += 1
    return {
        "primitive_count": primitive_count,
        "rich_primitive": rich_primitive,
        "relation_count": relation_count,
    }


def formula_like_text(value: str) -> bool:
    """Recognize displayed mathematical notation, including Unicode scripts."""
    return bool(FORMULA_SIGNAL.search(" ".join(value.split())))


def validate_visual_grammar(
    visual_grammar: Any,
    normalized_units: list[dict[str, Any]],
    carrier_by_id: dict[str, str],
    components: list[dict[str, Any]],
    registered_ids: set[str],
    by_id: dict[str, ET.Element],
    svg_root: ET.Element,
    source_text: str,
) -> dict[str, Any]:
    fields = {"route", "formula_budget", "input_bindings", "macro_regions"}
    if not isinstance(visual_grammar, dict) or set(visual_grammar) != fields:
        raise ContentRetentionError(
            f"schema_version 2 visual_grammar fields must be exactly {sorted(fields)}"
        )
    route = visual_grammar.get("route")
    if route not in SCHEMATIC_ROUTES:
        raise ContentRetentionError(f"unknown schematic route: {route}")
    formula_budget = visual_grammar.get("formula_budget")
    if not isinstance(formula_budget, int) or isinstance(formula_budget, bool) or formula_budget < 0:
        raise ContentRetentionError("visual_grammar.formula_budget must be a non-negative integer")
    if route != "FORMULA_CORE" and formula_budget > 1:
        raise ContentRetentionError(
            f"{route} permits a near-zero formula budget of at most one"
        )
    if route == "FORMULA_CORE" and formula_budget < 1:
        raise ContentRetentionError("FORMULA_CORE requires a positive formula budget")

    component_kinds = {
        str(item.get("id")): str(item.get("kind", "")).casefold()
        for item in components
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    notation_components = [
        identifier for identifier, kind in component_kinds.items()
        if kind in {"formula", "symbol"}
    ]
    formula_components = [identifier for identifier in notation_components if component_kinds[identifier] == "formula"]
    component_descendants = {
        identifier: {id(item) for item in by_id[identifier].iter()}
        for identifier in registered_ids if identifier in by_id
    }
    formula_texts: list[str] = []
    for element in svg_root.iter():
        if local_name(element.tag) != "text" or not is_visibly_painted(element):
            continue
        token = text_content(element)
        if not formula_like_text(token):
            continue
        if DISPLAY_EQUATION.search(token):
            formula_texts.append(token)
        typed_owners = [
            identifier for identifier in notation_components
            if id(element) in component_descendants.get(identifier, set())
        ]
        if not typed_owners:
            raise ContentRetentionError(
                "visible formula-like text must be registered as a formula or symbol component: "
                f"{token}"
            )
        if DISPLAY_EQUATION.search(token) and not any(component_kinds[k] == "formula" for k in typed_owners):
            raise ContentRetentionError("A displayed equation must be registered as formula, not as a symbol label")
    if len(formula_components) > formula_budget:
        raise ContentRetentionError(
            "registered formula and symbol components exceed the frozen overview budget: "
            f"actual={len(formula_components)}, budget={formula_budget}"
        )
    if formula_texts and formula_budget == 0:
        raise ContentRetentionError(
            "visible formula-like text exceeds the zero formula budget: "
            + ", ".join(formula_texts[:4])
        )

    input_bindings = visual_grammar.get("input_bindings")
    if not isinstance(input_bindings, list):
        raise ContentRetentionError("visual_grammar.input_bindings must be a list")
    component_records = {
        str(item.get("id")): item for item in components
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    visible_component_ids = {
        component_id
        for unit in normalized_units if unit["disposition"] == "VISIBLE"
        for component_id in unit.get("svg_components", [])
    }
    seen_bindings: set[str] = set()
    normalized_bindings: list[dict[str, str | None]] = []
    for index, binding in enumerate(input_bindings):
        label = f"visual_grammar.input_bindings[{index}]"
        binding_fields = {
            "id", "model_component", "input_component", "context_component",
            "granularity", "source_anchor", "connector_component",
        }
        if not isinstance(binding, dict) or set(binding) != binding_fields:
            raise ContentRetentionError(f"{label} fields must be exactly {sorted(binding_fields)}")
        identifier = binding.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", identifier):
            raise ContentRetentionError(f"{label} has an invalid id")
        if identifier in seen_bindings:
            raise ContentRetentionError(f"duplicate input binding id: {identifier}")
        seen_bindings.add(identifier)
        granularity = binding.get("granularity")
        if granularity not in INPUT_GRANULARITIES:
            raise ContentRetentionError(f"{identifier} has an invalid input granularity")
        source_anchor = binding.get("source_anchor")
        if not isinstance(source_anchor, str) or canonical_text(source_anchor) not in source_text:
            raise ContentRetentionError(f"{identifier} input source_anchor is absent from story and facts")
        if canonical_text(str(granularity)) not in canonical_text(source_anchor):
            raise ContentRetentionError(
                f"{identifier} source_anchor does not name its {granularity} granularity"
            )
        for field in ("model_component", "input_component", "connector_component"):
            component_id = binding.get(field)
            if not isinstance(component_id, str) or component_id not in registered_ids or component_id not in by_id:
                raise ContentRetentionError(f"{identifier} names an invalid {field}: {component_id}")
        context_component = binding.get("context_component")
        if context_component is not None and (
            not isinstance(context_component, str)
            or context_component not in registered_ids
            or context_component not in by_id
        ):
            raise ContentRetentionError(f"{identifier} names an invalid context_component")
        input_component = str(binding["input_component"])
        input_role = str(component_records[input_component].get("semantic_role", ""))
        if canonical_text(str(granularity)) not in canonical_text(input_role):
            raise ContentRetentionError(
                f"{identifier} input component does not preserve {granularity} granularity"
            )
        connector_component = str(binding["connector_component"])
        if str(component_records[connector_component].get("kind", "")).casefold() != "connector":
            raise ContentRetentionError(f"{identifier} connector_component is not a connector")
        if input_component not in visible_component_ids:
            raise ContentRetentionError(
                f"{identifier} input component is absent from visible content units"
            )
        normalized_bindings.append(
            {
                "id": identifier,
                "granularity": str(granularity),
                "input_component": input_component,
                "context_component": str(context_component) if context_component is not None else None,
                "model_component": str(binding["model_component"]),
                "connector_component": connector_component,
            }
        )

    regions = visual_grammar.get("macro_regions")
    if not isinstance(regions, list) or not regions:
        raise ContentRetentionError("visual_grammar requires at least one macro region")
    visible_ids = {
        item["id"] for item in normalized_units if item["disposition"] == "VISIBLE"
    }
    claimed_units: set[str] = set()
    seen_regions: set[str] = set()
    normalized_regions: list[dict[str, Any]] = []
    for index, region in enumerate(regions):
        label = f"visual_grammar.macro_regions[{index}]"
        region_fields = {"id", "role", "unit_ids", "skeleton_components"}
        if not isinstance(region, dict) or set(region) != region_fields:
            raise ContentRetentionError(f"{label} fields must be exactly {sorted(region_fields)}")
        identifier = region.get("id")
        role = region.get("role")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", identifier):
            raise ContentRetentionError(f"{label} has an invalid id")
        if identifier in seen_regions:
            raise ContentRetentionError(f"duplicate macro region id: {identifier}")
        seen_regions.add(identifier)
        if not isinstance(role, str) or len(role.strip()) < 12:
            raise ContentRetentionError(f"{identifier} requires a substantive scientific role")
        unit_ids = string_list(region.get("unit_ids"), f"{identifier}.unit_ids")
        skeleton_ids = string_list(
            region.get("skeleton_components"), f"{identifier}.skeleton_components"
        )
        if len(set(unit_ids)) != len(unit_ids):
            raise ContentRetentionError(f"{identifier}.unit_ids contains duplicates")
        for unit_id in unit_ids:
            if unit_id not in visible_ids:
                raise ContentRetentionError(
                    f"{identifier} names a missing or non-visible content unit: {unit_id}"
                )
            if unit_id in claimed_units:
                raise ContentRetentionError(f"visible content unit appears in two macro regions: {unit_id}")
            claimed_units.add(unit_id)
        if not any(carrier_by_id[unit_id] in {"VISUAL_OBJECT", "RELATION"} for unit_id in unit_ids):
            raise ContentRetentionError(
                f"{identifier} is text-only; every macro region needs a visual object or relation"
            )
        profiles = []
        for component_id in skeleton_ids:
            if component_id not in registered_ids or component_id not in by_id:
                raise ContentRetentionError(
                    f"{identifier} skeleton component is not registered and visible: {component_id}"
                )
            profile = structural_profile([by_id[component_id]])
            if profile["primitive_count"] < 2 and not profile["rich_primitive"]:
                raise ContentRetentionError(
                    f"{identifier} wordless skeleton is only a text card: {component_id}"
                )
            profiles.append({"id": component_id, **profile})
        normalized_regions.append(
            {
                "id": identifier,
                "unit_count": len(unit_ids),
                "skeleton_components": profiles,
            }
        )
    missing_visible = sorted(visible_ids - claimed_units)
    if missing_visible:
        raise ContentRetentionError(
            f"visible content units are absent from the macro-region map: {missing_visible}"
        )
    return {
        "route": route,
        "formula_budget": formula_budget,
        "formula_component_count": len(formula_components),
        "formula_text_count": len(formula_texts),
        "input_bindings": normalized_bindings,
        "macro_regions": normalized_regions,
    }


def audit_content_retention(
    contract_path: Path,
    story_path: Path,
    facts_path: Path,
    caption_path: Path,
    audit_svg_path: Path,
    layout_spec_path: Path,
) -> dict[str, Any]:
    contract = extract_contract(contract_path)
    contract_schema = contract.get("schema_version")
    if contract_schema == 1:
        required = {"schema_version", "mode", "reference", "reference_omissions", "units"}
    elif contract_schema == 2:
        required = {
            "schema_version", "mode", "reference", "reference_omissions", "units",
            "visual_grammar",
        }
    else:
        raise ContentRetentionError("figure content contract requires schema_version 1 or 2")
    if set(contract) != required:
        raise ContentRetentionError(
            f"figure content contract fields must be exactly {sorted(required)}"
        )
    mode = contract.get("mode")
    if mode not in MODES:
        raise ContentRetentionError(f"unknown content-retention mode: {mode}")

    reference_path: Path | None = None
    reference_hash: str | None = None
    reference_inventory: dict[str, str] = {}
    reference_inventory_counts: Counter[str] = Counter()
    reference_inventory_verifiable = False
    if mode == "REFERENCE_FLOOR":
        reference_path, reference_hash = resolve_reference(contract_path, contract.get("reference"))
        if reference_path.suffix.casefold() == ".svg":
            _, _, _, reference_nodes = svg_tree(reference_path)
            reference_inventory, reference_inventory_counts = reference_text_inventory(reference_nodes)
            reference_inventory_verifiable = True
    elif contract.get("reference") is not None:
        raise ContentRetentionError("STORY_ONLY requires reference: null")

    omissions = contract.get("reference_omissions")
    if not isinstance(omissions, list):
        raise ContentRetentionError("reference_omissions must be a list")
    if mode == "STORY_ONLY" and omissions:
        raise ContentRetentionError("STORY_ONLY requires reference_omissions: []")

    units = contract.get("units")
    if not isinstance(units, list) or not units:
        raise ContentRetentionError("figure content contract requires at least one content unit")
    layout = json.loads(layout_spec_path.read_text(encoding="utf-8"))
    components = layout.get("components")
    if not isinstance(components, list):
        raise ContentRetentionError("layout spec has no valid components list")
    registered_ids = {
        item.get("id") for item in components
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    svg_root, by_id, svg_text, _ = svg_tree(audit_svg_path)
    caption_text = canonical_text(caption_path.read_text(encoding="utf-8"))
    source_text = canonical_text(
        story_path.read_text(encoding="utf-8") + "\n" + facts_path.read_text(encoding="utf-8")
    )

    seen: set[str] = set()
    counts = {"VISIBLE": 0, "CAPTION": 0, "OPTIONAL_DROP": 0}
    reference_present_count = 0
    claimed_reference: Counter[str] = Counter()
    normalized_units: list[dict[str, Any]] = []
    carrier_by_id: dict[str, str] = {}
    legacy_fields = {
        "id", "region", "disposition", "source_anchor", "required_tokens",
        "svg_components", "reference_present", "reference_tokens",
        "reference_rewrites", "rationale",
    }
    fields = legacy_fields | ({"visual_carrier"} if contract_schema == 2 else set())
    for index, unit in enumerate(units):
        label = f"content unit {index}"
        if not isinstance(unit, dict) or set(unit) != fields:
            raise ContentRetentionError(f"{label} fields must be exactly {sorted(fields)}")
        identifier = unit.get("id")
        region = unit.get("region")
        disposition = unit.get("disposition")
        visual_carrier = (
            unit.get("visual_carrier")
            if contract_schema == 2
            else {
                "VISIBLE": "SHORT_LABEL", "CAPTION": "CAPTION", "OPTIONAL_DROP": "OPTIONAL_DROP"
            }.get(disposition)
        )
        source_anchor = unit.get("source_anchor")
        rationale = unit.get("rationale")
        reference_present = unit.get("reference_present")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", identifier):
            raise ContentRetentionError(f"{label} has an invalid id")
        if identifier in seen:
            raise ContentRetentionError(f"duplicate content unit id: {identifier}")
        seen.add(identifier)
        if not isinstance(region, str) or not region.strip():
            raise ContentRetentionError(f"{identifier} requires a non-empty region")
        if disposition not in DISPOSITIONS:
            raise ContentRetentionError(f"{identifier} has an invalid disposition")
        if visual_carrier not in VISUAL_CARRIERS:
            raise ContentRetentionError(f"{identifier} has an invalid visual_carrier")
        expected_carriers = {
            "VISIBLE": {"VISUAL_OBJECT", "RELATION", "SHORT_LABEL"},
            "CAPTION": {"CAPTION"},
            "OPTIONAL_DROP": {"OPTIONAL_DROP"},
        }
        if visual_carrier not in expected_carriers[disposition]:
            raise ContentRetentionError(
                f"{identifier} visual_carrier {visual_carrier} conflicts with {disposition}"
            )
        carrier_by_id[identifier] = visual_carrier
        if not isinstance(source_anchor, str) or not source_anchor.strip():
            raise ContentRetentionError(f"{identifier} requires a source_anchor")
        if canonical_text(source_anchor) not in source_text:
            raise ContentRetentionError(f"{identifier} source_anchor is absent from story and facts")
        if not isinstance(reference_present, bool):
            raise ContentRetentionError(f"{identifier} reference_present must be boolean")
        if not isinstance(rationale, str):
            raise ContentRetentionError(f"{identifier} rationale must be a string")

        tokens = string_list(
            unit.get("required_tokens"), f"{identifier}.required_tokens",
            allow_empty=disposition == "OPTIONAL_DROP",
        )
        svg_components = string_list(
            unit.get("svg_components"), f"{identifier}.svg_components",
            allow_empty=disposition != "VISIBLE",
        )
        reference_tokens = string_list(
            unit.get("reference_tokens"), f"{identifier}.reference_tokens", allow_empty=True,
        )
        rewrites = unit.get("reference_rewrites")
        if not isinstance(rewrites, list):
            raise ContentRetentionError(f"{identifier}.reference_rewrites must be a list")
        if mode == "STORY_ONLY" and (reference_present or reference_tokens or rewrites):
            raise ContentRetentionError(
                f"{identifier} cannot claim reference content in STORY_ONLY mode"
            )
        if reference_present != bool(reference_tokens):
            raise ContentRetentionError(
                f"{identifier}.reference_present must equal whether reference_tokens is non-empty"
            )
        if reference_present:
            reference_present_count += 1

        rewrite_map: dict[str, str] = {}
        for rewrite_index, rewrite in enumerate(rewrites):
            rewrite_label = f"{identifier}.reference_rewrites[{rewrite_index}]"
            if not isinstance(rewrite, dict) or set(rewrite) != {
                "reference_text", "destination_token", "rationale"
            }:
                raise ContentRetentionError(
                    f"{rewrite_label} fields must be reference_text, destination_token, rationale"
                )
            reference_key_value = reference_key(rewrite.get("reference_text", ""))
            destination_key = canonical_text(rewrite.get("destination_token", ""))
            rewrite_reason = rewrite.get("rationale")
            if not reference_key_value or not destination_key:
                raise ContentRetentionError(f"{rewrite_label} requires non-empty text fields")
            if reference_key_value in rewrite_map:
                raise ContentRetentionError(
                    f"{identifier} has duplicate rewrite for {rewrite['reference_text']}"
                )
            if destination_key not in {canonical_text(token) for token in tokens}:
                raise ContentRetentionError(
                    f"{rewrite_label} destination_token must name a required_token"
                )
            if not isinstance(rewrite_reason, str) or len(rewrite_reason.strip()) < 20:
                raise ContentRetentionError(f"{rewrite_label} requires a substantive rationale")
            rewrite_map[reference_key_value] = destination_key
        if disposition == "VISIBLE":
            for component_id in svg_components:
                if component_id not in registered_ids:
                    raise ContentRetentionError(
                        f"{identifier} uses unregistered layout component {component_id}"
                    )
                if component_id not in by_id:
                    raise ContentRetentionError(
                        f"{identifier} component is absent from audit SVG: {component_id}"
                    )
            component_text = canonical_text(
                " ".join(text_content(by_id[component_id]) for component_id in svg_components)
            )
            component_text_nodes = element_text_inventory(
                [by_id[component_id] for component_id in svg_components]
            )
            if contract_schema == 2:
                profile = structural_profile([by_id[component_id] for component_id in svg_components])
                if (
                    visual_carrier == "VISUAL_OBJECT"
                    and profile["primitive_count"] < 2
                    and not profile["rich_primitive"]
                ):
                    raise ContentRetentionError(
                        f"{identifier} declares VISUAL_OBJECT but contains only a text-card shell"
                    )
                if visual_carrier == "RELATION" and profile["relation_count"] == 0:
                    raise ContentRetentionError(
                        f"{identifier} declares RELATION but contains no connector geometry"
                    )
            for token in tokens:
                normalized = canonical_text(token)
                if normalized not in svg_text or normalized not in component_text:
                    raise ContentRetentionError(
                        f"{identifier} required visible token is missing from its components: {token}"
                    )
        elif disposition == "CAPTION":
            component_text = ""
            component_text_nodes = set()
            if svg_components:
                raise ContentRetentionError(f"{identifier} CAPTION unit must not name SVG components")
            for token in tokens:
                if canonical_text(token) not in caption_text:
                    raise ContentRetentionError(
                        f"{identifier} required caption token is missing: {token}"
                    )
        else:
            component_text = ""
            component_text_nodes = set()
            if svg_components:
                raise ContentRetentionError(f"{identifier} OPTIONAL_DROP must not name SVG components")
            if rewrites:
                raise ContentRetentionError(f"{identifier} OPTIONAL_DROP must not define rewrites")
            if len(rationale.strip()) < 20:
                raise ContentRetentionError(
                    f"{identifier} OPTIONAL_DROP requires a substantive rationale"
                )

        destination_text = component_text if disposition == "VISIBLE" else caption_text
        declared_reference_keys = {reference_key(token) for token in reference_tokens}
        if set(rewrite_map) - declared_reference_keys:
            raise ContentRetentionError(
                f"{identifier} rewrites text not listed in reference_tokens"
            )
        for token in reference_tokens:
            normalized = reference_key(token)
            if not normalized:
                raise ContentRetentionError(f"{identifier} has an empty canonical reference token")
            claimed_reference[normalized] += 1
            if (
                reference_inventory_verifiable
                and claimed_reference[normalized] > reference_inventory_counts[normalized]
            ):
                raise ContentRetentionError(f"reference text is over-claimed: {token}")
            if reference_inventory_verifiable and normalized not in reference_inventory:
                raise ContentRetentionError(
                    f"{identifier} reference token is absent from reference SVG: {token}"
                )
            if disposition != "OPTIONAL_DROP":
                direct = (
                    normalized in component_text_nodes
                    if disposition == "VISIBLE"
                    else normalized in destination_text
                )
                rewritten = normalized in rewrite_map and rewrite_map[normalized] in destination_text
                if not direct and not rewritten:
                    raise ContentRetentionError(
                        f"{identifier} reference token has no visible destination or explicit rewrite: {token}"
                    )
        counts[disposition] += 1
        normalized_units.append(
            {
                "id": identifier,
                "region": region,
                "disposition": disposition,
                "visual_carrier": visual_carrier,
                "reference_present": reference_present,
                "reference_token_count": len(reference_tokens),
                "reference_rewrite_count": len(rewrites),
                "svg_components": svg_components,
            }
        )

    normalized_omissions: list[dict[str, str]] = []
    for index, omission in enumerate(omissions):
        label = f"reference_omissions[{index}]"
        if not isinstance(omission, dict) or set(omission) != {"reference_text", "rationale"}:
            raise ContentRetentionError(
                f"{label} fields must be exactly reference_text and rationale"
            )
        reference_value = omission.get("reference_text")
        reason = omission.get("rationale")
        if not isinstance(reference_value, str) or not reference_key(reference_value):
            raise ContentRetentionError(f"{label}.reference_text must be non-empty")
        if not isinstance(reason, str) or len(reason.strip()) < 20:
            raise ContentRetentionError(f"{label} requires a substantive rationale")
        normalized = reference_key(reference_value)
        if reference_inventory_verifiable and normalized not in reference_inventory:
            raise ContentRetentionError(
                f"omitted reference text is absent from reference SVG: {reference_value}"
            )
        claimed_reference[normalized] += 1
        if (
            reference_inventory_verifiable
            and claimed_reference[normalized] > reference_inventory_counts[normalized]
        ):
            raise ContentRetentionError(f"reference text is over-dispositioned: {reference_value}")
        normalized_omissions.append({"reference_text": reference_value, "rationale": reason})

    if mode == "REFERENCE_FLOOR" and reference_present_count == 0:
        raise ContentRetentionError("REFERENCE_FLOOR requires at least one reference-present unit")
    if mode == "REFERENCE_FLOOR" and reference_inventory_verifiable:
        missing_counts = reference_inventory_counts - claimed_reference
        extra_counts = claimed_reference - reference_inventory_counts
        missing = sorted(missing_counts)
        extra = sorted(extra_counts)
        if missing or extra:
            missing_text = [
                f"{reference_inventory[key]} x{missing_counts[key]}" for key in missing[:8]
            ]
            raise ContentRetentionError(
                "reference inventory is incomplete or inconsistent; "
                f"missing={missing_text}, extra={[(key, extra_counts[key]) for key in extra[:8]]}"
            )
    if counts["VISIBLE"] == 0:
        raise ContentRetentionError("at least one content unit must remain visible")

    normalized_visual_grammar = None
    if contract_schema == 2:
        normalized_visual_grammar = validate_visual_grammar(
            contract.get("visual_grammar"), normalized_units, carrier_by_id,
            components, registered_ids, by_id, svg_root, source_text,
        )

    return {
        "schema_version": 1,
        "status": "PASS",
        "contract_schema_version": contract_schema,
        "mode": mode,
        "reference": (
            {"path": str(reference_path), "sha256": reference_hash}
            if reference_path is not None else None
        ),
        "counts": counts,
        "reference_present_count": reference_present_count,
        "reference_inventory": {
            "verifiable": reference_inventory_verifiable,
            "reference_text_count": sum(reference_inventory_counts.values()),
            "unique_reference_text_count": len(reference_inventory_counts),
            "dispositioned_text_count": sum(claimed_reference.values()),
            "omission_count": len(normalized_omissions),
        },
        "units": normalized_units,
        "visual_grammar": normalized_visual_grammar,
    }
