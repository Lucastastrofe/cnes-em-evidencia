from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

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


def format_timestamp(value: str) -> str:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment.strftime("%d/%m/%Y às %H:%M UTC")


def state_table(states: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(states).rename(
        columns={"name": "UF", "records": "Registros", "issues": "Ocorrências"}
    )
    frame["Taxa de ocorrências"] = frame["Ocorrências"] / frame["Registros"]
    return frame[["UF", "Registros", "Ocorrências", "Taxa de ocorrências"]]


def check_table(checks: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(checks).rename(
        columns={
            "label": "Regra",
            "dimension": "Dimensão",
            "status": "Resultado",
            "failures": "Ocorrências",
            "failure_rate": "Taxa",
        }
    )
    return frame[["Regra", "Dimensão", "Resultado", "Ocorrências", "Taxa"]]


def render() -> None:
    st.set_page_config(
        page_title="CNES em Evidência",
        page_icon="U0001f3e5",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        .block-container {max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem;}
        h1, h2, h3 {letter-spacing: -0.025em;}
        [data-testid="stMetric"] {border-top: 1px solid #9da8a3; padding-top: 0.8rem;}
        [data-testid="stMetricValue"] {font-size: 2rem;}
        .finding {border-left: 4px solid #a94c16; padding: 0.2rem 0 0.2rem 1rem; margin: 1rem 0 2rem;}
        .finding strong {font-size: 1.45rem; font-weight: 700;}
        .source {color: #5a6561; font-size: 0.88rem;}
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

    st.title("CNES em Evidência")
    st.write("Qualidade cadastral dos estabelecimentos de saúde na base aberta do CNES.")
    st.markdown(
        f'<p class="source">Fotografia processada em {format_timestamp(dashboard["metadata"]["generated_at"])}.</p>',
        unsafe_allow_html=True,
    )

    first, second, third, fourth = st.columns(4)
    first.metric("Registros", format_integer(summary["total_records"]))
    second.metric("UFs presentes", summary["states_with_records"])
    third.metric("Controles", summary["checks_run"])
    fourth.metric("Com achados", summary["checks_with_findings"])

    st.markdown(
        (
            '<div class="finding"><strong>'
            f'{format_percent(missing_location["failure_rate"])} sem o par completo de coordenadas'
            "</strong><br>"
            f'{format_integer(missing_location["failures"])} de '
            f'{format_integer(missing_location["evaluated"])} registros.</div>'
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
        st.caption("Dez UFs com maior quantidade de registros no arquivo processado.")
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
    st.dataframe(
        check_table(checks),
        width="stretch",
        hide_index=True,
        column_config={
            "Ocorrências": st.column_config.NumberColumn(format="localized"),
            "Taxa": st.column_config.NumberColumn(format="percent"),
        },
    )

    st.subheader("Tipo de gestão")
    management = pd.DataFrame(dashboard["by_management"]).set_index("label")
    st.bar_chart(management["records"], horizontal=True, color="#2B716F")

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

