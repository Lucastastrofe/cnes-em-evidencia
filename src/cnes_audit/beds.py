from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO
from zipfile import ZipFile

from cnes_audit.quality import UF_NAMES

REQUIRED_BED_COLUMNS = (
    "COMP",
    "UF",
    "CNES",
    "LEITOS_EXISTENTES",
    "LEITOS_SUS",
    "UTI_TOTAL_EXIST",
    "UTI_TOTAL_SUS",
)

UF_CODES = {
    "RO": "11",
    "AC": "12",
    "AM": "13",
    "RR": "14",
    "PA": "15",
    "AP": "16",
    "TO": "17",
    "MA": "21",
    "PI": "22",
    "CE": "23",
    "RN": "24",
    "PB": "25",
    "PE": "26",
    "AL": "27",
    "SE": "28",
    "BA": "29",
    "MG": "31",
    "ES": "32",
    "RJ": "33",
    "SP": "35",
    "PR": "41",
    "SC": "42",
    "RS": "43",
    "MS": "50",
    "MT": "51",
    "GO": "52",
    "DF": "53",
}


def iter_bed_rows(source: str | Path | BinaryIO) -> Iterator[dict[str, str]]:
    """Lê somente as colunas necessárias diretamente do CSV compactado."""
    if hasattr(source, "seek"):
        source.seek(0)
    with ZipFile(source) as archive:
        entries = [
            item for item in archive.infolist() if item.filename.lower().endswith(".csv")
        ]
        if len(entries) != 1:
            raise ValueError(f"esperado um CSV no ZIP de leitos; encontrados {len(entries)}")

        with archive.open(entries[0]) as raw:
            with io.TextIOWrapper(raw, encoding="cp1252", newline="") as text:
                reader = csv.DictReader(text, delimiter=";")
                columns = {str(column).strip('"') for column in (reader.fieldnames or [])}
                missing = set(REQUIRED_BED_COLUMNS) - columns
                if missing:
                    names = ", ".join(sorted(missing))
                    raise ValueError(f"schema de leitos incompatível; colunas ausentes: {names}")

                for row in reader:
                    yield {
                        column: (row.get(column) or "").strip()
                        for column in REQUIRED_BED_COLUMNS
                    }


def _bed_count(row: dict[str, str], column: str) -> int:
    try:
        value = int(row[column])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"quantidade de leitos inválida em {column}") from error
    if value < 0:
        raise ValueError(f"quantidade de leitos inválida em {column}")
    return value


def aggregate_latest_bed_capacity(
    source: str | Path | BinaryIO,
    expected_states: int = 27,
) -> dict[str, Any]:
    latest_competence = ""
    rows_read = 0
    selected: list[dict[str, str]] = []

    for row in iter_bed_rows(source):
        rows_read += 1
        competence = row["COMP"]
        if len(competence) != 6 or not competence.isdigit() or competence[4:] not in {
            f"{month:02d}" for month in range(1, 13)
        }:
            raise ValueError(f"competência inválida na fonte de leitos: {competence or 'vazia'}")
        if competence > latest_competence:
            latest_competence = competence
            selected = [row]
        elif competence == latest_competence:
            selected.append(row)

    if not selected:
        raise ValueError("fonte de leitos vazia")

    state_totals: dict[str, dict[str, int]] = {}
    seen_cnes: set[str] = set()
    for row in selected:
        state_abbreviation = row["UF"].upper()
        if state_abbreviation not in UF_CODES:
            raise ValueError(f"UF inválida na fonte de leitos: {state_abbreviation or 'vazia'}")
        cnes = row["CNES"]
        if not cnes:
            raise ValueError("CNES vazio na fonte de leitos")
        if cnes in seen_cnes:
            raise ValueError(f"CNES repetido na competência {latest_competence}: {cnes}")
        seen_cnes.add(cnes)

        beds = _bed_count(row, "LEITOS_EXISTENTES")
        sus_beds = _bed_count(row, "LEITOS_SUS")
        uti_beds = _bed_count(row, "UTI_TOTAL_EXIST")
        uti_sus_beds = _bed_count(row, "UTI_TOTAL_SUS")
        if sus_beds > beds:
            raise ValueError(f"leitos SUS maior que leitos existentes no CNES {cnes}")
        if uti_sus_beds > uti_beds:
            raise ValueError(f"leitos de UTI SUS maior que UTI existente no CNES {cnes}")

        totals = state_totals.setdefault(
            state_abbreviation,
            {"beds": 0, "sus_beds": 0, "uti_beds": 0, "uti_sus_beds": 0},
        )
        totals["beds"] += beds
        totals["sus_beds"] += sus_beds
        totals["uti_beds"] += uti_beds
        totals["uti_sus_beds"] += uti_sus_beds

    if len(state_totals) != expected_states:
        raise ValueError(
            "cobertura de UFs incompatível na fonte de leitos: "
            f"esperadas {expected_states}, recebidas {len(state_totals)}"
        )

    by_state = [
        {
            "code": code,
            "name": UF_NAMES[code],
            **state_totals[abbreviation],
        }
        for abbreviation, code in UF_CODES.items()
        if abbreviation in state_totals
    ]
    by_state.sort(key=lambda item: str(item["name"]))

    return {
        "competence": latest_competence,
        "rows_read": rows_read,
        "rows_selected": len(selected),
        "total_beds": sum(int(item["beds"]) for item in by_state),
        "sus_beds": sum(int(item["sus_beds"]) for item in by_state),
        "uti_beds": sum(int(item["uti_beds"]) for item in by_state),
        "uti_sus_beds": sum(int(item["uti_sus_beds"]) for item in by_state),
        "by_state": by_state,
    }


def enrich_beds_with_population(
    bed_states: list[dict[str, Any]], population: dict[str, Any]
) -> list[dict[str, Any]]:
    population_by_code = {
        str(item["code"]): int(item["population"]) for item in population["by_state"]
    }
    enriched: list[dict[str, Any]] = []
    for state in bed_states:
        code = str(state["code"])
        if code not in population_by_code:
            raise ValueError(f"UF {code} sem população para calcular a taxa de leitos")
        inhabitants = population_by_code[code]
        enriched.append(
            {
                **state,
                "population": inhabitants,
                "beds_per_100k": round(int(state["beds"]) / inhabitants * 100_000, 2),
                "sus_beds_per_100k": round(
                    int(state["sus_beds"]) / inhabitants * 100_000, 2
                ),
            }
        )
    return enriched
