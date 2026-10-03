from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO
from zipfile import ZipFile

REQUIRED_COLUMNS = (
    "CO_CNES",
    "CO_UF",
    "CO_IBGE",
    "TP_UNIDADE",
    "TP_GESTAO",
    "NU_LATITUDE",
    "NU_LONGITUDE",
)


def iter_csv_rows(source: str | Path | BinaryIO) -> Iterator[dict[str, str]]:
    """Lê apenas as colunas contratadas diretamente do primeiro CSV do ZIP."""
    with ZipFile(source) as archive:
        entries = [item for item in archive.infolist() if item.filename.lower().endswith(".csv")]
        if len(entries) != 1:
            raise ValueError(f"esperado um CSV no ZIP; encontrados {len(entries)}")

        with archive.open(entries[0]) as raw:
            with io.TextIOWrapper(raw, encoding="cp1252", newline="") as text:
                reader = csv.DictReader(text, delimiter=";")
                columns = set(reader.fieldnames or [])
                missing = set(REQUIRED_COLUMNS) - columns
                if missing:
                    names = ", ".join(sorted(missing))
                    raise ValueError(f"schema incompatível; colunas ausentes: {names}")

                for row in reader:
                    yield {column: (row.get(column) or "").strip() for column in REQUIRED_COLUMNS}


def zip_entry_metadata(source: str | Path | BinaryIO) -> dict[str, int | str]:
    if hasattr(source, "seek"):
        source.seek(0)
    with ZipFile(source) as archive:
        entries = [item for item in archive.infolist() if item.filename.lower().endswith(".csv")]
        if len(entries) != 1:
            raise ValueError(f"esperado um CSV no ZIP; encontrados {len(entries)}")
        entry = entries[0]
        return {
            "name": Path(entry.filename).name,
            "uncompressed_bytes": entry.file_size,
            "compressed_bytes": entry.compress_size,
        }
