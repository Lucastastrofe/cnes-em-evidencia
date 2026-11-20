import csv
import io
import json
import tempfile
import unittest
import sqlite3
from pathlib import Path

from cnes_audit.integrated import build_profile, data_dictionary, public_tables
from cnes_audit.publish import build_api
from cnes_audit.contracts import decode_dashboard, encode_dashboard, encode_profile, decode_profile
from cnes_audit.contracts import relational_snapshot


class PublicContractTest(unittest.TestCase):
    def setUp(self):
        self.data = Path(__file__).parents[1] / "data/published"
        self.dashboard = decode_dashboard(json.loads((self.data / "dashboard.json").read_text(encoding="utf-8")))
        self.profile = build_profile(self.dashboard)

    def test_migration_is_lossless_and_idempotent(self):
        canonical = encode_dashboard(self.dashboard)
        self.assertEqual(decode_dashboard(canonical), self.dashboard)
        self.assertEqual(encode_dashboard(canonical), canonical)
        self.assertEqual(decode_profile(encode_profile(self.profile))["rows"], self.profile["rows"])
        self.assertIn("co_uf", canonical["by_state"][0])
        self.assertIn("leitos_existentes", canonical["beds"]["by_state"][0])

    def test_relational_snapshot_has_types_keys_and_same_totals(self):
        tables = public_tables(self.dashboard, self.profile)
        _, content = relational_snapshot(tables, data_dictionary(self.dashboard, self.profile))
        connection = sqlite3.connect(":memory:")
        try:
            connection.deserialize(content)
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(connection.execute("SELECT SUM(leitos_existentes) FROM leitos_uf").fetchone()[0], self.dashboard["beds"]["summary"]["total_beds"])
            self.assertEqual(connection.execute("SELECT typeof(co_uf) FROM perfil_uf LIMIT 1").fetchone()[0], "text")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM perfil_uf").fetchone()[0], 27)
        finally:
            connection.close()

    def test_every_published_column_has_lineage_and_a_type(self):
        tables = public_tables(self.dashboard, self.profile)
        dictionary = data_dictionary(self.dashboard, self.profile)
        documented = {(row["tabela"], row["coluna"]) for row in dictionary}
        actual = {(table, column) for table, rows in tables.items() for column in rows[0]}
        self.assertEqual(actual, documented)
        self.assertEqual(len(actual), len(dictionary))
        for table, rows in tables.items():
            for row in rows:
                if "co_uf" in row:
                    self.assertRegex(row["co_uf"], r"^\d{2}$")
        self.assertIn("leitos_existentes", tables["leitos_uf"][0])
        self.assertNotIn("beds", tables["leitos_uf"][0])
        self.assertEqual(sum(row["leitos_existentes"] for row in tables["leitos_uf"]), self.dashboard["beds"]["summary"]["total_beds"])

    def test_api_files_use_same_rows_as_downloads_and_partition_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = build_api(self.data, Path(temporary))
            root = Path(temporary) / "api/v1"
            for table, rows in dataset["tabelas"].items():
                payload = json.loads((root / f"tabelas/{table}.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["dados"], rows)
                exported = list(csv.DictReader(io.StringIO((root / f"csv/{table}.csv").read_text(encoding="utf-8-sig"))))
                self.assertEqual(len(exported), len(rows))
                self.assertEqual(set(exported[0]), set(rows[0]))
                if "co_uf" in rows[0]:
                    for code in {row["co_uf"] for row in rows}:
                        subset = json.loads((root / f"tabelas/{table}/ufs/{code}.json").read_text(encoding="utf-8"))["dados"]
                        self.assertEqual(subset, [row for row in rows if row["co_uf"] == code])
            self.assertEqual(len(json.loads((root / "ufs.json").read_text(encoding="utf-8"))["dados"]), 27)
            self.assertEqual(dataset["id_execucao"], self.dashboard["metadata"]["run_id"])
