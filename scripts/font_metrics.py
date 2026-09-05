"""Font-backed SVG text metrics. Never estimate width from character count.

Latin and CJK fonts must be explicitly available; missing glyphs or unsupported
SVG text placement fail rather than silently substituting a different face.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import ImageFont
from fontTools.ttLib import TTFont


@lru_cache(maxsize=64)
def font_path(family: str = "Arial", weight: str = "400", italic: bool = False) -> Path:
    name = family.split(",")[0].strip(" \"'")
    bold = str(weight) in {"bold", "600", "700", "800", "900"}
    filenames = {
        "arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
        "times new roman": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
        "calibri": ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
        "microsoft yahei": ("msyh.ttc", "msyhbd.ttc", "msyh.ttc", "msyhbd.ttc"),
    }
    if os.name == "nt" and name.casefold() in filenames:
        path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / filenames[name.casefold()][int(bold) + 2*int(italic)]
        if path.is_file():
            return path
    command = shutil.which("fc-match")
    if command:
        query = f"{name}:style={'Bold' if bold else 'Regular'}{' Italic' if italic else ''}"
        run = subprocess.run([command, "-f", "%{family}\n%{file}", query], check=True, capture_output=True, text=True)
        lines = run.stdout.splitlines()
        if len(lines) >= 2 and name.casefold() in {v.strip().casefold() for v in lines[0].split(",")}:
            path = Path(lines[1])
            if path.is_file():
                return path
    raise ValueError(f"Exact font unavailable: {name}, weight={weight}, italic={italic}; install it or explicitly choose another family")


@lru_cache(maxsize=64)
def fingerprint(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=64)
def glyphs(path: str) -> frozenset[int]:
    face = TTFont(path, fontNumber=0)
    try:
        return frozenset((face.getBestCmap() or {}).keys())
    finally:
        face.close()


@lru_cache(maxsize=256)
def face(path: str, size: float):
    if not math.isfinite(size) or size <= 0:
        raise ValueError("Font size must be positive and finite")
    return ImageFont.truetype(path, max(1, round(size*4)), index=0)


def measure(text: str, size: float, family: str = "Arial", weight: str = "400", italic: bool = False):
    path = str(font_path(family, weight, italic))
    missing = sorted({ord(c) for c in text if not c.isspace()} - glyphs(path))
    if missing:
        raise ValueError(f"Font {family} is missing glyphs: {', '.join(f'U+{v:04X}' for v in missing)}")
    font = face(path, size)
    scale = font.size / size
    box = tuple(float(v)/scale for v in font.getbbox(text, anchor="ls"))
    return box, float(font.getlength(text))/scale


def _num(value: str) -> float:
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", value.strip()):
        raise ValueError(f"Text coordinate must be a plain number: {value!r}")
    return float(value)


def text_bounds(element: ET.Element, size: float):
    style = dict(part.strip().split(":",1) for part in element.get("style", "").split(";") if ":" in part)
    def attr(key, default):
        return element.get(key, style.get(key, default))
    unsupported = {"textLength", "lengthAdjust", "rotate", "letter-spacing", "word-spacing", "writing-mode", "baseline-shift"}
    if unsupported.intersection(set(element.attrib) | set(style)):
        raise ValueError("Expand unsupported SVG text spacing/rotation into explicit measured text runs")
    if attr("dominant-baseline", "alphabetic") not in {"auto", "alphabetic"}:
        raise ValueError("Use explicit alphabetic baselines for measured text")
    family, weight = attr("font-family", "Arial"), attr("font-weight", "400")
    italic = attr("font-style", "normal") == "italic"
    path = str(font_path(family, weight, italic))
    expected = element.get("data-font-sha256")
    if expected and expected != fingerprint(path):
        raise ValueError("Font fingerprint differs from the generating face")
    x, y = _num(attr("x", "0")), _num(attr("y", "0"))
    chunks = list(element)
    boxes = []
    if chunks:
        if (element.text or "").strip() or any((c.tail or "").strip() for c in chunks):
            raise ValueError("Mixed inline text must be expanded into independently measured runs")
        for child in chunks:
            if child.tag.rsplit("}",1)[-1] != "tspan" or list(child):
                raise ValueError("Only flat explicit-line tspans are supported")
            if any(k in child.attrib for k in ("font-family", "font-size", "font-weight", "font-style", "dx")):
                raise ValueError("Mixed-font tspans must be separate text components")
            x = _num(child.get("x", str(x)))
            y = _num(child.get("y", str(y))) + _num(child.get("dy", "0"))
            boxes.append(_run_bounds(child.text or "", x, y, size, family, weight, italic, attr("text-anchor", "start")))
    else:
        boxes.append(_run_bounds(element.text or "", x, y, size, family, weight, italic, attr("text-anchor", "start")))
    return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)


def _run_bounds(text, x, y, size, family, weight, italic, anchor):
    box, advance = measure(text, size, family, weight, italic)
    if anchor not in {"start", "middle", "end"}:
        raise ValueError(f"Unsupported text-anchor {anchor}")
    offset = {"start": 0, "middle": -advance/2, "end": -advance}[anchor]
    return x+offset+box[0], y+box[1], x+offset+box[2], y+box[3]
