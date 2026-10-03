import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from cnes_audit.pipeline import build_public_artifacts
from cnes_audit.source import REQUIRED_COLUMNS


class PipelineTest(unittest.TestCase):
    def test_builds_reconciled_public_artifacts_without_sensitive_columns(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.zip"
            output = root / "site" / "data"
            header = ";".join(REQUIRED_COLUMNS)
            row = ";".join(["1", "35", "355030", "5", "M", "-23.5", "-46.6"])
            with ZipFile(source, "w") as archive:
                archive.writestr("cnes_estabelecimentos.csv", f"{header}\n{row}\n")

            build_public_artifacts(
                source_path=source,
                output_directory=output,
                source_url="https://example.test/source.zip",
                obtained_at="2026-10-03T12:00:00Z",
                source_last_modified="2026-10-03T06:00:00Z",
                code_version="test-version",
            )

            dashboard = json.loads((output / "dashboard.json").read_text(encoding="utf-8"))
            audit = json.loads((output / "audit-report.json").read_text(encoding="utf-8"))
            public_text = json.dumps([dashboard, audit]).lower()

            self.assertEqual(dashboard["summary"]["total_records"], 1)
            self.assertEqual(audit["reconciliation"]["rows_read"], 1)
            self.assertEqual(audit["reconciliation"]["rows_aggregated"], 1)
            self.assertEqual(audit["status"], "concluído")
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

