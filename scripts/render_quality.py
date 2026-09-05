"""Independent SVG/PDF rendering with component-local comparison."""
from __future__ import annotations
import io
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def render(path: Path, width=1800):
    if path.suffix.casefold()==".svg":
        executable=shutil.which("rsvg-convert")
        if not executable:
            raise ValueError("Independent SVG renderer rsvg-convert is required; no silent same-engine fallback")
        root=ET.parse(path).getroot()
        _,_,vw,vh=map(float,root.attrib["viewBox"].split())
        height=round(width*vh/vw)
        result=subprocess.run([executable,"--width",str(width),"--height",str(height),str(path)],check=True,capture_output=True)
        image=Image.open(io.BytesIO(result.stdout)).convert("RGBA")
        background=Image.new("RGBA",image.size,"white")
        return Image.alpha_composite(background,image).convert("RGB")
    import pymupdf
    with pymupdf.open(path) as document:
        if len(document)!=1: raise ValueError("Figure export must have one page")
        page=document[0]
        pix=page.get_pixmap(matrix=pymupdf.Matrix(width/page.rect.width,width/page.rect.width),alpha=False)
        return Image.frombytes("RGB",(pix.width,pix.height),pix.samples)


def compare(svg_path: Path, export_path: Path):
    from svg_layout_audit import geometry_bounds, local
    first,second=render(svg_path),render(export_path)
    if abs(first.width/first.height-second.width/second.height)>.002:
        raise ValueError("Independent render aspect mismatch")
    second=second.resize(first.size,Image.Resampling.LANCZOS)
    difference=ImageChops.difference(first,second)
    global_rms=sum(ImageStat.Stat(difference).rms)/(3*255)
    root=ET.parse(svg_path).getroot()
    vx,vy,vw,vh=map(float,root.attrib["viewBox"].split())
    failures=[]
    checked=0
    for el in root.iter():
        if local(el.tag) not in {"rect","polygon","circle","ellipse","text","line","polyline","path"}: continue
        x1,y1,x2,y2=geometry_bounds(el)
        sx,sy=first.width/vw,first.height/vh
        crop=(max(0,int((x1-vx)*sx)-3),max(0,int((y1-vy)*sy)-3),min(first.width,int((x2-vx)*sx)+4),min(first.height,int((y2-vy)*sy)+4))
        if crop[2]<=crop[0] or crop[3]<=crop[1]: continue
        checked+=1
        # Evaluate local narrow strips too: missing one outline cannot be diluted
        # by the blank interior of a large document icon.
        regions=[crop]
        if local(el.tag) in {"rect","polygon"}:
            a,b,c,d=crop
            regions += [(a,b,min(a+8,c),d),(max(a,c-8),b,c,d),(a,b,c,min(b+8,d)),(a,max(b,d-8),c,d)]
        maximum=max(sum(ImageStat.Stat(difference.crop(r)).rms)/(3*255) for r in regions)
        if maximum>.14:
            failures.append({"component":el.get("id",local(el.tag)),"local_rms":round(maximum,6)})
    return {"status":"PASS" if global_rms<=.035 and not failures else "FAIL","svg_renderer":"librsvg","export_renderer":"librsvg" if export_path.suffix.lower()==".svg" else "MuPDF (PDF interpreter)","global_rms":round(global_rms,6),"components_checked":checked,"local_failures":failures}
