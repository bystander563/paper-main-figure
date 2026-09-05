"""Small measured layout primitives for editable scientific SVGs.

Coordinates are design units; use a physical placement width from the venue.
This module solves text/shape geometry, not scientific content or optical QA.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from font_metrics import font_path, fingerprint, measure


def n(value):
    return f"{float(value):.4f}".rstrip("0").rstrip(".") or "0"


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.x,self.y,self.w,self.h)) or self.w <= 0 or self.h <= 0:
            raise ValueError("Box must have finite coordinates and positive dimensions")

    @property
    def cx(self): return self.x+self.w/2
    @property
    def cy(self): return self.y+self.h/2
    @property
    def right(self): return self.x+self.w
    @property
    def bottom(self): return self.y+self.h

    def inset(self, amount):
        return Box(self.x+amount,self.y+amount,self.w-2*amount,self.h-2*amount)

    def port(self, side, offset=0):
        return {"left":(self.x,self.cy+offset), "right":(self.right,self.cy+offset),
                "top":(self.cx+offset,self.y), "bottom":(self.cx+offset,self.bottom)}[side]


def row(box: Box, count: int, gap: float, weights=None):
    if count < 1 or gap < 0:
        raise ValueError("Invalid row count or gap")
    values = list(weights or [1]*count)
    if len(values) != count or min(values) <= 0:
        raise ValueError("Weights must be positive and match count")
    usable = box.w-gap*(count-1)
    if usable <= 0:
        raise ValueError("Gaps consume row")
    x, result = box.x, []
    for value in values:
        width = usable*value/sum(values)
        result.append(Box(x,box.y,width,box.h))
        x += width+gap
    return result


def column(box: Box, count: int, gap: float, weights=None):
    return [Box(box.x,b.x,box.w,b.w) for b in row(Box(box.y,box.x,box.h,box.w),count,gap,weights)]


class Figure:
    def __init__(self, width, height, placement_mm=160, family="Arial", minimum_pt=7):
        self.width,self.height,self.placement_mm = width,height,placement_mm
        self.family,self.minimum_pt = family,minimum_pt
        self.root = ET.Element("svg", {"xmlns":"http://www.w3.org/2000/svg", "viewBox":f"0 0 {n(width)} {n(height)}",
            "width":f"{n(placement_mm)}mm", "height":f"{n(placement_mm*height/width)}mm", "data-layout-profile":"measured-v1"})
        self.elements,self.boxes = {},{}

    def add(self, tag, identifier, **attrs):
        if identifier in self.elements:
            raise ValueError(f"Duplicate component ID {identifier}")
        element = ET.SubElement(self.root,tag,{"id":identifier, **{k.replace('_','-'):n(v) if isinstance(v,(int,float)) else str(v) for k,v in attrs.items()}})
        self.elements[identifier] = element
        return element

    def rect(self, identifier, box, fill="#FFFFFF", stroke="#AAB5BB", radius=10, width=1.8, family=None):
        attrs={"x":box.x,"y":box.y,"width":box.w,"height":box.h,"rx":radius,"fill":fill,"stroke":stroke,"stroke_width":width}
        if family: attrs["data_equal_size"] = family
        self.boxes[identifier] = box
        return self.add("rect",identifier,**attrs)

    def line(self, identifier, points, color="#617079", width=1.8, dashed=False, role="relation"):
        attrs={"points":" ".join(f"{n(x)},{n(y)}" for x,y in points),"fill":"none","stroke":color,"stroke_width":width,"stroke_linecap":"round","stroke_linejoin":"round","data_role":role}
        if dashed: attrs["stroke_dasharray"]="7 5"
        return self.add("polyline",identifier,**attrs)

    def arrow(self, identifier, start, end, elbow=None, color="#617079", width=1.8, dashed=False):
        points=[start]+([elbow] if elbow else [])+[end]
        for (x1,y1),(x2,y2) in zip(points,points[1:]):
            if x1 != x2 and y1 != y2:
                raise ValueError("Ordinary arrows must use horizontal or vertical segments")
        line=self.line(identifier,points,color,width,dashed,role="connector")
        line.set("data-connector","true")
        (x0,y0),(x,y)=points[-2:]
        distance=math.hypot(x-x0,y-y0)
        if distance < 9: raise ValueError("Arrow requires a visible shaft")
        dx,dy=(x-x0)/distance,(y-y0)/distance
        head=[(x,y),(x-dx*9-dy*4,y-dy*9+dx*4),(x-dx*9+dy*4,y-dy*9-dx*4)]
        self.add("polygon",identifier+"-head",points=" ".join(f"{n(a)},{n(b)}" for a,b in head),fill=color,stroke="none")

    def circle(self,identifier,x,y,r,fill="#FFFFFF",stroke="#617079",width=1.8):
        return self.add("circle",identifier,cx=x,cy=y,r=r,fill=fill,stroke=stroke,stroke_width=width)

    def connect(self,identifier,start_owner,end_owner,start_port="right",end_port="left",gap=8,elbow=None,dashed=False):
        def point(owner,side):
            x,y=self.boxes[owner].port(side)
            dx,dy={"left":(-gap,0),"right":(gap,0),"top":(0,-gap),"bottom":(0,gap)}[side]
            return x+dx,y+dy
        self.arrow(identifier,point(start_owner,start_port),point(end_owner,end_port),elbow=elbow,dashed=dashed)
        line=self.elements[identifier]
        for name,value in {"data-start-owner":start_owner,"data-end-owner":end_owner,"data-start-port":start_port,"data-end-port":end_port,"data-port-gap":n(gap)}.items():
            line.set(name,value)

    def header_card(self,identifier,box,header_height,gap=0,header_fill="#E8F1ED",stroke="#AAB5BB"):
        header,body=header_body(box,header_height,gap)
        self.rect(identifier,box,stroke=stroke)
        self.rect(identifier+"-header",header,fill=header_fill,stroke="none",width=0)
        self.elements[identifier].set("data-header-owner",identifier+"-header")
        self.elements[identifier].set("data-header-gap",n(gap))
        return header,body

    def text(self, identifier, value, box, owner, size=28, weight="400", align="center", valign="center", padding=0, baseline=None, baseline_family=None, role="label", wrap=False, zone=None):
        if owner not in self.boxes:
            raise ValueError(f"Text owner must be a registered fixed visible shape: {owner}")
        outer=self.boxes[owner]
        if self.elements[owner].get("data-header-owner"):
            head=self.boxes[self.elements[owner].get("data-header-owner")]
            gap=float(self.elements[owner].get("data-header-gap","0"))
            region=head if zone=="header" else Box(outer.x,head.bottom+gap,outer.w,outer.bottom-head.bottom-gap)
            if zone not in {"header","body"} or box.x<region.x or box.y<region.y or box.right>region.right or box.bottom>region.bottom:
                raise ValueError("Header-card text requires an explicit valid header or body region")
        if box.x < outer.x-0.01 or box.y < outer.y-0.01 or box.right > outer.right+0.01 or box.bottom > outer.bottom+0.01:
            raise ValueError(f"Text frame outside owner: {identifier}")
        if size*self.placement_mm/self.width*72/25.4 < self.minimum_pt-1e-6:
            raise ValueError(f"{identifier}: text below declared final-size minimum")
        inner=box.inset(padding) if padding else box
        lines=value.split("\n")
        if wrap:
            lines=[]
            for para in value.split("\n"):
                current=""
                for word in para.split():
                    trial=(current+" "+word).strip()
                    if current and measure(trial,size,self.family,weight)[0][2] > inner.w:
                        lines.append(current); current=word
                    else: current=trial
                lines.append(current)
        metrics=[measure(v,size,self.family,weight)[0] for v in lines]
        step=size*1.24
        top=min(b[1]+i*step for i,b in enumerate(metrics))
        bottom=max(b[3]+i*step for i,b in enumerate(metrics))
        if max(b[2]-b[0] for b in metrics) > inner.w+0.01 or bottom-top > inner.h+0.01:
            raise ValueError(f"{identifier}: label does not fit; reflow or enlarge frame (no silent shrinking)")
        if baseline is not None:
            y=baseline
            valign="baseline"
        elif valign=="center": y=inner.cy-(top+bottom)/2
        elif valign=="top": y=inner.y-top
        else: raise ValueError("Use center, top, or an explicit baseline")
        attrs={"x":0,"y":y,"font_family":self.family,"font_size":size,"font_weight":weight,"fill":"#26343D",
            "data_font_sha256":fingerprint(str(font_path(self.family,weight))),"data_layout_owner":owner,
            "data_layout_box":" ".join(n(v) for v in (box.x,box.y,box.w,box.h)),"data_layout_padding":padding,
            "data_layout_align":align,"data_layout_valign":valign,"data_role":role}
        if baseline_family: attrs["data_align_baseline"]=baseline_family
        if zone: attrs["data_layout_zone"]=zone
        el=self.add("text",identifier,**attrs)
        for index,(line,bounds) in enumerate(zip(lines,metrics)):
            if align=="center": x=inner.cx-(bounds[0]+bounds[2])/2
            elif align=="left": x=inner.x-bounds[0]
            elif align=="right": x=inner.right-bounds[2]
            else: raise ValueError("Text alignment must be left, center or right")
            if len(lines)==1:
                el.set("x",n(x));el.text=line
            else:
                ET.SubElement(el,"tspan",{"x":n(x),"y":n(y+index*step)}).text=line
        return el

    def document(self, identifier, box, fill="#FFFFFF", stroke="#6F8899", width=1.8):
        fold=min(20,box.w*.16,box.h*.2)
        points=[(box.x,box.y),(box.right-fold,box.y),(box.right,box.y+fold),(box.right,box.bottom),(box.x,box.bottom),(box.x,box.y)]
        self.boxes[identifier]=box
        self.add("polygon",identifier,points=" ".join(f"{n(x)},{n(y)}" for x,y in points),fill=fill,stroke=stroke,stroke_width=width)
        self.line(identifier+"-fold",[(box.right-fold,box.y),(box.right-fold,box.y+fold),(box.right,box.y+fold)],stroke,width)

    def icon_label(self,identifier,value,box,owner,draw_icon,icon_width=32,icon_height=40,gap=12,size=28):
        ink,_=measure(value,size,self.family)
        text_width=ink[2]-ink[0]
        combined_width=icon_width+gap+text_width
        if combined_width>box.w or max(icon_height,ink[3]-ink[1])>box.h:
            raise ValueError("Icon-label group does not fit; reflow or enlarge it")
        x=box.cx-combined_width/2
        icon_box=Box(x,box.cy-icon_height/2,icon_width,icon_height)
        draw_icon(identifier+"-icon",icon_box)
        text_box=Box(x+icon_width+gap,box.y,text_width,box.h)
        label=self.text(identifier+"-label",value,text_box,owner,size=size)
        label.set("data-icon-peer",identifier+"-icon")
        label.set("data-group-frame"," ".join(n(v) for v in (box.x,box.y,box.w,box.h)))

    def tags(self,identifier,labels,box,gap=12,size=28):
        # One shared baseline, not independently centered glyph boxes.
        cells=row(box,len(labels),gap)
        ink,_=measure("Hg",size,self.family)
        baseline=box.cy-(ink[1]+ink[3])/2
        for i,(value,cell) in enumerate(zip(labels,cells)):
            id=f"{identifier}-{i}"
            self.rect(id,cell,fill="#FFFFFF",stroke="#8BA89D",radius=7,family=identifier)
            self.text(id+"-label",value,cell,id,size=size,padding=10,baseline=baseline,baseline_family=identifier)
        return cells

    def save(self,path):
        ET.indent(self.root,space="  ")
        ET.ElementTree(self.root).write(path,encoding="utf-8",xml_declaration=True)


def header_body(box, header_height, gap=0):
    if header_height <= 0 or header_height+gap >= box.h:
        raise ValueError("Header consumes the content body")
    return Box(box.x,box.y,box.w,header_height),Box(box.x,box.y+header_height+gap,box.w,box.h-header_height-gap)
