import json
import tempfile
import unittest
from pathlib import Path

from cnes_audit.population import enrich_states_with_population, read_population_estimates


def sidra_payload(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    header = {
        "V": "Valor",
        "D1C": "Unidade da Federação (Código)",
        "D1N": "Unidade da Federação",
        "D3C": "Ano (Código)",
        "D3N": "Ano",
    }
    return [header, *rows]


class PopulationSourceTest(unittest.TestCase):
    def test_reads_population_and_reference_year_from_sidra(self):
        payload = sidra_payload(
            [
                {"V": "1757338", "D1C": "11", "D1N": "Rondônia", "D3C": "2026", "D3N": "2026"},
                {"V": "887794", "D1C": "12", "D1N": "Acre", "D3C": "2026", "D3N": "2026"},
            ]
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "population.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            result = read_population_estimates(path, expected_states=2)

        self.assertEqual(result["reference_year"], 2026)
        self.assertEqual(result["total_population"], 2_645_132)
        self.assertEqual(
            result["by_state"],
            [
                {"code": "11", "name": "Rondônia", "population": 1_757_338},
                {"code": "12", "name": "Acre", "population": 887_794},
            ],
        )

    def test_rejects_incomplete_state_coverage(self):
        payload = sidra_payload(
            [{"V": "1757338", "D1C": "11", "D1N": "Rondônia", "D3C": "2026", "D3N": "2026"}]
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "population.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "cobertura de UFs incompatível"):
                read_population_estimates(path, expected_states=2)

    def test_rejects_mixed_reference_years(self):
        payload = sidra_payload(
            [
                {"V": "1757338", "D1C": "11", "D1N": "Rondônia", "D3C": "2026", "D3N": "2026"},
                {"V": "887794", "D1C": "12", "D1N": "Acre", "D3C": "2025", "D3N": "2025"},
            ]
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "population.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "mais de um ano"):
                read_population_estimates(path, expected_states=2)

    def test_calculates_establishments_per_100_thousand_inhabitants(self):
        cnes_states = [
            {"code": "11", "name": "Rondônia", "records": 200, "issues": 10},
            {"code": "12", "name": "Acre", "records": 150, "issues": 5},
        ]
        population = {
            "reference_year": 2026,
            "total_population": 3_000_000,
            "by_state": [
                {"code": "11", "name": "Rondônia", "population": 2_000_000},
                {"code": "12", "name": "Acre", "population": 1_000_000},
            ],
        }

        result = enrich_states_with_population(cnes_states, population)

        self.assertEqual(result[0]["population"], 2_000_000)
        self.assertEqual(result[0]["establishments_per_100k"], 10.0)
        self.assertEqual(result[1]["establishments_per_100k"], 15.0)

    def test_rejects_join_when_a_cnes_state_has_no_population(self):
        cnes_states = [{"code": "11", "name": "Rondônia", "records": 200, "issues": 10}]
        population = {
            "reference_year": 2026,
            "total_population": 1_000_000,
            "by_state": [{"code": "12", "name": "Acre", "population": 1_000_000}],
        }

        with self.assertRaisesRegex(ValueError, "sem correspondência"):
            enrich_states_with_population(cnes_states, population)


if __name__ == "__main__":
    unittest.main()
