from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_population_estimates(
    source_path: Path, expected_states: int = 27
) -> dict[str, Any]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("resposta do IBGE vazia ou incompatível")

    rows = payload[1:]
    state_codes = [str(row.get("D1C", "")) for row in rows]
    if len(rows) != expected_states or len(set(state_codes)) != expected_states:
        raise ValueError(
            f"cobertura de UFs incompatível: esperadas {expected_states}, recebidas {len(set(state_codes))}"
        )

    years = {str(row.get("D3C", "")) for row in rows}
    if len(years) != 1:
        raise ValueError("resposta do IBGE contém mais de um ano de referência")

    by_state: list[dict[str, int | str]] = []
    for row in rows:
        try:
            population = int(str(row["V"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("população ausente ou inválida na resposta do IBGE") from error
        if population <= 0:
            raise ValueError("população deve ser maior que zero")
        by_state.append(
            {
                "code": str(row["D1C"]),
                "name": str(row["D1N"]),
                "population": population,
            }
        )

    return {
        "reference_year": int(years.pop()),
        "total_population": sum(int(item["population"]) for item in by_state),
        "by_state": by_state,
    }
