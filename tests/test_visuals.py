import unittest
from cnes_audit.visuals import bed_comparison
from streamlit.testing.v1 import AppTest


class BedVisualTest(unittest.TestCase):
    def test_chart_numbers_use_brazilian_grouping(self):
        from streamlit_app import style_chart
        _, chart = bed_comparison([{"code": "35", "name": "São Paulo", "beds": 110713, "sus_beds": 62439, "population": 45973194}])
        spec = style_chart(chart).to_dict()
        self.assertEqual(spec["config"]["locale"]["number"]["thousands"], ".")
        self.assertEqual(spec["config"]["locale"]["number"]["decimal"], ",")
        self.assertEqual(spec["layer"][0]["encoding"]["y"]["axis"]["format"], ",.0f")

    def test_state_composition_labels_are_visible_without_hover(self):
        app = AppTest.from_string("from streamlit_app import render_bed_composition\nrender_bed_composition(1847, 1635)").run(timeout=40)
        self.assertFalse(app.exception)
        html = app.markdown[0].value
        for text in ("1.847 leitos", "Destinados ao SUS", "Demais leitos", "1.635", "212", "88,5%", "11,5%", "aria-label"):
            self.assertIn(text, html)

    def test_empty_and_full_sus_compositions_do_not_hide_labels(self):
        for total, sus in ((100, 0), (100, 100)):
            app = AppTest.from_string(f"from streamlit_app import render_bed_composition\nrender_bed_composition({total}, {sus})").run(timeout=40)
            self.assertFalse(app.exception)
            self.assertIn("0,0% do total", app.markdown[0].value)
            self.assertIn("100,0% do total", app.markdown[0].value)
        app = AppTest.from_string("from streamlit_app import render_bed_composition\nrender_bed_composition(0, 0)").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertFalse(app.markdown)

    def test_components_reconcile_before_display_rounding(self):
        rows = [{"code": "35", "name": "São Paulo", "beds": 10, "sus_beds": 3, "population": 333}]
        for proportional in (True, False):
            frame, chart = bed_comparison(rows, proportional)
            self.assertAlmostEqual(frame.iloc[0]["SUS"] + frame.iloc[0]["Demais"], frame.iloc[0]["Total"])
            self.assertEqual(frame.iloc[0]["UF"], "SP")
            spec = chart.to_dict()
            self.assertEqual(spec["layer"][0]["mark"]["type"], "bar")
            self.assertEqual(spec["layer"][1]["mark"]["type"], "line")
            self.assertNotIn("resolve", spec)  # shared y-scale

    def test_invalid_sus_composition_is_rejected(self):
        with self.assertRaises(ValueError):
            bed_comparison([{"code": "35", "name": "SP", "beds": 1, "sus_beds": 2, "population": 100}])
