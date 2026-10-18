import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from cnes_audit.pipeline import build_public_artifacts
from cnes_audit.quality import UF_NAMES
from cnes_audit.source import REQUIRED_COLUMNS


class PipelineTest(unittest.TestCase):
    def test_builds_reconciled_public_artifacts_without_sensitive_columns(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.zip"
            beds_source = root / "beds.zip"
            teams_source = root / "teams.html"
            population_source = root / "population.json"
            output = root / "site" / "data"
            header = ";".join(REQUIRED_COLUMNS)
            row = ";".join(["1", "35", "355030", "5", "M", "-23.5", "-46.6"])
            with ZipFile(source, "w") as archive:
                archive.writestr("cnes_estabelecimentos.csv", f"{header}\n{row}\n")
            bed_header = ";".join(
                (
                    "COMP",
                    "UF",
                    "CNES",
                    "LEITOS_EXISTENTES",
                    "LEITOS_SUS",
                    "UTI_TOTAL_EXIST",
                    "UTI_TOTAL_SUS",
                    "NOME_ESTABELECIMENTO",
                    "NU_TELEFONE",
                )
            )
            bed_rows = [
                ";".join(
                    ["202609", abbreviation, f"{index:07d}", "10", "6", "2", "1", "Hospital", "123"]
                )
                for index, abbreviation in enumerate(
                    (
                        "RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI",
                        "CE", "RN", "PB", "PE", "AL", "SE", "BA", "MG", "ES",
                        "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO", "DF",
                    ),
                    start=1,
                )
            ]
            with ZipFile(beds_source, "w") as archive:
                archive.writestr("Leitos_2026.csv", "\n".join([bed_header, *bed_rows]))
            team_rows = [
                f'"{code} {name}";2;1;3'
                for code, name in UF_NAMES.items()
            ]
            teams_source.write_bytes(
                (
                    "<html><body><pre>\n"
                    '"Unidade da Federa&ccedil;&atilde;o";'
                    '"70 ESF - EQUIPE DE SAUDE DA FAMILIA";'
                    '"71 ESB - EQUIPE DE SAUDE BUCAL";"Total"\n'
                    + "\n".join(team_rows)
                    + '\n"Total";54;27;81\n</pre></body></html>'
                ).encode("latin-1")
            )
            population_source.write_text(
                json.dumps(
                    [
                        {
                            "V": "Valor",
                            "D1C": "Unidade da Federação (Código)",
                            "D1N": "Unidade da Federação",
                            "D3C": "Ano (Código)",
                            "D3N": "Ano",
                        },
                        *[
                            {
                                "V": "1000000",
                                "D1C": code,
                                "D1N": name,
                                "D3C": "2026",
                                "D3N": "2026",
                            }
                            for code, name in UF_NAMES.items()
                        ],
                    ]
                ),
                encoding="utf-8",
            )

            build_public_artifacts(
                source_path=source,
                beds_path=beds_source,
                teams_path=teams_source,
                population_path=population_source,
                output_directory=output,
                source_url="https://example.test/source.zip",
                beds_url="https://example.test/beds.zip",
                teams_url="https://example.test/teams",
                population_url="https://example.test/population.json",
                obtained_at="2026-10-03T12:00:00Z",
                source_last_modified="2026-10-03T06:00:00Z",
                beds_last_modified="2026-09-20T20:20:00Z",
                teams_last_modified="não informado",
                population_last_modified="2026-08-28T12:00:00Z",
                teams_competence="202609",
                code_version="test-version",
            )

            dashboard = json.loads((output / "dashboard.json").read_text(encoding="utf-8"))
            audit = json.loads((output / "audit-report.json").read_text(encoding="utf-8"))
            public_text = json.dumps([dashboard, audit]).lower()

            self.assertEqual(dashboard["summary"]["total_records"], 1)
            self.assertEqual(audit["reconciliation"]["rows_read"], 1)
            self.assertEqual(audit["reconciliation"]["rows_aggregated"], 1)
            self.assertEqual(audit["status"], "concluído")
            self.assertEqual(dashboard["summary"]["population_reference_year"], 2026)
            self.assertEqual(dashboard["by_state"][0]["population"], 1_000_000)
            self.assertEqual(dashboard["by_state"][0]["establishments_per_100k"], 0.1)
            self.assertEqual(audit["population_source"]["states"], 27)
            self.assertEqual(audit["population_source"]["reference_year"], 2026)
            self.assertEqual(dashboard["beds"]["summary"]["competence"], "202609")
            self.assertEqual(dashboard["beds"]["summary"]["total_beds"], 270)
            self.assertEqual(dashboard["beds"]["summary"]["sus_beds"], 162)
            self.assertEqual(dashboard["beds"]["by_state"][0]["beds_per_100k"], 1.0)
            self.assertEqual(audit["beds_source"]["rows_selected"], 27)
            self.assertEqual(dashboard["teams"]["summary"]["competence"], "202609")
            self.assertEqual(dashboard["teams"]["summary"]["total_teams"], 81)
            self.assertEqual(dashboard["teams"]["by_state"][0]["teams_per_100k"], 0.3)
            self.assertEqual(audit["teams_source"]["states"], 27)
            for prohibited in (
                "nu_telefone",
                "no_email",
                "no_logradouro",
                "nu_cnpj",
                "nu_latitude",
                "nu_longitude",
                "nome_estabelecimento",
            ):
                self.assertNotIn(prohibited, public_text)


if __name__ == "__main__":
    unittest.main()
