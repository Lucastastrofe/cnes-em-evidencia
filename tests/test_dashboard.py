import ast
import json
import unittest
from pathlib import Path

from cnes_audit.presentation import (
    CONTROL_DESCRIPTIONS,
    describe_controls,
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
        checks = [
            {
                "id": "coordinates_missing",
                "failures": 12_345,
                "failure_rate": 0.123,
            }
        ]

        descriptions = describe_controls(checks)

        self.assertEqual(len(CONTROL_DESCRIPTIONS), 8)
        coordinate_check = descriptions[0]
        self.assertEqual(coordinate_check["Controle"], "Coordenadas preenchidas")
        self.assertEqual(coordinate_check["Resultado"], "Atenção: 12.345 registros (12,3%)")
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

    def test_dashboard_identifies_the_dataset_instead_of_the_local_file(self):
        self.assertIn("Fonte principal", self.source)
        self.assertIn("CNES Estabelecimentos + IBGE", self.source)
        self.assertIn("CNES Leitos + IBGE", self.source)
        self.assertIn("CNES Equipes + IBGE", self.source)
        self.assertIn("CNES Serviços + IBGE", self.source)
        self.assertIn("Painel atualizado", self.source)
        self.assertNotIn("Arquivo informado pela fonte", self.source)
        self.assertNotIn("arquivo local", self.source)

    def test_data_cache_is_invalidated_when_published_files_change(self):
        self.assertIn("def load_data(data_version:", self.source)
        self.assertIn("published_data_version()", self.source)

    def test_timestamps_are_presented_in_brasilia_time(self):
        self.assertEqual(
            format_timestamp("2026-10-05T10:55:49Z"),
            "05/10/2026 às 07:55",
        )

    def test_chart_caption_does_not_repeat_automation_details(self):
        self.assertNotIn("O gráfico é regenerado em cada execução automática.", self.source)

    def test_capacity_chart_keeps_legend_labels_visible(self):
        self.assertIn('title="Composição do total"', self.source)
        self.assertIn('orient="top"', self.source)

    def test_capacity_chart_shows_sus_as_part_of_the_total(self):
        self.assertIn(
            'value_vars=["Leitos destinados ao SUS", "Demais leitos cadastrados"]',
            self.source,
        )
        self.assertIn('text=alt.Text("Percentual SUS:N")', self.source)
        self.assertNotIn('yOffset="Indicador:N"', self.source)

    def test_bed_source_facts_have_clear_labels(self):
        self.assertIn("Competência dos leitos", self.source)
        self.assertIn("CNES Leitos", self.source)
        self.assertIn("Painel atualizado", self.source)

    def test_second_part_compares_cnes_with_population_without_claiming_capacity(self):
        self.assertIn("Parte 2 · Comparação proporcional", self.source)
        self.assertIn("por 100 mil habitantes", self.source)
        self.assertIn("não mede oferta, acesso ou capacidade assistencial", self.source)
        self.assertNotIn("O ETL combina", self.source)

    def test_second_part_is_an_interactive_dashboard_view(self):
        self.assertIn("Compare as UFs", self.source)
        self.assertIn("multiselect", self.source)
        self.assertIn("vazio = Brasil completo", self.source)
        self.assertIn("Recorte da comparação", self.source)
        self.assertIn("Taxa ponderada", self.source)
        self.assertIn("UFs na comparação", self.source)

    def test_each_part_has_its_own_dashboard_navigation(self):
        self.assertIn("st.navigation", self.source)
        self.assertIn('"CNES em Evidência"', self.source)
        self.assertIn('"1 · Qualidade cadastral"', self.source)
        self.assertIn('"2 · Presença por população"', self.source)
        self.assertIn('"3 · Capacidade hospitalar"', self.source)
        self.assertIn('"4 · Equipes de saúde"', self.source)
        self.assertIn('"5 · Serviços cadastrados"', self.source)

    def test_fifth_part_explains_service_records_without_claiming_delivery(self):
        self.assertIn("Parte 5 · Serviços cadastrados", self.source)
        self.assertIn("Registros de serviço/classificação", self.source)
        self.assertIn("não comprova atendimento realizado", self.source)
        self.assertIn("Competência dos serviços", self.source)

    def test_fourth_part_explains_teams_without_claiming_workforce_or_coverage(self):
        self.assertIn("Parte 4 · Equipes de saúde", self.source)
        self.assertIn("Equipes cadastradas", self.source)
        self.assertIn("não representa quantidade de profissionais", self.source)
        self.assertIn("Competência das equipes", self.source)

    def test_third_part_explains_capacity_without_claiming_availability(self):
        self.assertIn("Parte 3 · Capacidade hospitalar", self.source)
        self.assertIn("Leitos existentes", self.source)
        self.assertIn("Leitos destinados ao SUS", self.source)
        self.assertIn("não informa ocupação ou disponibilidade em tempo real", self.source)
        self.assertIn("Competência dos leitos", self.source)

    def test_population_rates_are_calculated_with_precision_but_displayed_as_whole_numbers(self):
        self.assertIn("def format_rate", self.source)
        self.assertIn('format=".0f"', self.source)
        self.assertIn('format="%.0f"', self.source)

    def test_population_panel_explains_its_purpose_and_metrics(self):
        self.assertIn("O que este painel responde", self.source)
        self.assertIn("Registros do CNES", self.source)
        self.assertIn("População estimada", self.source)
        self.assertIn("Uma taxa maior não significa", self.source)
        self.assertIn("não é a média simples", self.source)

    def test_bed_counts_and_rates_are_displayed_without_fractional_units(self):
        self.assertIn('.round().astype(int)', self.source)
        self.assertIn('title="Taxa por 100 mil", format=".0f"', self.source)
        self.assertNotIn('title="Taxa", format=".1f"', self.source)
        self.assertNotIn('NumberColumn(format="%.1f")', self.source)

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
