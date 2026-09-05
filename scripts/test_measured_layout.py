"""Real positive and adversarial regressions for measured scientific layouts."""
import copy
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from figure_components import Figure,Box,row,column,header_body
from font_metrics import measure,font_path,text_bounds
from micro_layout_audit import audit,fixed_bounds,revision_gap
from svg_layout_audit import audit as svg_audit


class MeasuredLayoutTests(unittest.TestCase):
    def fixture(self):
        f=Figure(800,400)
        b=Box(50,50,300,180)
        f.rect("card",b)
        _,body=header_body(b,50)
        f.text("label","Final text",body.inset(12),"card",size=22)
        return f

    def codes(self,f):
        return {item["code"] for item in audit(f.root)["findings"]}

    def test_widths_not_character_count(self):
        w=measure("WWW",28)[0];i=measure("iii",28)[0]
        self.assertGreater(w[2]-w[0],3*(i[2]-i[0]))

    def test_bold_face_changes_actual_width(self):
        regular=measure("human",28)[0]
        bold=measure("human",28,weight="700")[0]
        self.assertGreater(bold[2]-bold[0],regular[2]-regular[0])

    def test_missing_font_does_not_fallback(self):
        with self.assertRaises(ValueError): font_path("Nonexistent face 9B8977")

    def test_missing_glyph_fails(self):
        with self.assertRaises(ValueError): measure("标签",28,"Arial")

    def test_white_body_center_not_outer_center(self):
        f=self.fixture()
        self.assertEqual(audit(f.root)["status"],"PASS")
        f.elements["label"].set("y",str(float(f.elements["label"].get("y"))-25))
        self.assertIn("TEXT_VERTICAL_CENTER",self.codes(f))

    def test_multiline_center_passes(self):
        f=self.fixture()
        f.rect("other",Box(400,70,300,170))
        f.text("two-lines","Base encoder\nBinary head",Box(412,82,276,146),"other",size=22)
        self.assertEqual(audit(f.root)["status"],"PASS")

    def test_large_word_fails_before_drawing(self):
        f=self.fixture()
        with self.assertRaises(ValueError):
            f.text("overflow","Unreasonably long label",Box(60,60,80,40),"card",size=22)

    def test_css_override_rejected_by_both_audits(self):
        f=self.fixture();f.elements["label"].set("style","font-size:80px")
        self.assertIn("INLINE_STYLE_NOT_AUDITED",self.codes(f))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"style.svg";f.save(path)
            self.assertEqual(svg_audit(path,160)["status"],"FAIL")

    def test_painted_header_body_binding(self):
        f=Figure(800,400)
        outer=Box(50,50,300,280)
        head,body=f.header_card("card",outer,60)
        f.text("title","Input",head.inset(10),"card",size=22,zone="header")
        f.text("body","Final text",body.inset(10),"card",size=22,zone="body")
        self.assertEqual(audit(f.root)["status"],"PASS")
        with self.assertRaises(ValueError):
            f.text("wrong","Final text",outer.inset(10),"card",size=22,zone="body")
        f.elements["body"].set("data-layout-box","60 60 280 260")
        self.assertIn("HEADER_BODY_REGION",self.codes(f))

    def test_visible_header_without_binding_rejected(self):
        f=Figure(800,400)
        f.rect("card",Box(50,50,300,280))
        f.rect("header",Box(50,50,300,60))
        f.text("body","Final text",Box(60,60,280,260),"card",size=22)
        self.assertIn("HEADER_BODY_BINDING",self.codes(f))

    def test_right_padding_movement_detected(self):
        f=self.fixture()
        el=f.elements["label"]
        el.set("x",str(float(el.get("x"))+230))
        self.assertIn("TEXT_INNER_PADDING",self.codes(f))

    def test_container_not_inflated_by_child(self):
        root=ET.fromstring('<g><rect x="0" y="0" width="100" height="100" fill="#ffffff"/><text x="90" y="40" font-size="28">Overflow</text></g>')
        self.assertEqual(fixed_bounds(root),(0.,0.,100.,100.))

    def test_group_without_unique_shape_rejected(self):
        root=ET.fromstring('<g><rect x="0" y="0" width="100" height="100"/><rect x="100" y="0" width="100" height="100"/></g>')
        with self.assertRaises(ValueError): fixed_bounds(root)

    def test_invisible_frame_rejected(self):
        for extra in ['fill="none" stroke="#333" stroke-width="0"',
                      'fill="#fff" opacity="0"',
                      'fill="none" stroke="#333" stroke-opacity="0"']:
            shape=ET.fromstring(f'<rect x="0" y="0" width="100" height="100" {extra}/>')
            with self.assertRaises(ValueError): fixed_bounds(shape)

    def test_legacy_profile_is_not_micro_pass(self):
        f=self.fixture();del f.root.attrib["data-layout-profile"]
        self.assertEqual(audit(f.root)["status"],"LEGACY_UNMEASURED")

    def test_typography_role_drift_is_detected(self):
        f=self.fixture()
        f.rect("second",Box(400,50,300,180))
        f.text("other","Final text",Box(410,100,280,100),"second",size=22)
        f.elements["other"].set("font-size","23")
        self.assertIn("TYPOGRAPHY_ROLE_DRIFT",self.codes(f))

    def test_missing_label_metadata_is_not_pass(self):
        f=self.fixture();del f.elements["label"].attrib["data-layout-owner"]
        self.assertIn("TEXT_LAYOUT_METADATA",self.codes(f))

    def test_changed_font_hash_rejected(self):
        f=self.fixture();f.elements["label"].set("data-font-sha256","0"*64)
        self.assertIn("TEXT_LAYOUT_METADATA",self.codes(f))

    def test_icon_and_label_center_as_group(self):
        f=Figure(800,400);f.rect("panel",Box(20,20,760,360))
        f.icon_label("document","Final text",Box(100,80,500,90),"panel",f.document,size=22)
        self.assertEqual(audit(f.root)["status"],"PASS")
        label=f.elements["document-label"];label.set("x",str(float(label.get("x"))+25))
        self.assertIn("ICON_LABEL_GROUP_CENTER",self.codes(f))

    def test_tags_share_baseline(self):
        f=Figure(800,400)
        f.tags("row",["trajectory","generator","operation"],Box(20,50,760,60),size=22)
        baselines={e.get("y") for e in f.elements.values() if e.tag=="text"}
        self.assertEqual(len(baselines),1)
        self.assertEqual(audit(f.root)["status"],"PASS")

    def test_row_column_size_and_gap(self):
        cells=row(Box(10,20,320,200),3,10)
        self.assertEqual([b.w for b in cells],[100,100,100])
        self.assertEqual(cells[1].x-cells[0].right,10)
        cols=column(Box(10,20,320,200),2,20)
        self.assertEqual(cols[1].y-cols[0].bottom,20)

    def test_visible_horizontal_connector_has_painted_bounds(self):
        from figure_layout_audit import element_bounds
        line=ET.fromstring('<line x1="10" y1="20" x2="80" y2="20" fill="none" stroke="#333" stroke-width="2"/>')
        self.assertEqual(element_bounds(line),(9.,19.,81.,21.))

    def test_port_tracks_owner(self):
        f=Figure(800,400)
        f.rect("a",Box(20,50,200,100));f.rect("b",Box(300,50,200,100))
        f.connect("edge","a","b")
        self.assertEqual(audit(f.root)["status"],"PASS")
        f.elements["b"].set("y","90")
        self.assertIn("CONNECTOR_PORT_DRIFT",self.codes(f))

    def test_fill_none_line_and_path_collisions(self):
        templates=['<line x1="90" y1="90" x2="240" y2="90"/>','<polyline points="90,90 240,90"/>','<path d="M90 90 H240"/>']
        with tempfile.TemporaryDirectory() as directory:
            for shape in templates:
                for fill in ['', ' fill="none"']:
                    path=Path(directory)/"test.svg"
                    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="80mm" viewBox="0 0 400 200"><text x="80" y="100" font-family="Arial" font-size="28" fill="#222222">human</text>'+shape.replace('/>',f' stroke="#333333" stroke-width="2"{fill}/></svg>'),encoding="utf-8")
                    codes={r["code"] for r in svg_audit(path,160)["findings"]}
                    self.assertIn("TEXT_STROKE_COLLISION",codes)

    def test_revision_requires_actual_gap_change_and_fixed_anchor(self):
        before={"heading":(0,0,100,20),"body":(0,40,100,70)}
        correct={**before,"body":(0,50,100,80)}
        wrong={"heading":(0,10,100,30),"body":(0,50,100,80)}
        self.assertEqual(revision_gap(before,correct,"heading","body","heading",allowed=["body"])["status"],"PASS")
        self.assertEqual(revision_gap(before,wrong,"heading","body","heading",allowed=["body"])["status"],"FAIL")


if __name__=="__main__": unittest.main()
