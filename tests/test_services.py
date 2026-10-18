import unittest

from cnes_audit.services import (
    enrich_services_with_population,
    extract_latest_service_file,
    parse_service_snapshot,
)


DEFINITION_HTML = b"""
<option value=\"srbr2608.dbf\">Ago/2026</option>
<option value=\"srbr2609.dbf\">Set/2026</option>
"""

SNAPSHOT_HTML = """
<html><body><pre>
\"Classifica&ccedil;&atilde;o do Servi&ccedil;o\";\"RO\";\"SP\";\"Total\"
\"103001 103 SERVICO DE URGENCIA / 001 AMBULANCIA DE TRANSPORTE\";2;3;5
\"105002 105 SERVICO DE ATENCAO DOMICILIAR / 002 ATENDIMENTO DOMICILIAR\";1;-;1
\"Total\";3;3;6
</pre></body></html>
""".encode("latin-1")


class ServicesTest(unittest.TestCase):
    def test_selects_latest_service_competence(self):
        filename, competence = extract_latest_service_file(DEFINITION_HTML)

        self.assertEqual(filename, "srbr2609.dbf")
        self.assertEqual(competence, "202609")

    def test_parses_and_reconciles_services_by_state_and_classification(self):
        result = parse_service_snapshot(
            SNAPSHOT_HTML,
            competence="202609",
            expected_states=2,
        )

        self.assertEqual(result["total_service_records"], 6)
        self.assertEqual(result["service_classifications"], 2)
        self.assertEqual(
            result["by_state"],
            [
                {"code": "11", "name": "Rondônia", "service_records": 3},
                {"code": "35", "name": "São Paulo", "service_records": 3},
            ],
        )
        self.assertEqual(result["by_classification"][0]["classification_code"], "103001")
        self.assertEqual(result["by_classification"][0]["service_code"], "103")
        self.assertEqual(result["by_classification"][0]["service_records"], 5)

    def test_rejects_a_national_total_that_does_not_reconcile(self):
        inconsistent = SNAPSHOT_HTML.replace(b'\"Total\";3;3;6', b'\"Total\";3;3;7')

        with self.assertRaisesRegex(ValueError, "total nacional"):
            parse_service_snapshot(inconsistent, competence="202609", expected_states=2)

    def test_rejects_missing_states(self):
        with self.assertRaisesRegex(ValueError, "cobertura de UFs"):
            parse_service_snapshot(SNAPSHOT_HTML, competence="202609", expected_states=27)

    def test_calculates_service_record_rates_with_population(self):
        states = [{"code": "35", "name": "São Paulo", "service_records": 250}]
        population = {
            "by_state": [{"code": "35", "name": "São Paulo", "population": 5_000_000}]
        }

        result = enrich_services_with_population(states, population)

        self.assertEqual(result[0]["service_records_per_100k"], 5.0)


if __name__ == "__main__":
    unittest.main()
