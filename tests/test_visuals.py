import unittest
from cnes_audit.visuals import bed_comparison


class BedVisualTest(unittest.TestCase):
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
