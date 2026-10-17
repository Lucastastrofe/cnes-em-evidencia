from __future__ import annotations

import argparse
import os
from pathlib import Path

from cnes_audit.pipeline import (
    DEFAULT_BEDS_URL,
    DEFAULT_POPULATION_URL,
    DEFAULT_SOURCE_URL,
    build_public_artifacts,
    download_source,
    utc_now,
)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Baixa, audita e agrega os dados abertos de estabelecimentos do CNES."
    )
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--population-url", default=DEFAULT_POPULATION_URL)
    parser.add_argument("--beds-url", default=DEFAULT_BEDS_URL)
    parser.add_argument("--input", type=Path, help="usa um ZIP local e não faz download")
    parser.add_argument(
        "--population-input",
        type=Path,
        help="usa um JSON local do SIDRA e não baixa a estimativa populacional",
    )
    parser.add_argument(
        "--beds-input",
        type=Path,
        help="usa um ZIP local de leitos e não baixa a fonte hospitalar",
    )
    parser.add_argument("--work-directory", type=Path, default=Path("data/work"))
    parser.add_argument("--output", type=Path, default=Path("data/published"))
    parser.add_argument("--code-version", default=os.getenv("GITHUB_SHA", "working-tree"))
    return parser


def main() -> int:
    args = make_parser().parse_args()
    obtained_at = utc_now()
    source_path = args.input or args.work_directory / "cnes_estabelecimentos_csv.zip"
    population_path = (
        args.population_input or args.work_directory / "ibge_population.json"
    )
    beds_path = args.beds_input or args.work_directory / "Leitos_csv_2026.zip"
    source_headers = {"last_modified": "arquivo local", "etag": "não informado"}
    population_headers = {
        "last_modified": "arquivo local",
        "etag": "não informado",
    }
    beds_headers = {"last_modified": "arquivo local", "etag": "não informado"}

    if args.input is None:
        source_headers = download_source(args.source_url, source_path)
    if args.population_input is None:
        population_headers = download_source(args.population_url, population_path)
    if args.beds_input is None:
        beds_headers = download_source(args.beds_url, beds_path)

    dashboard, audit = build_public_artifacts(
        source_path=source_path,
        beds_path=beds_path,
        population_path=population_path,
        output_directory=args.output,
        source_url=args.source_url,
        beds_url=args.beds_url,
        population_url=args.population_url,
        obtained_at=obtained_at,
        source_last_modified=source_headers["last_modified"],
        beds_last_modified=beds_headers["last_modified"],
        population_last_modified=population_headers["last_modified"],
        source_etag=source_headers["etag"],
        beds_etag=beds_headers["etag"],
        population_etag=population_headers["etag"],
        code_version=args.code_version,
    )
    print(
        f"{audit['run_id']}: {dashboard['summary']['total_records']} registros, "
        f"{dashboard['summary']['checks_with_findings']} controles com achados, "
        f"população de {dashboard['summary']['population_reference_year']}"
        f", leitos da competência {dashboard['beds']['summary']['competence']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
