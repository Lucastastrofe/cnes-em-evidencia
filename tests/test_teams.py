from io import BytesIO
import unittest

from cnes_audit.teams import (
    enrich_teams_with_population,
    extract_latest_team_file,
    parse_team_snapshot,
)


DEFINITION_HTML = b"""
<select name=\"Arquivos\">
  <option value=\"epbr2608.dbf\">Ago/2026</option>
  <option value=\"epbr2609.dbf\" selected>Set/2026</option>
</select>
"""

SNAPSHOT_HTML = """
<html><body><pre>
\"Unidade da Federa&ccedil;&atilde;o\";\"70 ESF - EQUIPE DE SAUDE DA FAMILIA\";\"71 ESB - EQUIPE DE SAUDE BUCAL\";\"Total\"
\"33 Rio de Janeiro\";80;40;120
\"35 S&atilde;o Paulo\";100;60;160
\"Total\";180;100;280
&amp;
</pre></body></html>
""".encode("latin-1")


class TeamSnapshotTest(unittest.TestCase):
    def test_finds_the_latest_available_competence(self):
        filename, competence = extract_latest_team_file(DEFINITION_HTML)

        self.assertEqual(filename, "epbr2609.dbf")
        self.assertEqual(competence, "202609")

    def test_parses_reconciled_team_counts_by_state_and_type(self):
        result = parse_team_snapshot(SNAPSHOT_HTML, competence="202609", expected_states=2)

        self.assertEqual(result["competence"], "202609")
        self.assertEqual(result["total_teams"], 280)
        self.assertEqual(result["states"], 2)
        self.assertEqual(
            result["by_state"],
            [
                {"code": "33", "name": "Rio de Janeiro", "teams": 120},
                {"code": "35", "name": "São Paulo", "teams": 160},
            ],
        )
        self.assertEqual(
            result["by_type"],
            [
                {
                    "code": "70",
                    "name": "ESF - EQUIPE DE SAUDE DA FAMILIA",
                    "teams": 180,
                },
                {
                    "code": "71",
                    "name": "ESB - EQUIPE DE SAUDE BUCAL",
                    "teams": 100,
                },
            ],
        )

    def test_rejects_a_total_that_does_not_reconcile(self):
        inconsistent = SNAPSHOT_HTML.replace(b";180;100;280", b";180;100;281")

        with self.assertRaisesRegex(ValueError, "reconcilia"):
            parse_team_snapshot(inconsistent, competence="202609", expected_states=2)

    def test_rejects_incomplete_state_coverage(self):
        with self.assertRaisesRegex(ValueError, "cobertura de UFs"):
            parse_team_snapshot(SNAPSHOT_HTML, competence="202609", expected_states=27)

    def test_calculates_team_rates_with_population(self):
        states = [{"code": "35", "name": "São Paulo", "teams": 160}]
        population = {
            "by_state": [
                {"code": "35", "name": "São Paulo", "population": 2_000_000}
            ]
        }

        result = enrich_teams_with_population(states, population)

        self.assertEqual(result[0]["teams_per_100k"], 8.0)


if __name__ == "__main__":
    unittest.main()
