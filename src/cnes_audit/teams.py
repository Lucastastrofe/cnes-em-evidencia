from __future__ import annotations

import csv
import html
from io import StringIO
import os
from pathlib import Path
import re
import shutil
import time
from typing import BinaryIO
import urllib.error
import urllib.parse
import urllib.request

from cnes_audit.quality import UF_NAMES


TEAM_DEFINITION_URL = (
    "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/equipebr.def"
)
TEAM_QUERY_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/equipebr.def"


def _read_bytes(source: Path | BinaryIO | bytes) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, Path):
        return source.read_bytes()
    source.seek(0)
    return source.read()


def _competence_from_filename(filename: str) -> str:
    match = re.fullmatch(r"epbr(\d{2})(\d{2})\.dbf", filename, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"arquivo de equipes fora do padrão esperado: {filename}")
    return f"20{match.group(1)}{match.group(2)}"


def extract_latest_team_file(source: Path | BinaryIO | bytes) -> tuple[str, str]:
    document = _read_bytes(source).decode("latin-1")
    filenames = set(re.findall(r"epbr\d{4}\.dbf", document, flags=re.IGNORECASE))
    if not filenames:
        raise ValueError("a página do TabNet não informou competências de equipes")
    latest = max(filenames, key=_competence_from_filename).lower()
    return latest, _competence_from_filename(latest)


def _team_query_payload(filename: str) -> bytes:
    fields = {
        "Linha": "Unidade_da_Federação",
        "Coluna": "Tipo_da_Equipe",
        "Incremento": "Quantidade",
        "Arquivos": filename,
        "formato": "prn",
        "mostre": "Mostra",
    }
    return urllib.parse.urlencode(fields, encoding="latin-1").encode("ascii")


def download_team_snapshot(
    destination: Path,
    definition_url: str = TEAM_DEFINITION_URL,
    query_url: str = TEAM_QUERY_URL,
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
            filename, competence = extract_latest_team_file(definition)

            query_request = urllib.request.Request(
                query_url,
                data=_team_query_payload(filename),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "cnes-em-evidencia/0.1",
                },
            )
            with urllib.request.urlopen(query_request, timeout=120) as response:  # noqa: S310
                with temporary.open("wb") as target:
                    shutil.copyfileobj(response, target)
                headers = {
                    "last_modified": response.headers.get(
                        "Last-Modified", "não informado"
                    ),
                    "etag": response.headers.get("ETag", "não informado").strip('"'),
                }

            parse_team_snapshot(temporary, competence=competence)
            os.replace(temporary, destination)
            return {
                **headers,
                "competence": competence,
                "filename": filename,
            }
        except (OSError, urllib.error.URLError, ValueError) as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(
        f"não foi possível obter as equipes após {attempts} tentativas"
    ) from last_error


def _count(value: str) -> int:
    normalized = value.strip().replace(".", "")
    if normalized in {"", "-"}:
        return 0
    try:
        result = int(normalized)
    except ValueError as error:
        raise ValueError(f"quantidade de equipes inválida: {value}") from error
    if result < 0:
        raise ValueError(f"quantidade de equipes inválida: {value}")
    return result


