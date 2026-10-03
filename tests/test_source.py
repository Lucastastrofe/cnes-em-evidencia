from io import BytesIO
import unittest
from zipfile import ZipFile

from cnes_audit.source import REQUIRED_COLUMNS, iter_csv_rows


def make_zip(header: str, rows: list[str], encoding: str = "cp1252") -> BytesIO:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "cnes_estabelecimentos.csv",
            "\n".join([header, *rows]).encode(encoding),
        )
    buffer.seek(0)
    return buffer


class SourceTest(unittest.TestCase):
    def test_reads_semicolon_csv_directly_from_zip(self):
        header = ";".join(REQUIRED_COLUMNS)
        values = ["1", "35", "355030", "5", "M", "-23.5", "-46.6"]

        rows = list(iter_csv_rows(make_zip(header, [";".join(values)])))

        self.assertEqual(rows, [dict(zip(REQUIRED_COLUMNS, values, strict=True))])

    def test_rejects_incompatible_schema_before_publication(self):
        incomplete_header = ";".join(REQUIRED_COLUMNS[:-1])

        with self.assertRaisesRegex(ValueError, "schema incompatível"):
            list(iter_csv_rows(make_zip(incomplete_header, [])))

    def test_accepts_windows_encoding_used_by_the_source(self):
        header = ";".join([*REQUIRED_COLUMNS, "NO_FANTASIA"])
        values = ["1", "35", "355030", "5", "M", "-23.5", "-46.6", "Clínica São João"]

        rows = list(iter_csv_rows(make_zip(header, [";".join(values)])))

        self.assertEqual(rows[0]["CO_CNES"], "1")


if __name__ == "__main__":
    unittest.main()
