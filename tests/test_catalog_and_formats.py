import io
import json
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pyarrow.parquet as pq

from cnes_audit.contracts import decode_dashboard, relational_snapshot
from cnes_audit.integrated import build_profile, data_dictionary, public_dataset, public_tables
from cnes_audit.catalog import table_catalog
from cnes_audit.exports import parquet_bytes
from cnes_audit.snapshot_client import obter_snapshot, conectar_somente_leitura


class CatalogAndFormatsTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parents[1] / "data/published"
        self.dashboard = decode_dashboard(json.loads((root / "dashboard.json").read_text(encoding="utf-8")))
        self.profile = build_profile(self.dashboard)
        self.audit = json.loads((root / "audit-report.json").read_text(encoding="utf-8"))

    def test_source_columns_and_layers_are_separate_and_reconcile(self):
        tables = public_tables(self.dashboard, self.profile)
        self.assertEqual(set(tables["fonte_leitos"][0]), {"comp", "uf", "leitos_existentes", "leitos_sus", "uti_total_exist", "uti_total_sus"})
        self.assertEqual(set(tables["fonte_populacao"][0]), {"d1c", "d1n", "d3c", "v"})
        latest = max(row["comp"] for row in tables["fonte_leitos"])
        self.assertEqual(sum(row["leitos_existentes"] for row in tables["fonte_leitos"] if row["comp"] == latest), self.dashboard["beds"]["summary"]["total_beds"])
        self.assertEqual(sum(row["quantidade"] for row in tables["fonte_profissionais"]), self.dashboard["professionals"]["summary"]["total_professionals"])
        catalog = table_catalog(public_dataset(self.dashboard, self.profile, self.audit))
        self.assertEqual({item["tabela"] for item in catalog}, set(tables))
        self.assertEqual(sum(item["camada"] == "fonte_normalizada_agregada" for item in catalog), 5)

    def test_parquet_preserves_columns_types_and_values(self):
        tables = public_tables(self.dashboard, self.profile)
        dictionary = data_dictionary(self.dashboard, self.profile)
        for name, rows in tables.items():
            fields = [item for item in dictionary if item["tabela"] == name]
            restored = pq.read_table(io.BytesIO(parquet_bytes(rows, fields))).to_pylist()
            self.assertEqual(restored, rows)

    def test_verified_sqlite_is_reused_and_cannot_be_modified(self):
        content = relational_snapshot(public_tables(self.dashboard, self.profile), data_dictionary(self.dashboard, self.profile))[1]
        digest = hashlib.sha256(content).hexdigest()
        metadata = {"arquivo": f"snapshots/{digest}.sqlite", "sha256": digest, "bytes": len(content)}
        with tempfile.TemporaryDirectory() as root:
            with patch("cnes_audit.snapshot_client._download", side_effect=[json.dumps(metadata).encode(), content]):
                path, _ = obter_snapshot(Path(root))
            connection = conectar_somente_leitura(path)
            try:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM perfil_uf").fetchone()[0], 27)
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute("DELETE FROM perfil_uf")
            finally:
                connection.close()
            with patch("cnes_audit.snapshot_client._download", return_value=json.dumps(metadata).encode()) as download:
                self.assertEqual(obter_snapshot(Path(root))[0], path)
                self.assertEqual(download.call_count, 1)

    def test_corrupt_snapshot_is_rejected_before_being_saved(self):
        metadata = {"arquivo": "snapshots/" + "a" * 64 + ".sqlite", "sha256": "a" * 64, "bytes": 3}
        with tempfile.TemporaryDirectory() as root:
            with patch("cnes_audit.snapshot_client._download", side_effect=[json.dumps(metadata).encode(), b"bad"]):
                with self.assertRaises(ValueError):
                    obter_snapshot(Path(root))
            self.assertEqual(list(Path(root).glob("*.sqlite")), [])
