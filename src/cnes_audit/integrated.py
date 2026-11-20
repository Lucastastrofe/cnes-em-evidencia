"""Public state-level data contract, shared by exports and the interactive map."""
from __future__ import annotations

import csv
import io
from typing import Any
from cnes_audit.quality import UF_NAMES

METRICS = {
    "records": ("Estabelecimentos", None),
    "beds": ("Leitos", "beds"),
    "sus_beds": ("Leitos SUS", "beds"),
    "teams": ("Equipes", "teams"),
    "service_records": ("Registros de serviços", "services"),
    "professionals": ("Profissionais", "professionals"),
    "sus_professionals": ("Profissionais associados ao SUS", "professionals"),
}


def build_profile(dashboard: dict[str, Any]) -> dict[str, Any]:
    indexes = {}
    for section in ("beds", "teams", "services", "professionals"):
        rows = dashboard[section]["by_state"]
        index = {str(row["code"]): row for row in rows}
        if len(index) != len(rows):
            raise ValueError(f"UF duplicada: {section}")
        indexes[section] = index
    rows = []
    seen = set()
    states = list(dashboard["by_state"])
    base_codes = {str(row["code"]) for row in states}
    extra_codes = set().union(*(set(index) for index in indexes.values())) - base_codes
    for code in sorted(extra_codes):
        reference = next(index[code] for index in indexes.values() if code in index)
        states.append({"code": code, "name": reference["name"], "population": reference.get("population"), "issues": None})
    for state in states:
        code = str(state["code"])
        if code not in UF_NAMES:
            raise ValueError("UF fora do domínio oficial")
        if code in seen:
            raise ValueError("UF duplicada: estabelecimentos")
        seen.add(code)
        population = state["population"]
        if population is not None and population <= 0:
            raise ValueError("População precisa ser positiva")
        row = {key: state[key] for key in ("code", "name", "population", "issues")}
        for metric, (_, section) in METRICS.items():
            value = state.get(metric) if section is None else indexes[section].get(code, {}).get(metric)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"Contagem inválida: {metric}")
            row[metric] = value
        rows.append(row)
    return {
        "schema_version": "1.0",
        "run_id": dashboard["metadata"]["run_id"],
        "generated_at": dashboard["metadata"]["generated_at"],
        "population_reference_year": dashboard["summary"]["population_reference_year"],
        "periods": {section: dashboard[section]["summary"]["competence"] for section in indexes},
        "dictionary": {metric: {"label": label, "unit": "cadastros", "source": section or "estabelecimentos"} for metric, (label, section) in METRICS.items()},
        "rows": sorted(rows, key=lambda row: row["code"]),
    }


def profile_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
