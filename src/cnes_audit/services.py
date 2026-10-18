from __future__ import annotations

import csv
import html
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from io import StringIO
from pathlib import Path
from typing import BinaryIO

from cnes_audit.quality import UF_NAMES


SERVICE_DEFINITION_URL = (
    "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/servc2br.def"
)
SERVICE_QUERY_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/servc2br.def"

UF_CODES_BY_ABBREVIATION = dict(
    zip(
        (
            "RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE",
            "RN", "PB", "PE", "AL", "SE", "BA", "MG", "ES", "RJ", "SP",
            "PR", "SC", "RS", "MS", "MT", "GO", "DF",
        ),
        UF_NAMES,
        strict=True,
    )
)


def _read_bytes(source: Path | BinaryIO | bytes) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, Path):
        return source.read_bytes()
    source.seek(0)
    return source.read()


def _competence_from_filename(filename: str) -> str:
    match = re.fullmatch(r"srbr(\d{2})(\d{2})\.dbf", filename, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"arquivo de serviços fora do padrão esperado: {filename}")
    return f"20{match.group(1)}{match.group(2)}"


def extract_latest_service_file(source: Path | BinaryIO | bytes) -> tuple[str, str]:
    document = _read_bytes(source).decode("latin-1")
    filenames = set(re.findall(r"srbr\d{4}\.dbf", document, flags=re.IGNORECASE))
    if not filenames:
        raise ValueError("a página do TabNet não informou competências de serviços")
    latest = max(filenames, key=_competence_from_filename).lower()
    return latest, _competence_from_filename(latest)


def _service_query_payload(filename: str) -> bytes:
    fields = {
        "Linha": "Classificação_do_Serviço",
        "Coluna": "Unidade_da_Federação",
        "Incremento": "Quantidade",
        "Arquivos": filename,
        "formato": "prn",
        "mostre": "Mostra",
    }
    return urllib.parse.urlencode(fields, encoding="latin-1").encode("ascii")


def download_service_snapshot(
    destination: Path,
    definition_url: str = SERVICE_DEFINITION_URL,
    query_url: str = SERVICE_QUERY_URL,
    attempts: int = 3,
) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            definition_request = urllib.request.Request(
                definition_url,
                headers={"User-Agent": "cnes-em-evidencia/0.1"},
            )
            with urllib.request.urlopen(definition_request, timeout=120) as response:  # noqa: S310
                definition = response.read()
            filename, competence = extract_latest_service_file(definition)

            query_request = urllib.request.Request(
                query_url,
                data=_service_query_payload(filename),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "cnes-em-evidencia/0.1",
                },
            )
            with urllib.request.urlopen(query_request, timeout=120) as response:  # noqa: S310
                with temporary.open("wb") as target:
                    shutil.copyfileobj(response, target)
                headers = {
                    "last_modified": response.headers.get("Last-Modified", "não informado"),
                    "etag": response.headers.get("ETag", "não informado").strip('"'),
                }

            parse_service_snapshot(temporary, competence=competence)
            os.replace(temporary, destination)
            return {**headers, "competence": competence, "filename": filename}
        except (OSError, urllib.error.URLError, ValueError) as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(
        f"não foi possível obter os serviços após {attempts} tentativas"
    ) from last_error


def _count(value: str) -> int:
    normalized = value.strip().replace(".", "")
    if normalized in {"", "-"}:
        return 0
    try:
        result = int(normalized)
    except ValueError as error:
        raise ValueError(f"quantidade de serviços inválida: {value}") from error
    if result < 0:
        raise ValueError(f"quantidade de serviços inválida: {value}")
    return result


def _classification(label: str) -> dict[str, str]:
    match = re.match(r"(\d{6})\s+(\d{3})\s+(.+?)\s+/\s+(\d{3})\s+(.+)", label.strip())
    if match is None:
        raise ValueError(f"classificação de serviço fora do padrão esperado: {label}")
    if match.group(1) != f"{match.group(2)}{match.group(4)}":
        raise ValueError(f"código de classificação inconsistente: {label}")
    return {
        "classification_code": match.group(1),
        "service_code": match.group(2),
        "service_name": " ".join(match.group(3).split()),
        "classification_name": " ".join(match.group(5).split()),
    }


