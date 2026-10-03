from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

UF_NAMES = {
    "11": "Rondônia",
    "12": "Acre",
    "13": "Amazonas",
    "14": "Roraima",
    "15": "Pará",
    "16": "Amapá",
    "17": "Tocantins",
    "21": "Maranhão",
    "22": "Piauí",
    "23": "Ceará",
    "24": "Rio Grande do Norte",
    "25": "Paraíba",
    "26": "Pernambuco",
    "27": "Alagoas",
    "28": "Sergipe",
    "29": "Bahia",
    "31": "Minas Gerais",
    "32": "Espírito Santo",
    "33": "Rio de Janeiro",
    "35": "São Paulo",
    "41": "Paraná",
    "42": "Santa Catarina",
    "43": "Rio Grande do Sul",
    "50": "Mato Grosso do Sul",
    "51": "Mato Grosso",
    "52": "Goiás",
    "53": "Distrito Federal",
}

MANAGEMENT_NAMES = {
    "E": "Estadual",
    "M": "Municipal",
    "D": "Dupla",
    "S": "Sem informação",
}

CHECK_DEFINITIONS = {
    "cnes_missing": ("Chave CNES não preenchida", "completude", "alerta"),
    "cnes_duplicate": ("Chave CNES repetida", "unicidade", "alerta"),
    "uf_invalid": ("Código de UF fora do domínio", "validade", "alerta"),
    "municipality_code_invalid": (
        "Código de município ausente ou fora do formato esperado",
        "validade",
        "alerta",
    ),
    "coordinates_missing": (
        "Par de coordenadas não preenchido",
        "completude",
        "observação",
    ),
    "coordinates_out_of_range": (
        "Par de coordenadas fora das faixas geográficas",
        "validade",
        "alerta",
    ),
    "unit_type_missing": ("Tipo de unidade não preenchido", "completude", "alerta"),
    "management_missing": ("Tipo de gestão não preenchido", "completude", "observação"),
}


def _coordinates_valid(north_south: str, east_west: str) -> bool:
    try:
        return -90 <= float(north_south) <= 90 and -180 <= float(east_west) <= 180
    except ValueError:
        return False


def _make_check(check_id: str, failures: int, evaluated: int) -> dict[str, Any]:
    label, dimension, severity = CHECK_DEFINITIONS[check_id]
    return {
        "id": check_id,
        "label": label,
        "dimension": dimension,
        "severity": severity,
        "status": "aprovado" if failures == 0 else severity,
        "evaluated": evaluated,
        "failures": failures,
        "failure_rate": round(failures / evaluated, 6) if evaluated else 0,
    }


def audit_rows(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    total = 0
    seen_cnes: set[str] = set()
    failures: Counter[str] = Counter()
    by_state: dict[str, Counter[str]] = defaultdict(Counter)
    by_type: Counter[str] = Counter()
    by_management: Counter[str] = Counter()

    for row in rows:
        total += 1
        uf = row["CO_UF"]
        state_key = uf if uf in UF_NAMES else "invalid"
        state = by_state[state_key]
        state["records"] += 1

        cnes = row["CO_CNES"]
        if not cnes:
            failures["cnes_missing"] += 1
            state["cnes_missing"] += 1
        elif cnes in seen_cnes:
            failures["cnes_duplicate"] += 1
            state["cnes_duplicate"] += 1
        else:
            seen_cnes.add(cnes)

        if uf not in UF_NAMES:
            failures["uf_invalid"] += 1
            state["uf_invalid"] += 1

        municipality = row["CO_IBGE"]
        if not re.fullmatch(r"\d{6}", municipality):
            failures["municipality_code_invalid"] += 1
            state["municipality_code_invalid"] += 1

        unit_type = row["TP_UNIDADE"]
        if unit_type:
            by_type[unit_type] += 1
        else:
            failures["unit_type_missing"] += 1
            state["unit_type_missing"] += 1
            by_type["missing"] += 1

        management = row["TP_GESTAO"] or "S"
        by_management[management] += 1
        if not row["TP_GESTAO"]:
            failures["management_missing"] += 1
            state["management_missing"] += 1

        first_coord = row["NU_LATITUDE"]
        second_coord = row["NU_LONGITUDE"]
        if not first_coord or not second_coord:
            failures["coordinates_missing"] += 1
            state["coordinates_missing"] += 1
        elif not _coordinates_valid(first_coord, second_coord):
            failures["coordinates_out_of_range"] += 1
            state["coordinates_out_of_range"] += 1

    checks = [_make_check(check_id, failures[check_id], total) for check_id in CHECK_DEFINITIONS]
    state_rows = []
    for code, values in by_state.items():
        state_rows.append(
            {
                "code": code,
                "name": UF_NAMES.get(code, "UF inválida"),
                "records": values["records"],
                "issues": sum(values[check_id] for check_id in CHECK_DEFINITIONS),
            }
        )

    return {
        "summary": {
            "total_records": total,
            "states_with_records": sum(1 for code in by_state if code in UF_NAMES),
            "checks_run": len(checks),
            "checks_with_findings": sum(1 for item in checks if item["failures"] > 0),
        },
        "checks": checks,
        "by_state": sorted(state_rows, key=lambda item: (-item["records"], item["name"])),
        "by_unit_type": [
            {
                "code": code,
                "label": "Não informado" if code == "missing" else f"Tipo {code}",
                "records": count,
            }
            for code, count in by_type.most_common()
        ],
        "by_management": [
            {
                "code": code,
                "label": MANAGEMENT_NAMES.get(code, f"Código {code}"),
                "records": count,
            }
            for code, count in by_management.most_common()
        ],
    }

