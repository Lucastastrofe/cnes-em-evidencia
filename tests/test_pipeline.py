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
            population_source = root / "population.json"
            output = root / "site" / "data"
            header = ";".join(REQUIRED_COLUMNS)
            row = ";".join(["1", "35", "355030", "5", "M", "-23.5", "-46.6"])
            with ZipFile(source, "w") as archive:
                archive.writestr("cnes_estabelecimentos.csv", f"{header}\n{row}\n")
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
                population_path=population_source,
                output_directory=output,
                source_url="https://example.test/source.zip",
                population_url="https://example.test/population.json",
                obtained_at="2026-10-03T12:00:00Z",
                source_last_modified="2026-10-03T06:00:00Z",
                population_last_modified="2026-08-28T12:00:00Z",
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
            for prohibited in (
                "nu_telefone",
                "no_email",
                "no_logradouro",
                "nu_cnpj",
                "nu_latitude",
                "nu_longitude",
            ):
                self.assertNotIn(prohibited, public_text)


if __name__ == "__main__":
    unittest.main()