def parse_service_snapshot(
    source: Path | BinaryIO | bytes,
    competence: str,
    expected_states: int = 27,
) -> dict:
    document = _read_bytes(source).decode("latin-1")
    preformatted = re.search(r"<pre[^>]*>(.*?)</pre>", document, flags=re.I | re.S)
    if preformatted is None:
        raise ValueError("a resposta do TabNet não contém a tabela de serviços")

    table = html.unescape(preformatted.group(1)).strip()
    rows = [row for row in csv.reader(StringIO(table), delimiter=";") if row]
    if len(rows) < 3:
        raise ValueError("a resposta do TabNet não contém linhas suficientes")

    header = rows[0]
    if header[-1].strip() != "Total":
        raise ValueError("a tabela de serviços não possui a coluna Total")
    abbreviations = [value.strip() for value in header[1:-1]]
    if len(abbreviations) != expected_states or len(set(abbreviations)) != expected_states:
        raise ValueError(
            f"cobertura de UFs incompatível: esperado {expected_states}, recebido {len(abbreviations)}"
        )
    if any(value not in UF_CODES_BY_ABBREVIATION for value in abbreviations):
        raise ValueError("a tabela de serviços possui uma UF inválida")

    total_positions = [
        index
        for index, row in enumerate(rows[1:], 1)
        if row[0].strip() == "Total"
    ]
    if len(total_positions) != 1:
        raise ValueError("a tabela de serviços não possui total nacional")
    total_position = total_positions[0]
    national_row = rows[total_position]
    if len(national_row) != len(header):
        raise ValueError("o total nacional possui colunas incompatíveis")

    state_totals = [_count(value) for value in national_row[1:-1]]
    national_total = _count(national_row[-1])
    if sum(state_totals) != national_total:
        raise ValueError("o total nacional não reconcilia com as UFs")

    by_classification: list[dict[str, str | int]] = []
    by_state_classification: list[dict[str, str | int]] = []
    observed_state_totals = [0] * len(abbreviations)
    for row in rows[1:total_position]:
        if len(row) != len(header):
            raise ValueError("uma linha de classificação possui colunas incompatíveis")
        definition = _classification(row[0])
        counts = [_count(value) for value in row[1:-1]]
        classification_total = _count(row[-1])
        if sum(counts) != classification_total:
            raise ValueError(
                f"a classificação {definition['classification_code']} não reconcilia com as UFs"
            )
        for position, count in enumerate(counts):
            observed_state_totals[position] += count
            if count > 0:
                abbreviation = abbreviations[position]
                code = UF_CODES_BY_ABBREVIATION[abbreviation]
                by_state_classification.append(
                    {
                        "state_code": code,
                        "state_name": UF_NAMES[code],
                        **definition,
                        "service_records": count,
                    }
                )
        by_classification.append({**definition, "service_records": classification_total})

    if observed_state_totals != state_totals:
        raise ValueError("as classificações não reconciliam com os totais das UFs")
    if sum(int(item["service_records"]) for item in by_classification) != national_total:
        raise ValueError("as classificações não reconciliam com o total nacional")

    by_state = []
    for abbreviation, count in zip(abbreviations, state_totals, strict=True):
        code = UF_CODES_BY_ABBREVIATION[abbreviation]
        by_state.append(
            {"code": code, "name": UF_NAMES[code], "service_records": count}
        )
    by_state.sort(key=lambda item: str(item["name"]))
    by_classification.sort(
        key=lambda item: (-int(item["service_records"]), str(item["classification_code"]))
    )
    return {
        "competence": competence,
        "total_service_records": national_total,
        "states": len(by_state),
        "service_classifications": len(by_classification),
        "by_state": by_state,
        "by_classification": by_classification,
        "by_state_classification": by_state_classification,
    }


def enrich_services_with_population(states: list[dict], population: dict) -> list[dict]:
    population_by_code = {
        item["code"]: int(item["population"]) for item in population["by_state"]
    }
    enriched = []
    for state in states:
        code = state["code"]
        if code not in population_by_code:
            raise ValueError(f"população ausente para a UF {code}")
        population_value = population_by_code[code]
        enriched.append(
            {
                **state,
                "population": population_value,
                "service_records_per_100k": round(
                    int(state["service_records"]) / population_value * 100_000,
                    2,
                ),
            }
        )
    return enriched
