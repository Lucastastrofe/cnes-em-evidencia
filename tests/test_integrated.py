import copy
import json
import unittest
import io
import csv
import hashlib
from zipfile import ZipFile
from pathlib import Path

from cnes_audit.integrated import METRICS, build_profile, profile_csv, data_package, public_tables


class IntegratedTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.dashboard = json.loads((self.root / "data/published/dashboard.json").read_text(encoding="utf-8"))

    def test_reconciles_each_indicator_and_geometry(self):
        profile = build_profile(self.dashboard)
        self.assertEqual(len(profile["rows"]), 27)
        geometry = json.loads((self.root / "data/published/uf-boundaries.geojson").read_text(encoding="utf-8"))
        self.assertEqual({row["code"] for row in profile["rows"]}, {str(item["properties"]["codarea"]) for item in geometry["features"]})
        for metric, (_, source) in METRICS.items():
            original = self.dashboard[source]["by_state"] if source else self.dashboard["by_state"]
            self.assertEqual(sum(row[metric] for row in profile["rows"]), sum(row[metric] for row in original))
        self.assertIn("code,name,population", profile_csv(profile["rows"]))

    def test_missing_is_not_zero(self):
        source = copy.deepcopy(self.dashboard)
        missing = source["beds"]["by_state"].pop()
        row = next(row for row in build_profile(source)["rows"] if row["code"] == missing["code"])
        self.assertIsNone(row["beds"])

    def test_full_package_preserves_all_published_tables(self):
        profile = build_profile(self.dashboard)
        audit = json.loads((self.root / "data/published/audit-report.json").read_text(encoding="utf-8"))
        with ZipFile(io.BytesIO(data_package(self.dashboard, profile, audit))) as archive:
            for name, rows in public_tables(self.dashboard, profile).items():
                exported = list(csv.DictReader(io.StringIO(archive.read(f"tabelas/{name}.csv").decode("utf-8-sig"))))
                self.assertEqual(len(exported), len(rows))
                self.assertEqual(set(exported[0]), set(rows[0]))
            self.assertEqual(json.loads(archive.read("auditoria.json")), audit)
            manifest = json.loads(archive.read("manifesto.json"))
            self.assertEqual(manifest["run_id"], profile["run_id"])
            for entry in manifest["files"]:
                self.assertEqual(hashlib.sha256(archive.read(entry["path"])).hexdigest(), entry["sha256"])
            sources = json.loads(archive.read("fontes.json"))
            self.assertEqual(len(sources), 6)
            self.assertTrue(all(source["catalog_url"] and source["sha256"] for source in sources))

    def test_duplicate_and_invalid_counts_fail(self):
        source = copy.deepcopy(self.dashboard)
        source["beds"]["by_state"].append(source["beds"]["by_state"][0])
        with self.assertRaises(ValueError):
            build_profile(source)
        self.dashboard["by_state"][0]["records"] = 0.5
        with self.assertRaises(ValueError):
            build_profile(self.dashboard)
