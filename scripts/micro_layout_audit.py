"""Main-figure measured-layout profile; independently recompute label relations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import svg_layout_audit as svg


def fixed_bounds(element):
    tag=svg.local(element.tag)
    if tag not in {"rect","polygon","circle","ellipse"}:
        shapes=[c for c in element if svg.local(c.tag) in {"rect","polygon","circle","ellipse"}]
        if len(shapes)!=1:
            raise ValueError("Container must name one fixed painted shape, not a union of its contents")
        element=shapes[0]
    painted_fill=(svg.color_value(element,"fill","#000000")!="none" and
                  svg.number(element.get("fill-opacity","1"),"fill opacity")>0)
    painted_stroke=(svg.color_value(element,"stroke","none")!="none" and
                    svg.number(element.get("stroke-width","1"),"stroke width")>0 and
                    svg.number(element.get("stroke-opacity","1"),"stroke opacity")>0)
    if svg.number(element.get("opacity","1"),"opacity")<=0 or not (painted_fill or painted_stroke):
        raise ValueError("Invisible shape cannot establish a layout frame")
    return svg.geometry_bounds(element)


def audit(root):
    if root.get("data-layout-profile") != "measured-v1":
        return {"status":"LEGACY_UNMEASURED","labels_checked":0,"findings":[]}
    by_id={e.get("id"):e for e in root.iter() if e.get("id")}
    findings=[]
    boxes={}
    roles={}
    def fail(code,identifier,message):
        findings.append({"severity":"ERROR","code":code,"message":f"{identifier}: {message}"})
    for e in root.iter():
        if e.get("style","").strip():
            fail("INLINE_STYLE_NOT_AUDITED",e.get("id","svg"),"Expand CSS into explicit presentation attributes")
    for element in root.iter():
        if svg.local(element.tag)!="text": continue
        identifier=element.get("id","<unregistered>")
        try:
            if not element.get("data-font-sha256"):
                raise ValueError("Missing font fingerprint")
            owner_id=element.get("data-layout-owner")
            if owner_id not in by_id or owner_id==identifier:
                raise ValueError("Missing independent fixed owner shape")
            outer=fixed_bounds(by_id[owner_id])
            values=[svg.number(v,"layout frame") for v in element.get("data-layout-box","").split()]
            if len(values)!=4 or values[2]<=0 or values[3]<=0:
                raise ValueError("Missing positive x y width height layout frame")
            x,y,w,h=values
            frame=(x,y,x+w,y+h)
            if not svg.contains_bounds(outer,frame):
                raise ValueError("Declared content region leaves fixed owner")
            header_id=by_id[owner_id].get("data-header-owner")
            # A real painted top band cannot be ignored by omitting metadata.
            possible_headers=[]
            for candidate_id,candidate in by_id.items():
                if candidate_id==owner_id or svg.local(candidate.tag)!="rect" or svg.color_value(candidate,"fill","none")=="none": continue
                bound=svg.geometry_bounds(candidate)
                if max(abs(bound[0]-outer[0]),abs(bound[1]-outer[1]),abs(bound[2]-outer[2]))<=.5 and 0<bound[3]-outer[1]<(outer[3]-outer[1])/2:
                    possible_headers.append(candidate_id)
            if possible_headers and header_id not in possible_headers:
                fail("HEADER_BODY_BINDING",identifier,"Visible header band requires an independent header/body binding")
            if header_id:
                head=fixed_bounds(by_id[header_id])
                if max(abs(head[0]-outer[0]),abs(head[1]-outer[1]),abs(head[2]-outer[2]))>.5 or not (outer[1]<head[3]<outer[3]):
                    raise ValueError("Header no longer matches its fixed owner")
                zone=element.get("data-layout-zone")
                gap=float(by_id[owner_id].get("data-header-gap","0"))
                region=head if zone=="header" else (outer[0],head[3]+gap,outer[2],outer[3])
                if zone not in {"header","body"} or not svg.contains_bounds(region,frame):
                    fail("HEADER_BODY_REGION",identifier,"Content frame must stay in the declared painted header or white body")
            pad=svg.number(element.get("data-layout-padding","0"),"padding")
            if pad<0 or 2*pad>=min(w,h): raise ValueError("Invalid frame padding")
            inner=(x+pad,y+pad,x+w-pad,y+h-pad)
            size=svg.number(element.get("font-size"),"font size")
            ink=svg.text_bounds(element,size)
            boxes[identifier]=ink
            if not svg.contains_bounds(tuple(v+(-.5 if i<2 else .5) for i,v in enumerate(inner)),ink):
                fail("TEXT_INNER_PADDING",identifier,"Actual font bounds leave the intended content region")
            align=element.get("data-layout-align")
            expected={"left":inner[0],"right":inner[2],"center":(inner[0]+inner[2])/2}
            actual={"left":ink[0],"right":ink[2],"center":(ink[0]+ink[2])/2}
            if align not in expected: raise ValueError("Missing horizontal alignment intent")
            if abs(actual[align]-expected[align])>.5:
                fail("TEXT_HORIZONTAL_ALIGNMENT",identifier,"Ink range does not match its declared rail")
            valign=element.get("data-layout-valign")
            if valign=="center" and abs((ink[1]+ink[3]-inner[1]-inner[3])/2)>.5:
                fail("TEXT_VERTICAL_CENTER",identifier,"Text block is not centered in its declared body region")
            elif valign=="top" and abs(ink[1]-inner[1])>.5:
                fail("TEXT_TOP_ALIGNMENT",identifier,"Text block misses its top rail")
            elif valign not in {"center","top","baseline"}:
                raise ValueError("Missing vertical alignment intent")
            role=element.get("data-role")
            if not role: raise ValueError("Missing typography role")
            roles.setdefault(role,set()).add((element.get("font-family"),element.get("font-weight","400"),size))
            if element.get("data-icon-peer"):
                peer=fixed_bounds(by_id[element.attrib["data-icon-peer"]])
                gx,gy,gw,gh=map(float,element.attrib["data-group-frame"].split())
                group=(min(ink[0],peer[0]),min(ink[1],peer[1]),max(ink[2],peer[2]),max(ink[3],peer[3]))
                if not svg.contains_bounds(outer,(gx,gy,gx+gw,gy+gh)):
                    raise ValueError("Composite frame leaves owner")
                if max(abs((group[0]+group[2])/2-gx-gw/2),abs((group[1]+group[3])/2-gy-gh/2))>.5:
                    fail("ICON_LABEL_GROUP_CENTER",identifier,"The combined visible icon and label are not centered")
        except (ValueError,OSError,KeyError) as exc:
            fail("TEXT_LAYOUT_METADATA",identifier,str(exc))
    for role,styles in roles.items():
        if len(styles)>1: fail("TYPOGRAPHY_ROLE_DRIFT",role,"Same-role labels use different font metrics")
    items=list(boxes.items())
    for i,(a,first) in enumerate(items):
        for b,second in items[i+1:]:
            if svg.intersects_bounds(first,second):
                fail("TEXT_TEXT_COLLISION",a,f"Overlaps {b}")
    for element in root.iter():
        if not element.get("data-start-owner"): continue
        identifier=element.get("id", "connector")
        try:
            points=svg.parse_points(element.get("points",""))
            for prefix,endpoint in (("start",points[0]),("end",points[-1])):
                owner=fixed_bounds(by_id[element.attrib[f"data-{prefix}-owner"]])
                side=element.attrib[f"data-{prefix}-port"]
                gap=float(element.get("data-port-gap","8"))
                x1,y1,x2,y2=owner
                expected={"left":(x1-gap,(y1+y2)/2),"right":(x2+gap,(y1+y2)/2),"top":((x1+x2)/2,y1-gap),"bottom":((x1+x2)/2,y2+gap)}[side]
                if max(abs(a-b) for a,b in zip(endpoint,expected))>.5:
                    fail("CONNECTOR_PORT_DRIFT",identifier,f"{prefix} no longer follows its owner")
        except (ValueError,KeyError) as exc: fail("CONNECTOR_PORT_METADATA",identifier,str(exc))
    return {"status":"FAIL" if findings else "PASS","labels_checked":len(boxes),"findings":findings}


def revision_gap(before,after,first,second,anchor,axis="y",direction="increase",allowed=()):
    """Verify the requested relationship, not merely a changed screenshot.

before/after map component IDs to fixed or ink bounds already computed by the
auditor. An explicit allowlist includes permitted follower connectors.
"""
    errors=[]
    if set(before)!=set(after): errors.append("Component set changed")
    if before.get(anchor)!=after.get(anchor): errors.append("Fixed anchor moved")
    changed={k for k in before.keys() & after.keys() if before[k]!=after[k]}
    if changed-set(allowed): errors.append("Unapproved object moved")
    lo,hi=(1,3) if axis=="y" else (0,2)
    old=before[second][lo]-before[first][hi]
    new=after[second][lo]-after[first][hi]
    if direction not in {"increase","decrease"}: raise ValueError("Unknown revision direction")
    if (new-old)*(1 if direction=="increase" else -1)<=.5:
        errors.append("Requested gap did not change in the requested direction")
    return {"status":"FAIL" if errors else "PASS","before_gap":old,"after_gap":new,"findings":errors}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=audit(ET.parse(args.svg).getroot())
    payload=json.dumps(result,indent=2)
    if args.output: args.output.write_text(payload,encoding="utf-8")
    print(payload)
    raise SystemExit(0 if result["status"]=="PASS" else 1)