def parse_team_snapshot(
    source: Path | BinaryIO | bytes,
    competence: str,
    expected_states: int = 27,
) -> dict:
    document = _read_bytes(source).decode("latin-1")
    preformatted = re.search(r"<pre[^>]*>(.*?)</pre>", document, flags=re.I | re.S)
    if preformatted is None:
        raise ValueError("a resposta do TabNet não contém a tabela de equipes")

    table = html.unescape(preformatted.group(1)).strip()
    rows = [row for row in csv.reader(StringIO(table), delimiter=";") if row]
    if len(rows) < 3:
        raise ValueError("a resposta do TabNet não contém linhas suficientes")

    header = rows[0]
    if header[-1].strip() != "Total":
        raise ValueError("a tabela de equipes não possui a coluna Total")
    type_columns: list[dict[str, str | int]] = []
    for position, label in enumerate(header[1:-1], start=1):
        match = re.match(r"(\d{2})\s+(.+)", label.strip())
        if match is None:
            raise ValueError(f"tipo de equipe fora do padrão esperado: {label}")
        type_columns.append(
            {
                "position": position,
                "code": match.group(1),
                "name": " ".join(match.group(2).split()),
            }
        )

    national_positions = [
        position for position, row in enumerate(rows[1:], start=1)
        if row[0].strip() == "Total"
    ]
    if len(national_positions) != 1:
        raise ValueError("a tabela de equipes não possui total nacional")
    national_position = national_positions[0]
    national_row = rows[national_position]
    if len(national_row) != len(header):
        raise ValueError("o total nacional possui colunas incompatíveis")

    national_types = {
        str(item["code"]): _count(national_row[int(item["position"])])
        for item in type_columns
    }
    national_total = _count(national_row[-1])
    if sum(national_types.values()) != national_total:
        raise ValueError("o total por tipo não reconcilia com o total nacional")

    by_state: list[dict[str, str | int]] = []
    by_state_type: list[dict[str, str | int]] = []
    observed_by_type = {code: 0 for code in national_types}
    for row in rows[1:national_position]:
        if len(row) != len(header):
            raise ValueError("uma linha estadual possui colunas incompatíveis")
        state_match = re.match(r"(\d{2})\s+(.+)", row[0].strip())
        if state_match is None or state_match.group(1) not in UF_NAMES:
            raise ValueError(f"UF inválida na tabela de equipes: {row[0]}")
        code = state_match.group(1)
        counts = {
            str(item["code"]): _count(row[int(item["position"])])
            for item in type_columns
        }
        state_total = _count(row[-1])
        if sum(counts.values()) != state_total:
            raise ValueError(f"o total da UF {code} não reconcilia com seus tipos")
        for type_code, count in counts.items():
            observed_by_type[type_code] += count
            if count > 0:
                type_definition = next(
                    item for item in type_columns if item["code"] == type_code
                )
                by_state_type.append(
                    {
                        "state_code": code,
                        "state_name": UF_NAMES[code],
                        "team_code": type_code,
                        "team_name": str(type_definition["name"]),
                        "teams": count,
                    }
                )
        by_state.append({"code": code, "name": UF_NAMES[code], "teams": state_total})

    if len(by_state) != expected_states or len({item["code"] for item in by_state}) != expected_states:
        raise ValueError(
            f"cobertura de UFs incompatível: esperado {expected_states}, recebido {len(by_state)}"
        )
    if sum(int(item["teams"]) for item in by_state) != national_total:
        raise ValueError("o total das UFs não reconcilia com o total nacional")
    if observed_by_type != national_types:
        raise ValueError("os totais estaduais por tipo não reconciliam com o total nacional")

    by_type = [
        {
            "code": str(item["code"]),
            "name": str(item["name"]),
            "teams": national_types[str(item["code"])],
        }
        for item in type_columns
        if national_types[str(item["code"])] > 0
    ]
    by_type.sort(key=lambda item: (-int(item["teams"]), str(item["name"])))
    by_state.sort(key=lambda item: str(item["name"]))
    return {
        "competence": competence,
        "total_teams": national_total,
        "states": len(by_state),
        "team_types": len(by_type),
        "by_state": by_state,
        "by_type": by_type,
        "by_state_type": by_state_type,
    }


def enrich_teams_with_population(states: list[dict], population: dict) -> list[dict]:
    population_by_code = {
        item["code"]: int(item["population"]) for item in population["by_state"]
    }
    enriched: list[dict] = []
    for state in states:
        code = state["code"]
        if code not in population_by_code:
            raise ValueError(f"população ausente para a UF {code}")
        population_value = population_by_code[code]
        enriched.append(
            {
                **state,
                "population": population_value,
                "teams_per_100k": round(
                    int(state["teams"]) / population_value * 100_000,
                    2,
                ),
            }
        )
    return enriched
