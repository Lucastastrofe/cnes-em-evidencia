from __future__ import annotations

import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from cnes_audit.presentation import (
    describe_controls,
    interpret_materiality,
    management_without_information,
    split_checks,
)

DATA_DIRECTORY = Path(__file__).parent / "data" / "published"


@st.cache_data(show_spinner=False)
def load_data() -> tuple[dict, dict]:
    dashboard = json.loads((DATA_DIRECTORY / "dashboard.json").read_text(encoding="utf-8"))
    audit = json.loads((DATA_DIRECTORY / "audit-report.json").read_text(encoding="utf-8"))
    return dashboard, audit


def format_integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def format_small_percent(value: float) -> str:
    return f"{value * 100:.3f}%".replace(".", ",")


def format_timestamp(value: str) -> str:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment.strftime("%d/%m/%Y às %H:%M UTC")


def format_source_date(value: str) -> str:
    if value == "não informado":
        return value
    return parsedate_to_datetime(value).strftime("%d/%m/%Y às %H:%M UTC")


def state_table(states: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(states).rename(
        columns={"name": "UF", "records": "Registros", "issues": "Ocorrências"}
    )
    frame["Taxa de ocorrências"] = frame["Ocorrências"] / frame["Registros"]
    return frame[["UF", "Registros", "Ocorrências", "Taxa de ocorrências"]]


def render() -> None:
    st.set_page_config(
        page_title="CNES em Evidência",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        :root {
            --ink: #17211d;
            --muted: #56645e;
            --line: #d9e0dc;
            --green: #176b52;
            --green-soft: #edf6f1;
            --amber: #9a4f16;
            --amber-soft: #fff4e8;
        }
        .block-container {max-width: 1120px; padding-top: 2.5rem; padding-bottom: 4rem;}
        h1, h2, h3 {color: var(--ink); letter-spacing: -0.025em;}
        h1 {font-size: clamp(2.25rem, 5vw, 3.8rem); line-height: 1.02; margin-bottom: 0.65rem;}
        .eyebrow {color: var(--green); font-size: 0.76rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;}
        .deck {color: var(--muted); font-size: 1.08rem; max-width: 760px; margin: 0.5rem 0 0.25rem;}
        .source {color: var(--muted); font-size: 0.85rem; margin-bottom: 1.75rem;}
        [data-testid="stMetric"] {border-top: 2px solid var(--ink); padding-top: 0.75rem;}
        [data-testid="stMetricLabel"] {color: var(--muted);}
        [data-testid="stMetricValue"] {color: var(--ink); font-size: 2rem;}
        .verdict {background: var(--green-soft); border-left: 4px solid var(--green); padding: 1rem 1.15rem; margin: 1.5rem 0;}
        .verdict strong {display: block; color: var(--ink); font-size: 1.2rem; margin: 0.2rem 0;}
        .finding {border: 1px solid #e8c9aa; background: var(--amber-soft); padding: 1.25rem; margin: 1rem 0 1.25rem;}
        .finding-grid {display: grid; grid-template-columns: minmax(110px, 0.35fr) 1fr; gap: 1.25rem; align-items: start;}
        .finding-rate {color: var(--amber); font-size: 2.5rem; font-weight: 750; line-height: 1;}
        .finding-title {color: var(--ink); font-size: 1.15rem; font-weight: 700; margin-bottom: 0.35rem;}
        .finding-copy {color: #4f4035; margin: 0.25rem 0;}
        .scope-note {border-top: 1px solid var(--line); color: var(--muted); font-size: 0.9rem; margin-top: 1rem; padding-top: 0.75rem;}
        @media (max-width: 640px) {
            .block-container {padding-top: 1.5rem;}
            .finding-grid {grid-template-columns: 1fr; gap: 0.65rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        dashboard, audit = load_data()
    except (OSError, json.JSONDecodeError, KeyError) as error:
        st.error("Os dados do painel não estão disponíveis nesta execução.")
        st.exception(error)
        st.stop()

    summary = dashboard["summary"]
    checks = dashboard["checks"]
    missing_location = next(item for item in checks if item["id"] == "coordinates_missing")
    approved_checks, _ = split_checks(checks)
    materiality = interpret_materiality(
        missing_location["id"], missing_location["failure_rate"]
    )

    st.markdown('<p class="eyebrow">Auditoria antes da análise</p>', unsafe_allow_html=True)
    st.title("CNES em Evidência")
    st.markdown(
        '<p class="deck">Uma leitura da qualidade cadastral antes de reutilizar a base '
        "em mapas, indicadores e estudos sobre a rede de saúde.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<p class="source">'
            f'Última verificação automática: {format_timestamp(dashboard["metadata"]["generated_at"])}. '
            f'Data informada pela fonte: {format_source_date(dashboard["metadata"]["source_last_modified"])}.'
            "</p>"
        ),
        unsafe_allow_html=True,
    )

    first, second, third = st.columns(3)
    first.metric("Registros verificados", format_integer(summary["total_records"]))
    second.metric("UFs presentes", summary["states_with_records"])
    third.metric(f"Controles aprovados (de {summary['checks_run']})", len(approved_checks))

    st.markdown(
        (
            '<div class="verdict"><span class="eyebrow">Leitura executiva</span>'
            f"<strong>{len(approved_checks)} de {summary['checks_run']} controles não encontraram ocorrências.</strong>"
            "A base passou pelas verificações definidas antes de ser usada nos próximos estudos. "
            "O único achado precisa ser considerado quando a análise depender de localização exata.</div>"
        ),
        unsafe_allow_html=True,
    )

    st.subheader("Achado que muda a forma de usar a base")
    st.markdown(
        (
            '<div class="finding"><div class="finding-grid">'
            f'<div><div class="finding-rate">{format_percent(missing_location["failure_rate"])}</div>'
            f'<div>{format_integer(missing_location["failures"])} registros</div></div>'
            f'<div><div class="finding-title">{materiality["classification"]}</div>'
            f'<p class="finding-copy">{materiality["affected_use"]}</p>'
            f'<p class="finding-copy">{materiality["unaffected_use"]}</p>'
            f'<p class="scope-note">{materiality["criterion"]}</p></div>'
            "</div></div>"
        ),
        unsafe_allow_html=True,
    )

    states = state_table(dashboard["by_state"])
    selected_state = st.selectbox("Detalhar uma UF", ["Todas", *states["UF"].tolist()])
    if selected_state != "Todas":
        detail = states.loc[states["UF"] == selected_state].iloc[0]
        detail_a, detail_b, detail_c = st.columns(3)
        detail_a.metric("Registros na UF", format_integer(int(detail["Registros"])))
        detail_b.metric("Ocorrências de regras", format_integer(int(detail["Ocorrências"])))
        detail_c.metric("Taxa de ocorrências", format_percent(detail["Taxa de ocorrências"]))

    chart_tab, table_tab = st.tabs(["Distribuição por UF", "Tabela completa"])
    with chart_tab:
        top_states = states.nlargest(10, "Registros").set_index("UF")
        st.bar_chart(top_states["Registros"], horizontal=True, color="#176B52")
        st.caption(
            "Dez UFs com maior quantidade de registros na fonte mais recente verificada. "
            "O gráfico é regenerado em cada execução automática."
        )
    with table_tab:
        st.dataframe(
            states,
            width="stretch",
            hide_index=True,
            column_config={
                "Registros": st.column_config.NumberColumn(format="localized"),
                "Ocorrências": st.column_config.NumberColumn(format="localized"),
                "Taxa de ocorrências": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=max(float(states["Taxa de ocorrências"].max()), 0.01),
                    format="percent",
                ),
            },
        )

    st.subheader("Controles de qualidade")
    st.write(
        "Oito regras verificam completude, unicidade e validade. O resultado informa o que "
        "foi aprovado e identifica diretamente a regra que exige atenção."
    )
    st.dataframe(
        pd.DataFrame(describe_controls(checks)),
        width="stretch",
        hide_index=True,
        column_config={
            "Controle": st.column_config.TextColumn(width="medium"),
            "O que verifica": st.column_config.TextColumn(width="large"),
            "Resultado": st.column_config.TextColumn(width="medium"),
        },
    )
    with st.expander("Como interpretar os controles aprovados"):
        st.write(
            f"{len(approved_checks)} controles não encontraram ocorrência nesta fotografia. "
            "Isso é evidência de verificação para essas regras, não uma garantia de qualidade "
            "total da base. Novos usos podem exigir controles adicionais."
        )

    st.subheader("Tipo de gestão")
    management_rows = dashboard["by_management"]
    management = pd.DataFrame(management_rows).set_index("label")
    management_chart, management_note = st.columns([3, 1])
    with management_chart:
        st.bar_chart(management["records"], horizontal=True, color="#2B716F")
    with management_note:
        unknown_management = management_without_information(
            management_rows, summary["total_records"]
        )
        st.metric("Gestão sem informação", format_integer(unknown_management["records"]))
        st.write(f'{format_small_percent(unknown_management["rate"])} da base.')
        st.caption(
            "O código S está separado para não desaparecer na escala do gráfico. "
            "Ele indica limitação analítica; não foi classificado como erro sem uma regra "
            "oficial de domínio que sustente essa conclusão."
        )

    with st.expander("Rastreabilidade da execução"):
        trace_first, trace_second = st.columns(2)
        trace_first.write(f"**Execução:** `{audit['run_id']}`")
        trace_first.write(f"**Versão do código:** `{audit['code_version']}`")
        trace_second.write(f"**Linhas lidas:** {format_integer(audit['reconciliation']['rows_read'])}")
        trace_second.write(
            f"**Linhas agregadas:** {format_integer(audit['reconciliation']['rows_aggregated'])}"
        )
        st.write(f"**SHA-256 da fonte:** `{audit['source']['sha256']}`")
        st.link_button("Consultar a fonte oficial", audit["source"]["catalog_url"])

    st.caption(
        "Os indicadores descrevem o cadastro processado. Não medem qualidade assistencial, "
        "conformidade sanitária ou disponibilidade atual de serviços."
    )


if __name__ == "__main__":
    render()
