import unittest
from cnes_audit.visuals import bed_comparison, bed_composition


class BedVisualTest(unittest.TestCase):
    def test_single_state_bar_has_visible_row_and_exact_intervals(self):
        frame, chart = bed_composition(110713, 62439)
        self.assertEqual(list(frame["Inicio"]), [0, 62439])
        self.assertEqual(list(frame["Fim"]), [62439, 110713])
        self.assertEqual(sum(frame["Leitos"]), 110713)
        spec = chart.to_dict()
        self.assertEqual(spec["encoding"]["y"]["field"], "Linha")
        self.assertEqual(spec["encoding"]["x2"]["field"], "Fim")
        self.assertEqual(spec["encoding"]["color"]["scale"]["domain"][0], "Destinados ao SUS")

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
