"""Real independent-render regressions for small missing outlines."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from figure_components import Figure, Box
from render_quality import render, compare


class RenderQualityTests(unittest.TestCase):
    def test_missing_independent_renderer_fails(self):
        with patch("render_quality.shutil.which",return_value=None):
            with self.assertRaises(ValueError): render(Path("figure.svg"))

    @unittest.skipUnless(shutil.which("rsvg-convert"),"librsvg required for live render test")
    def test_positive_export_and_missing_document_edge(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            f=Figure(800,400)
            f.rect("canvas",Box(0,0,800,400),"#FFFFFF","none",0,0)
            f.document("doc",Box(300,100,100,180),width=2)
            svg=base/"figure.svg";pdf=base/"figure.pdf"
            f.save(svg)
            subprocess.run(["rsvg-convert","-f","pdf","-o",str(pdf),str(svg)],check=True)
            self.assertEqual(compare(svg,pdf)["status"],"PASS")
            # Remove the left contour by changing the closed document into an
            # open polyline. It occupies too little area for a global-only check.
            element=f.elements["doc"]
            points=element.get("points").split()
            element.tag="polyline";element.set("points"," ".join(points[:-1]))
            element.set("fill","none")
            bad=base/"bad.svg";f.save(bad)
            subprocess.run(["rsvg-convert","-f","pdf","-o",str(pdf),str(bad)],check=True)
            result=compare(svg,pdf)
            self.assertEqual(result["status"],"FAIL")
            self.assertTrue(result["local_failures"])


    @unittest.skipUnless(shutil.which("rsvg-convert"),"librsvg required for live render test")
    def test_deleted_path_detected_locally(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            f=Figure(800,400)
            f.rect("canvas",Box(0,0,800,400),"#FFFFFF","none",0,0)
            path=f.add("path","edge",d="M290 180 H510",fill="none",stroke="#333333",stroke_width=2)
            source=base/"source.svg";bad=base/"bad.svg";pdf=base/"bad.pdf"
            f.save(source);f.root.remove(path);f.save(bad)
            subprocess.run(["rsvg-convert","-f","pdf","-o",str(pdf),str(bad)],check=True)
            result=compare(source,pdf)
            self.assertEqual(result["status"],"FAIL")
            self.assertTrue(any(x["component"]=="edge" for x in result["local_failures"]))


if __name__=="__main__": unittest.main()
