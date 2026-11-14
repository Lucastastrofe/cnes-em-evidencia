import unittest

from cnes_audit.professionals import (
    enrich_professionals_with_population,
    extract_latest_professional_file,
    parse_professional_snapshot,
)


DEFINITION_HTML = b"""
<option value="pfbr2608.dbf">Ago/2026</option>
<option value="pfbr2609.dbf" selected>Set/2026</option>
"""

SNAPSHOT_HTML = """
<html><body><pre>
"Unidade da Federa&ccedil;&atilde;o";"Sim";"N&atilde;o";"Total"
"33 Rio de Janeiro";80;20;100
"35 S&atilde;o Paulo";120;30;150
"Total";200;50;250
</pre></body></html>
""".encode("latin-1")


class ProfessionalSnapshotTest(unittest.TestCase):
    def test_finds_the_latest_available_competence(self):
        filename, competence = extract_latest_professional_file(DEFINITION_HTML)

        self.assertEqual(filename, "pfbr2609.dbf")
        self.assertEqual(competence, "202609")

    def test_parses_reconciled_counts_by_state_and_sus_status(self):
        result = parse_professional_snapshot(
            SNAPSHOT_HTML,
            competence="202609",
            expected_states=2,
        )

        self.assertEqual(result["competence"], "202609")
        self.assertEqual(result["total_professionals"], 250)
        self.assertEqual(result["sus_professionals"], 200)
        self.assertEqual(result["non_sus_professionals"], 50)
        self.assertEqual(
            result["by_state"],
            [
                {
                    "code": "33",
                    "name": "Rio de Janeiro",
                    "professionals": 100,
                    "sus_professionals": 80,
                    "non_sus_professionals": 20,
                },
                {
                    "code": "35",
                    "name": "São Paulo",
                    "professionals": 150,
                    "sus_professionals": 120,
                    "non_sus_professionals": 30,
                },
            ],
        )

    def test_rejects_a_total_that_does_not_reconcile(self):
        inconsistent = SNAPSHOT_HTML.replace(b'"Total";200;50;250', b'"Total";200;50;251')

        with self.assertRaisesRegex(ValueError, "reconcilia"):
            parse_professional_snapshot(
                inconsistent,
                competence="202609",
                expected_states=2,
            )

    def test_rejects_incomplete_state_coverage(self):
        with self.assertRaisesRegex(ValueError, "cobertura de UFs"):
            parse_professional_snapshot(SNAPSHOT_HTML, competence="202609")

    def test_calculates_population_rate_and_sus_share(self):
        states = [
            {
                "code": "35",
                "name": "São Paulo",
                "professionals": 150,
                "sus_professionals": 120,
                "non_sus_professionals": 30,
            }
        ]
        population = {
            "by_state": [
                {"code": "35", "name": "São Paulo", "population": 2_000_000}
            ]
        }

        result = enrich_professionals_with_population(states, population)

        self.assertEqual(result[0]["professionals_per_100k"], 7.5)
        self.assertEqual(result[0]["sus_share"], 0.8)


if __name__ == "__main__":
    unittest.main()
