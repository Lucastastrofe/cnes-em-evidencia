import unittest

from cnes_audit.quality import audit_rows


def sample_rows():
    return [
        {
            "CO_CNES": "0000001",
            "CO_UF": "35",
            "CO_IBGE": "355030",
            "TP_UNIDADE": "5",
            "TP_GESTAO": "M",
            "NU_LATITUDE": "-23.55",
            "NU_LONGITUDE": "-46.63",
        },
        {
            "CO_CNES": "0000002",
            "CO_UF": "35",
            "CO_IBGE": "355030",
            "TP_UNIDADE": "5",
            "TP_GESTAO": "M",
            "NU_LATITUDE": "",
            "NU_LONGITUDE": "",
        },
        {
            "CO_CNES": "0000002",
            "CO_UF": "99",
            "CO_IBGE": "ABC",
            "TP_UNIDADE": "",
            "TP_GESTAO": "",
            "NU_LATITUDE": "-95",
            "NU_LONGITUDE": "200",
        },
        {
            "CO_CNES": "",
            "CO_UF": "33",
            "CO_IBGE": "330455",
            "TP_UNIDADE": "7",
            "TP_GESTAO": "E",
            "NU_LATITUDE": "-22.91",
            "NU_LONGITUDE": "-43.17",
        },
    ]


class QualityTest(unittest.TestCase):
    def test_audit_reconciles_rows_and_exposes_quality_failures(self):
        result = audit_rows(sample_rows())

        self.assertEqual(result["summary"]["total_records"], 4)
        self.assertEqual(sum(item["records"] for item in result["by_state"]), 4)
        self.assertEqual(result["summary"]["states_with_records"], 2)

        checks = {item["id"]: item for item in result["checks"]}
        self.assertEqual(checks["cnes_missing"]["failures"], 1)
        self.assertEqual(checks["cnes_duplicate"]["failures"], 1)
        self.assertEqual(checks["uf_invalid"]["failures"], 1)
        self.assertEqual(checks["municipality_code_invalid"]["failures"], 1)
        self.assertEqual(checks["coordinates_missing"]["failures"], 1)
        self.assertEqual(checks["coordinates_out_of_range"]["failures"], 1)

    def test_state_filter_preserves_invalid_records_without_inventing_a_state(self):
        result = audit_rows(sample_rows())

        states = {item["code"]: item for item in result["by_state"]}
        self.assertEqual(states["35"]["name"], "São Paulo")
        self.assertEqual(states["35"]["records"], 2)
        self.assertEqual(states["invalid"]["records"], 1)

    def test_public_payload_contains_no_record_level_or_prohibited_fields(self):
        result = audit_rows(sample_rows())
        serialized = str(result).lower()

        prohibited = (
            "telefone",
            "email",
            "logradouro",
            "endereco",
            "bairro",
            "cep",
            "cnpj",
            "latitude",
            "longitude",
            "razao_social",
            "fantasia",
        )
        self.assertTrue(all(field not in serialized for field in prohibited))
        self.assertNotIn("rows", result)


if __name__ == "__main__":
    unittest.main()
