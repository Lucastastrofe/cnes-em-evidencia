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
    history = aggregate_bed_history(source, expected_states=expected_states)
    return latest_bed_capacity(history)


def aggregate_bed_history(
    source: str | Path | BinaryIO,
    expected_states: int = 27,
) -> dict[str, Any]:
    rows_read = 0
    rows_by_competence: dict[str, int] = {}
    state_totals_by_competence: dict[str, dict[str, dict[str, int]]] = {}
    seen_cnes_by_competence: dict[str, set[str]] = {}

    for row in iter_bed_rows(source):
        rows_read += 1
        competence = row["COMP"]
        if len(competence) != 6 or not competence.isdigit() or competence[4:] not in {
            f"{month:02d}" for month in range(1, 13)
        }:
            raise ValueError(
                f"competência inválida na fonte de leitos: {competence or 'vazia'}"
            )
        state_abbreviation = row["UF"].upper()
        if state_abbreviation not in UF_CODES:
            raise ValueError(f"UF inválida na fonte de leitos: {state_abbreviation or 'vazia'}")
        cnes = row["CNES"]
        if not cnes:
            raise ValueError("CNES vazio na fonte de leitos")
        seen_cnes = seen_cnes_by_competence.setdefault(competence, set())
        if cnes in seen_cnes:
            raise ValueError(f"CNES repetido na competência {competence}: {cnes}")
        seen_cnes.add(cnes)

        beds = _bed_count(row, "LEITOS_EXISTENTES")
        sus_beds = _bed_count(row, "LEITOS_SUS")
        uti_beds = _bed_count(row, "UTI_TOTAL_EXIST")
        uti_sus_beds = _bed_count(row, "UTI_TOTAL_SUS")
        if sus_beds > beds:
            raise ValueError(f"leitos SUS maior que leitos existentes no CNES {cnes}")
        if uti_sus_beds > uti_beds:
            raise ValueError(f"leitos de UTI SUS maior que UTI existente no CNES {cnes}")

        rows_by_competence[competence] = rows_by_competence.get(competence, 0) + 1
        state_totals = state_totals_by_competence.setdefault(competence, {})
        totals = state_totals.setdefault(
            state_abbreviation,
            {"beds": 0, "sus_beds": 0, "uti_beds": 0, "uti_sus_beds": 0},
        )
        totals["beds"] += beds
        totals["sus_beds"] += sus_beds
        totals["uti_beds"] += uti_beds
        totals["uti_sus_beds"] += uti_sus_beds

    if not state_totals_by_competence:
        raise ValueError("fonte de leitos vazia")

    national: list[dict[str, Any]] = []
    by_state: list[dict[str, Any]] = []
    for competence in sorted(state_totals_by_competence):
        state_totals = state_totals_by_competence[competence]
        if len(state_totals) != expected_states:
            raise ValueError(
                "cobertura de UFs incompatível na fonte de leitos para a competência "
                f"{competence}: esperadas {expected_states}, recebidas {len(state_totals)}"
            )
        competence_states = [
            {
                "competence": competence,
                "code": code,
                "name": UF_NAMES[code],
                **state_totals[abbreviation],
            }
            for abbreviation, code in UF_CODES.items()
            if abbreviation in state_totals
        ]
        competence_states.sort(key=lambda item: str(item["name"]))
        by_state.extend(competence_states)
        national.append(
            {
                "competence": competence,
                "rows_selected": rows_by_competence[competence],
                "beds": sum(int(item["beds"]) for item in competence_states),
                "sus_beds": sum(int(item["sus_beds"]) for item in competence_states),
                "uti_beds": sum(int(item["uti_beds"]) for item in competence_states),
                "uti_sus_beds": sum(
                    int(item["uti_sus_beds"]) for item in competence_states
                ),
            }
        )

    competences = [item["competence"] for item in national]
    return {
        "rows_read": rows_read,
        "competences": len(competences),
        "first_competence": competences[0],
        "latest_competence": competences[-1],
        "national": national,
        "by_state": by_state,
    }


def latest_bed_capacity(history: dict[str, Any]) -> dict[str, Any]:
    latest_competence = str(history["latest_competence"])
    latest_national = next(
        item for item in history["national"] if item["competence"] == latest_competence
    )
    latest_states = [
        {key: value for key, value in item.items() if key != "competence"}
        for item in history["by_state"]
        if item["competence"] == latest_competence
    ]
    return {
        "competence": latest_competence,
        "rows_read": int(history["rows_read"]),
        "rows_selected": int(latest_national["rows_selected"]),
        "total_beds": int(latest_national["beds"]),
        "sus_beds": int(latest_national["sus_beds"]),
        "uti_beds": int(latest_national["uti_beds"]),
        "uti_sus_beds": int(latest_national["uti_sus_beds"]),
        "by_state": latest_states,
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


def enrich_bed_history_with_population(
    history: dict[str, Any], population: dict[str, Any]
) -> dict[str, Any]:
    total_population = int(population["total_population"])
    national = []
    for item in history["national"]:
        national.append(
            {
                **item,
                "population": total_population,
                "beds_per_100k": round(int(item["beds"]) / total_population * 100_000, 2),
                "sus_beds_per_100k": round(
                    int(item["sus_beds"]) / total_population * 100_000, 2
                ),
                "uti_beds_per_100k": round(
                    int(item["uti_beds"]) / total_population * 100_000, 2
                ),
                "uti_sus_beds_per_100k": round(
                    int(item["uti_sus_beds"]) / total_population * 100_000, 2
                ),
            }
        )

    state_rows = []
    for item in history["by_state"]:
        enriched = enrich_beds_with_population([item], population)[0]
        inhabitants = int(enriched["population"])
        state_rows.append(
            {
                **enriched,
                "uti_beds_per_100k": round(
                    int(item["uti_beds"]) / inhabitants * 100_000, 2
                ),
                "uti_sus_beds_per_100k": round(
                    int(item["uti_sus_beds"]) / inhabitants * 100_000, 2
                ),
            }
        )

    return {
        "summary": {
            "competences": int(history["competences"]),
            "first_competence": str(history["first_competence"]),
            "latest_competence": str(history["latest_competence"]),
            "population_reference_year": int(population["reference_year"]),
        },
        "national": national,
        "by_state": state_rows,
    }
