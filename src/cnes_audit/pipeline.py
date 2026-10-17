from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cnes_audit.beds import aggregate_latest_bed_capacity, enrich_beds_with_population
from cnes_audit.population import enrich_states_with_population, read_population_estimates
from cnes_audit.quality import audit_rows
from cnes_audit.source import iter_csv_rows, zip_entry_metadata

DEFAULT_SOURCE_URL = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/"
    "CNES/cnes_estabelecimentos_csv.zip"
)
DEFAULT_POPULATION_URL = (
    "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/"
    "p/last%201?formato=json"
)
DEFAULT_BEDS_URL = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/"
    "Leitos_SUS/Leitos_csv_2026.zip"
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_source(url: str, destination: Path, attempts: int = 3) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    request = urllib.request.Request(url, headers={"User-Agent": "cnes-em-evidencia/0.1"})
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                with temporary.open("wb") as target:
                    shutil.copyfileobj(response, target, length=1024 * 1024)
                os.replace(temporary, destination)
                return {
                    "last_modified": response.headers.get("Last-Modified", "não informado"),
                    "etag": response.headers.get("ETag", "não informado").strip('"'),
                }
        except (OSError, urllib.error.URLError) as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(f"não foi possível obter a fonte após {attempts} tentativas") from last_error


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def build_public_artifacts(
    source_path: Path,
    beds_path: Path,
    population_path: Path,
    output_directory: Path,
    source_url: str,
    beds_url: str,
    population_url: str,
    obtained_at: str,
    source_last_modified: str,
    beds_last_modified: str,
    population_last_modified: str,
    code_version: str,
    source_etag: str = "não informado",
    beds_etag: str = "não informado",
    population_etag: str = "não informado",
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_hash = sha256_file(source_path)
    beds_hash = sha256_file(beds_path)
    population_hash = sha256_file(population_path)
    archive = zip_entry_metadata(source_path)
    dashboard = audit_rows(iter_csv_rows(source_path))
    population = read_population_estimates(population_path)
    beds = aggregate_latest_bed_capacity(beds_path)
    dashboard["by_state"] = enrich_states_with_population(
        dashboard["by_state"], population
    )
    dashboard["summary"].update(
        {
            "population_reference_year": population["reference_year"],
            "total_population": population["total_population"],
        }
    )
    bed_states = enrich_beds_with_population(beds["by_state"], population)
    dashboard["beds"] = {
        "summary": {
            "competence": beds["competence"],
            "rows_selected": beds["rows_selected"],
            "total_beds": beds["total_beds"],
            "sus_beds": beds["sus_beds"],
            "uti_beds": beds["uti_beds"],
            "uti_sus_beds": beds["uti_sus_beds"],
            "beds_per_100k": round(
                beds["total_beds"] / population["total_population"] * 100_000,
                2,
            ),
            "sus_beds_per_100k": round(
                beds["sus_beds"] / population["total_population"] * 100_000,
                2,
            ),
        },
        "by_state": bed_states,
    }
    total_rows = dashboard["summary"]["total_records"]
    aggregated_rows = sum(item["records"] for item in dashboard["by_state"])
    if total_rows != aggregated_rows:
        raise RuntimeError(
            f"reconciliação falhou: {total_rows} lidas e {aggregated_rows} agregadas"
        )

    run_id = f"{obtained_at.replace(':', '').replace('-', '')}-{source_hash[:12]}"
    public_metadata = {
        "run_id": run_id,
        "generated_at": obtained_at,
        "source_last_modified": source_last_modified,
        "source_sha256": source_hash,
        "population_source_sha256": population_hash,
    }
    dashboard["metadata"] = public_metadata
    audit = {
        "status": "concluído",
        "run_id": run_id,
        "generated_at": obtained_at,
        "process": "cnes-audit",
        "code_version": code_version,
        "source": {
            "catalog_url": (
                "https://dadosabertos.saude.gov.br/dataset/"
                "cnes-cadastro-nacional-de-estabelecimentos-de-saude"
            ),
            "resource_url": source_url,
            "obtained_at": obtained_at,
            "last_modified": source_last_modified,
            "etag": source_etag,
            "sha256": source_hash,
            "archive_bytes": source_path.stat().st_size,
            "entry_name": archive["name"],
            "entry_bytes": archive["uncompressed_bytes"],
        },
        "population_source": {
            "catalog_url": (
                "https://www.ibge.gov.br/estatisticas/sociais/populacao/"
                "9103-estimativas-de-populacao.html"
            ),
            "resource_url": population_url,
            "obtained_at": obtained_at,
            "last_modified": population_last_modified,
            "etag": population_etag,
            "sha256": population_hash,
            "reference_year": population["reference_year"],
            "states": len(population["by_state"]),
            "total_population": population["total_population"],
        },
        "beds_source": {
            "catalog_url": "https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos",
            "resource_url": beds_url,
            "obtained_at": obtained_at,
            "last_modified": beds_last_modified,
            "etag": beds_etag,
            "sha256": beds_hash,
            "archive_bytes": beds_path.stat().st_size,
            "competence": beds["competence"],
            "rows_read": beds["rows_read"],
            "rows_selected": beds["rows_selected"],
            "states": len(beds["by_state"]),
        },
        "contract": {
            "version": "3.0",
            "publication_level": "somente contagens agregadas",
            "raw_data_published": False,
        },
        "reconciliation": {
            "rows_read": total_rows,
            "rows_aggregated": aggregated_rows,
            "difference": total_rows - aggregated_rows,
            "beds_national": beds["total_beds"],
            "beds_by_state": sum(int(item["beds"]) for item in bed_states),
            "sus_beds_national": beds["sus_beds"],
            "sus_beds_by_state": sum(int(item["sus_beds"]) for item in bed_states),
        },
        "checks": dashboard["checks"],
        "limitations": [
            "Os resultados descrevem o arquivo processado e não a qualidade da assistência.",
            "A fonte pode refletir ritmos diferentes de atualização entre gestores locais.",
            "Ausência cadastral não comprova ausência de serviço ou estrutura.",
            "A taxa por população mede presença cadastral relativa, não capacidade assistencial.",
            "Leitos cadastrados não informam ocupação ou disponibilidade em tempo real.",
            "Os tipos de unidade são exibidos por código até a incorporação de tabela oficial versionada.",
        ],
    }
    _write_json(output_directory / "dashboard.json", dashboard)
    _write_json(output_directory / "audit-report.json", audit)
    return dashboard, audit
