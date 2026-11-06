from io import BytesIO
import unittest
from zipfile import ZipFile

from cnes_audit.beds import (
    aggregate_bed_history,
    aggregate_latest_bed_capacity,
    enrich_bed_history_with_population,
    enrich_beds_with_population,
)


BED_COLUMNS = (
    "COMP",
    "UF",
    "CNES",
    "LEITOS_EXISTENTES",
    "LEITOS_SUS",
    "UTI_TOTAL_EXIST",
    "UTI_TOTAL_SUS",
)


def make_bed_zip(rows: list[list[str]]) -> BytesIO:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        content = [";".join(BED_COLUMNS), *(";".join(row) for row in rows)]
        archive.writestr("Leitos_2026.csv", "\n".join(content).encode("cp1252"))
    buffer.seek(0)
    return buffer


class BedCapacityTest(unittest.TestCase):
    def test_builds_a_reconciled_history_for_each_competence(self):
        source = make_bed_zip(
            [
                ["202601", "SP", "1", "100", "70", "10", "8"],
                ["202601", "RJ", "2", "80", "60", "6", "5"],
                ["202602", "SP", "1", "110", "75", "12", "9"],
                ["202602", "RJ", "2", "90", "80", "6", "5"],
            ]
        )

        result = aggregate_bed_history(source, expected_states=2)

        self.assertEqual(result["competences"], 2)
        self.assertEqual(result["first_competence"], "202601")
        self.assertEqual(result["latest_competence"], "202602")
        self.assertEqual(result["rows_read"], 4)
        self.assertEqual(result["national"][0]["beds"], 180)
        self.assertEqual(result["national"][1]["sus_beds"], 155)
        self.assertEqual(len(result["by_state"]), 4)

    def test_aggregates_only_the_latest_competence_by_state(self):
        source = make_bed_zip(
            [
                ["202601", "SP", "1", "100", "70", "10", "8"],
                ["202602", "SP", "1", "110", "75", "12", "9"],
                ["202602", "RJ", "2", "90", "80", "6", "5"],
                ["202601", "RJ", "2", "85", "75", "5", "4"],
            ]
        )

        result = aggregate_latest_bed_capacity(source, expected_states=2)

        self.assertEqual(result["competence"], "202602")
        self.assertEqual(result["rows_read"], 4)
        self.assertEqual(result["rows_selected"], 2)
        self.assertEqual(result["total_beds"], 200)
        self.assertEqual(result["sus_beds"], 155)
        self.assertEqual(result["uti_beds"], 18)
        self.assertEqual(result["uti_sus_beds"], 14)
        self.assertEqual(
            result["by_state"],
            [
                {
                    "code": "33",
                    "name": "Rio de Janeiro",
                    "beds": 90,
                    "sus_beds": 80,
                    "uti_beds": 6,
                    "uti_sus_beds": 5,
                },
                {
                    "code": "35",
                    "name": "São Paulo",
                    "beds": 110,
                    "sus_beds": 75,
                    "uti_beds": 12,
                    "uti_sus_beds": 9,
                },
            ],
        )

    def test_rejects_duplicate_cnes_in_latest_competence(self):
        source = make_bed_zip(
            [
                ["202602", "SP", "1", "100", "70", "10", "8"],
                ["202602", "SP", "1", "100", "70", "10", "8"],
            ]
        )

        with self.assertRaisesRegex(ValueError, "CNES repetido"):
            aggregate_latest_bed_capacity(source, expected_states=1)

    def test_rejects_negative_or_inconsistent_bed_counts(self):
        negative = make_bed_zip(
            [["202602", "SP", "1", "-1", "0", "0", "0"]]
        )
        sus_above_total = make_bed_zip(
            [["202602", "SP", "1", "10", "11", "0", "0"]]
        )

        with self.assertRaisesRegex(ValueError, "quantidade de leitos inválida"):
            aggregate_latest_bed_capacity(negative, expected_states=1)
        with self.assertRaisesRegex(ValueError, "leitos SUS maior"):
            aggregate_latest_bed_capacity(sus_above_total, expected_states=1)

    def test_rejects_incomplete_state_coverage(self):
        source = make_bed_zip(
            [["202602", "SP", "1", "100", "70", "10", "8"]]
        )

        with self.assertRaisesRegex(ValueError, "cobertura de UFs incompatível"):
            aggregate_latest_bed_capacity(source, expected_states=2)

    def test_rejects_incomplete_state_coverage_in_any_competence(self):
        source = make_bed_zip(
            [
                ["202601", "SP", "1", "100", "70", "10", "8"],
                ["202602", "SP", "1", "110", "75", "12", "9"],
                ["202602", "RJ", "2", "90", "80", "6", "5"],
            ]
        )

        with self.assertRaisesRegex(ValueError, "202601"):
            aggregate_bed_history(source, expected_states=2)

    def test_calculates_total_and_sus_bed_rates_with_population(self):
        states = [
            {
                "code": "35",
                "name": "São Paulo",
                "beds": 200,
                "sus_beds": 120,
                "uti_beds": 20,
                "uti_sus_beds": 12,
            }
        ]
        population = {
            "by_state": [{"code": "35", "name": "São Paulo", "population": 2_000_000}]
        }

        result = enrich_beds_with_population(states, population)

        self.assertEqual(result[0]["beds_per_100k"], 10.0)
        self.assertEqual(result[0]["sus_beds_per_100k"], 6.0)

    def test_calculates_history_rates_with_one_population_reference(self):
        history = {
            "rows_read": 1,
            "competences": 1,
            "first_competence": "202601",
            "latest_competence": "202601",
            "national": [
                {
                    "competence": "202601",
                    "rows_selected": 1,
                    "beds": 200,
                    "sus_beds": 120,
                    "uti_beds": 20,
                    "uti_sus_beds": 12,
                }
            ],
            "by_state": [
                {
                    "competence": "202601",
                    "code": "35",
                    "name": "São Paulo",
                    "beds": 200,
                    "sus_beds": 120,
                    "uti_beds": 20,
                    "uti_sus_beds": 12,
                }
            ],
        }
        population = {
            "reference_year": 2026,
            "total_population": 2_000_000,
            "by_state": [
                {"code": "35", "name": "São Paulo", "population": 2_000_000}
            ],
        }

        result = enrich_bed_history_with_population(history, population)

        self.assertEqual(result["summary"]["competences"], 1)
        self.assertEqual(result["national"][0]["beds_per_100k"], 10.0)
        self.assertEqual(result["by_state"][0]["uti_beds_per_100k"], 1.0)


if __name__ == "__main__":
    unittest.main()
