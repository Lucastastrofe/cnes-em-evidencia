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


PROFESSIONAL_DEFINITION_URL = (
    "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?cnes/cnv/prid02br.def"
)
PROFESSIONAL_QUERY_URL = (
    "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/prid02br.def"
)


def _read_bytes(source: Path | BinaryIO | bytes) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, Path):
        return source.read_bytes()
    source.seek(0)
    return source.read()


def _competence_from_filename(filename: str) -> str:
    match = re.fullmatch(r"pfbr(\d{2})(\d{2})\.dbf", filename, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"arquivo de profissionais fora do padrão esperado: {filename}")
    return f"20{match.group(1)}{match.group(2)}"


def extract_latest_professional_file(source: Path | BinaryIO | bytes) -> tuple[str, str]:
    document = _read_bytes(source).decode("latin-1")
    filenames = set(re.findall(r"pfbr\d{4}\.dbf", document, flags=re.IGNORECASE))
    if not filenames:
        raise ValueError("a página do TabNet não informou competências de profissionais")
    latest = max(filenames, key=_competence_from_filename).lower()
    return latest, _competence_from_filename(latest)


def _professional_query_payload(filename: str) -> bytes:
    fields = {
        "Linha": "Unidade_da_Federação",
        "Coluna": "Atende_no_SUS",
        "Incremento": "Quantidade",
        "Arquivos": filename,
        "formato": "prn",
        "mostre": "Mostra",
    }
    return urllib.parse.urlencode(fields, encoding="latin-1").encode("ascii")


def download_professional_snapshot(
    destination: Path,
    definition_url: str = PROFESSIONAL_DEFINITION_URL,
    query_url: str = PROFESSIONAL_QUERY_URL,
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
            filename, competence = extract_latest_professional_file(definition)

            query_request = urllib.request.Request(
                query_url,
                data=_professional_query_payload(filename),
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

            parse_professional_snapshot(temporary, competence=competence)
            os.replace(temporary, destination)
            return {**headers, "competence": competence, "filename": filename}
        except (OSError, urllib.error.URLError, ValueError) as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(
        f"não foi possível obter os profissionais após {attempts} tentativas"
    ) from last_error


def _count(value: str) -> int:
    normalized = value.strip().replace(".", "")
    if normalized in {"", "-"}:
        return 0
    try:
        result = int(normalized)
    except ValueError as error:
        raise ValueError(f"quantidade de profissionais inválida: {value}") from error
    if result < 0:
        raise ValueError(f"quantidade de profissionais inválida: {value}")
    return result


def parse_professional_snapshot(
    source: Path | BinaryIO | bytes,
    competence: str,
    expected_states: int = 27,
) -> dict:
    document = _read_bytes(source).decode("latin-1")
    preformatted = re.search(r"<pre[^>]*>(.*?)</pre>", document, flags=re.I | re.S)
    if preformatted is None:
        raise ValueError("a resposta do TabNet não contém a tabela de profissionais")

    table = html.unescape(preformatted.group(1)).strip()
    rows = [row for row in csv.reader(StringIO(table), delimiter=";") if row]
    if len(rows) < 3:
        raise ValueError("a resposta do TabNet não contém linhas suficientes")

    header = [value.strip() for value in rows[0]]
    if header[1:] != ["Sim", "Não", "Total"]:
        raise ValueError("a tabela de profissionais não possui as colunas SUS esperadas")

    national_positions = [
        position
        for position, row in enumerate(rows[1:], start=1)
        if row[0].strip() == "Total"
    ]
    if len(national_positions) != 1:
        raise ValueError("a tabela de profissionais não possui total nacional")
    national_position = national_positions[0]
    national_row = rows[national_position]
    if len(national_row) != len(header):
        raise ValueError("o total nacional possui colunas incompatíveis")

    national_sus = _count(national_row[1])
    national_non_sus = _count(national_row[2])
    national_total = _count(national_row[3])
    if national_sus + national_non_sus != national_total:
        raise ValueError("a situação SUS não reconcilia com o total nacional")

    by_state: list[dict[str, str | int]] = []
    for row in rows[1:national_position]:
        if len(row) != len(header):
            raise ValueError("uma linha estadual possui colunas incompatíveis")
        state_match = re.match(r"(\d{2})\s+(.+)", row[0].strip())
        if state_match is None or state_match.group(1) not in UF_NAMES:
            raise ValueError(f"UF inválida na tabela de profissionais: {row[0]}")
        code = state_match.group(1)
        sus_professionals = _count(row[1])
        non_sus_professionals = _count(row[2])
        professionals = _count(row[3])
        if sus_professionals + non_sus_professionals != professionals:
            raise ValueError(f"a situação SUS da UF {code} não reconcilia")
        by_state.append(
            {
                "code": code,
                "name": UF_NAMES[code],
                "professionals": professionals,
                "sus_professionals": sus_professionals,
                "non_sus_professionals": non_sus_professionals,
            }
        )

    observed_codes = {str(item["code"]) for item in by_state}
    if len(by_state) != expected_states or len(observed_codes) != expected_states:
        raise ValueError(
            "cobertura de UFs incompatível: "
            f"esperado {expected_states}, recebido {len(by_state)}"
        )
    if sum(int(item["professionals"]) for item in by_state) != national_total:
        raise ValueError("o total das UFs não reconcilia com o total nacional")
    if sum(int(item["sus_professionals"]) for item in by_state) != national_sus:
        raise ValueError("os profissionais SUS das UFs não reconciliam")
    if sum(int(item["non_sus_professionals"]) for item in by_state) != national_non_sus:
        raise ValueError("os profissionais não SUS das UFs não reconciliam")

    by_state.sort(key=lambda item: str(item["name"]))
    return {
        "competence": competence,
        "total_professionals": national_total,
        "sus_professionals": national_sus,
        "non_sus_professionals": national_non_sus,
        "states": len(by_state),
        "by_state": by_state,
    }


def enrich_professionals_with_population(states: list[dict], population: dict) -> list[dict]:
    population_by_code = {
        item["code"]: int(item["population"]) for item in population["by_state"]
    }
    enriched: list[dict] = []
    for state in states:
        code = state["code"]
        if code not in population_by_code:
            raise ValueError(f"população ausente para a UF {code}")
        population_value = population_by_code[code]
        professionals = int(state["professionals"])
        enriched.append(
            {
                **state,
                "population": population_value,
                "professionals_per_100k": round(
                    professionals / population_value * 100_000,
                    2,
                ),
                "sus_share": (
                    round(int(state["sus_professionals"]) / professionals, 6)
                    if professionals
                    else 0.0
                ),
            }
        )
    return enriched
