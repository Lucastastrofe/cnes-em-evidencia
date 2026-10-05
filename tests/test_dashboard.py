import ast
import json
import unittest
from pathlib import Path

from cnes_audit.presentation import (
    describe_controls,
    format_source_date,
    format_timestamp,
    interpret_materiality,
    management_without_information,
    split_checks,
)


class DashboardContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parents[1]
        cls.source = (cls.root / "streamlit_app.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.public_data = json.dumps(
            [
                json.loads(
                    (cls.root / "data" / "published" / "dashboard.json").read_text(
                        encoding="utf-8"
                    )
                ),
                json.loads(
                    (cls.root / "data" / "published" / "audit-report.json").read_text(
                        encoding="utf-8"
                    )
                ),
            ]
        ).lower()

    def test_entrypoint_is_a_single_streamlit_dashboard(self):
        calls = {
            node.func.attr
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("set_page_config", calls)
        self.assertIn("metric", calls)
        self.assertIn("bar_chart", calls)
        self.assertIn("dataframe", calls)
        self.assertIn("selectbox", calls)

    def test_static_site_was_removed(self):
        self.assertFalse((self.root / "site" / "index.html").exists())

    def test_approved_controls_are_separated_from_findings(self):
        checks = [
            {
                "label": "Identificador preenchido",
                "dimension": "completude",
                "status": "aprovado",
                "failures": 0,
                "failure_rate": 0.0,
            },
            {
                "label": "Coordenadas preenchidas",
                "dimension": "completude",
                "status": "observação",
                "failures": 12,
                "failure_rate": 0.12,
            },
        ]

        approved, findings = split_checks(checks)

        self.assertEqual(approved, [
            {"Regra": "Identificador preenchido", "Dimensão": "Completude", "Resultado": "Aprovado"}
        ])
        self.assertEqual(findings[0]["Ocorrências"], 12)
        self.assertEqual(findings[0]["Taxa"], 0.12)

    def test_coordinate_gap_is_interpreted_by_analytical_use(self):
        interpretation = interpret_materiality("coordinates_missing", 0.092765)

        self.assertEqual(interpretation["classification"], "Atenção para uso geográfico")
        self.assertIn("mapas", interpretation["affected_use"])
        self.assertIn("UF", interpretation["unaffected_use"])

    def test_controls_are_explained_and_the_finding_is_named(self):
        checks = json.loads(
            (self.root / "data" / "published" / "dashboard.json").read_text(encoding="utf-8")
        )["checks"]

        descriptions = describe_controls(checks)

        self.assertEqual(len(descriptions), 8)
        coordinate_check = next(
            item for item in descriptions if item["Controle"] == "Coordenadas preenchidas"
        )
        self.assertEqual(coordinate_check["Resultado"], "Atenção: 59.184 registros (9,3%)")
        self.assertIn("latitude e longitude", coordinate_check["O que verifica"])

    def test_management_without_information_is_visible_even_when_rate_is_small(self):
        summary = management_without_information(
            [
                {"code": "M", "records": 900},
                {"code": "S", "records": 1},
            ],
            total_records=1000,
        )

        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["rate"], 0.001)

    def test_dashboard_distinguishes_source_date_from_daily_check(self):
        self.assertIn("Última verificação automática", self.source)
        self.assertIn("Data informada pela fonte", self.source)

    def test_data_cache_is_invalidated_when_published_files_change(self):
        self.assertIn("def load_data(data_version:", self.source)
        self.assertIn("published_data_version()", self.source)

    def test_timestamps_are_presented_in_brasilia_time(self):
        self.assertEqual(
            format_timestamp("2026-10-05T10:55:49Z"),
            "05/10/2026 às 07:55 (horário de Brasília)",
        )
        self.assertEqual(
            format_source_date("Sat, 03 Oct 2026 06:00:25 GMT"),
            "03/10/2026 às 03:00 (horário de Brasília)",
        )

    def test_published_data_excludes_source_columns_outside_the_contract(self):
        for prohibited in (
            "nu_telefone",
            "no_email",
            "no_logradouro",
            "nu_endereco",
            "no_bairro",
            "co_cep",
            "nu_cnpj",
            "nu_latitude",
            "nu_longitude",
            "no_razao_social",
            "no_fantasia",
        ):
            self.assertNotIn(prohibited, self.public_data)


if __name__ == "__main__":
    unittest.main()
