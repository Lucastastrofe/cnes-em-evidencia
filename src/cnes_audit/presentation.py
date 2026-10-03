from __future__ import annotations


CONTROL_DESCRIPTIONS = {
    "cnes_missing": (
        "Chave CNES preenchida",
        "Confere se cada registro possui o identificador CNES.",
    ),
    "cnes_duplicate": (
        "Chave CNES única",
        "Procura identificadores CNES repetidos no arquivo.",
    ),
    "uf_invalid": (
        "UF válida",
        "Verifica se o código da UF pertence ao domínio oficial.",
    ),
    "municipality_code_invalid": (
        "Código do município válido",
        "Confere presença e formato do código de município.",
    ),
    "coordinates_missing": (
        "Coordenadas preenchidas",
        "Verifica se latitude e longitude estão preenchidas em conjunto.",
    ),
    "coordinates_out_of_range": (
        "Coordenadas em faixa geográfica válida",
        "Procura latitude ou longitude fora das faixas possíveis.",
    ),
    "unit_type_missing": (
        "Tipo de unidade preenchido",
        "Confere se o tipo de estabelecimento foi informado.",
    ),
    "management_missing": (
        "Tipo de gestão preenchido",
        "Confere se a gestão municipal, estadual ou dupla foi informada.",
    ),
}


def describe_controls(checks: list[dict]) -> list[dict[str, str]]:
    descriptions: list[dict[str, str]] = []
    for check in checks:
        title, explanation = CONTROL_DESCRIPTIONS[check["id"]]
        failures = int(check["failures"])
        if failures == 0:
            result = "Aprovado"
        else:
            rate = f"{float(check['failure_rate']) * 100:.1f}".replace(".", ",")
            count = f"{failures:,}".replace(",", ".")
            result = f"Atenção: {count} registros ({rate}%)"
        descriptions.append(
            {"Controle": title, "O que verifica": explanation, "Resultado": result}
        )
    return descriptions


def interpret_materiality(check_id: str, failure_rate: float) -> dict[str, str]:
    """Describe impact without assigning an unsupported universal severity threshold."""
    if check_id == "coordinates_missing" and failure_rate > 0:
        return {
            "classification": "Atenção para uso geográfico",
            "affected_use": "Afeta mapas, distâncias e análises de cobertura territorial.",
            "unaffected_use": "Não impede as contagens agregadas por UF ou tipo de gestão.",
            "criterion": "Sem limiar institucional informado, a criticidade depende do uso.",
        }

    return {
        "classification": "Avaliar conforme o uso",
        "affected_use": "Verifique se o campo participa do cálculo ou da decisão.",
        "unaffected_use": "Análises que não dependem do campo não são diretamente afetadas.",
        "criterion": "A taxa deve ser interpretada junto com o impacto analítico.",
    }


def split_checks(checks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate passed controls from findings so zeroes are not framed as failures."""
    approved: list[dict] = []
    findings: list[dict] = []

    for check in checks:
        dimension = str(check["dimension"]).capitalize()
        if int(check["failures"]) == 0:
            approved.append(
                {
                    "Regra": check["label"],
                    "Dimensão": dimension,
                    "Resultado": "Aprovado",
                }
            )
            continue

        findings.append(
            {
                "Regra": check["label"],
                "Dimensão": dimension,
                "Ocorrências": int(check["failures"]),
                "Taxa": float(check["failure_rate"]),
            }
        )

    return approved, findings
