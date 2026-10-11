from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from cnes_audit.presentation import (
    describe_controls,
    format_source_date,
    format_timestamp,
    interpret_materiality,
    management_without_information,
    split_checks,
)

DATA_DIRECTORY = Path(__file__).parent / "data" / "published"


def published_data_version() -> tuple[int, int]:
    return tuple(
        (DATA_DIRECTORY / filename).stat().st_mtime_ns
        for filename in ("dashboard.json", "audit-report.json")
    )


@st.cache_data(show_spinner=False)
def load_data(data_version: tuple[int, int]) -> tuple[dict, dict]:
    del data_version
    dashboard = json.loads((DATA_DIRECTORY / "dashboard.json").read_text(encoding="utf-8"))
    audit = json.loads((DATA_DIRECTORY / "audit-report.json").read_text(encoding="utf-8"))
    return dashboard, audit


def format_integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def format_small_percent(value: float) -> str:
    return f"{value * 100:.3f}%".replace(".", ",")


def format_rate(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def state_table(states: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(states).rename(
        columns={
            "name": "UF",
            "records": "Registros",
            "issues": "Ocorrências",
            "population": "População estimada",
            "establishments_per_100k": "Cadastros por 100 mil habitantes",
        }
    )
    frame["Taxa de ocorrências"] = frame["Ocorrências"] / frame["Registros"]
    return frame[
        [
            "UF",
            "Registros",
            "População estimada",
            "Cadastros por 100 mil habitantes",
            "Ocorrências",
            "Taxa de ocorrências",
        ]
    ]


def render_update_context(dashboard: dict) -> None:
    st.markdown(
        (
            '<p class="source">'
            f'Última verificação automática: {format_timestamp(dashboard["metadata"]["generated_at"])}. '
            f'Data informada pela fonte: {format_source_date(dashboard["metadata"]["source_last_modified"])}.'
            "</p>"
        ),
        unsafe_allow_html=True,
    )


def render_traceability(audit: dict, include_population: bool = False) -> None:
    with st.expander("Rastreabilidade da execução"):
        trace_first, trace_second = st.columns(2)
        trace_first.write(f"**Execução:** `{audit['run_id']}`")
        trace_first.write(f"**Versão do código:** `{audit['code_version']}`")
        trace_second.write(
            f"**Linhas lidas:** {format_integer(audit['reconciliation']['rows_read'])}"
        )
        trace_second.write(
            f"**Linhas agregadas:** {format_integer(audit['reconciliation']['rows_aggregated'])}"
        )
        st.write(f"**SHA-256 da fonte:** `{audit['source']['sha256']}`")
        st.link_button("Consultar a fonte oficial", audit["source"]["catalog_url"])
        if include_population:
            st.write(f"**SHA-256 da população:** `{audit['population_source']['sha256']}`")
            st.link_button(
                "Consultar estimativas do IBGE",
                audit["population_source"]["catalog_url"],
            )


def render_population_panel(dashboard: dict, audit: dict) -> None:
    summary = dashboard["summary"]
    states = state_table(dashboard["by_state"])
    population_states = states.dropna(
        subset=["População estimada", "Cadastros por 100 mil habitantes"]
    )

    st.markdown('<p class="eyebrow">Parte 2 · Comparação proporcional</p>', unsafe_allow_html=True)
    st.title("CNES e população")
    st.markdown(
        '<p class="deck">Um painel para comparar a presença cadastral entre UFs sem deixar '
        "que o tamanho da população distorça a leitura.</p>",
        unsafe_allow_html=True,
    )
    render_update_context(dashboard)

    st.subheader("Painel de comparação por população")
    st.write(
        "Estados com populações diferentes não devem ser comparados apenas pelo total de "
        "cadastros. Este painel apresenta quantos registros do CNES existem para cada 100 mil "
        "habitantes, permitindo observar diferenças relativas entre as UFs."
    )
    filter_states, filter_scope = st.columns([2, 1])
    with filter_states:
        selected_ufs = st.multiselect(
            "UFs para comparar (vazio = Brasil completo)",
            population_states["UF"].tolist(),
            placeholder="Todas as UFs",
        )
    with filter_scope:
        comparison_scope = st.selectbox(
            "Recorte da comparação",
            ["Todas as UFs selecionadas", "10 maiores taxas", "10 menores taxas"],
        )

    if not selected_ufs:
        selected_ufs = population_states["UF"].tolist()

    comparison = population_states.loc[population_states["UF"].isin(selected_ufs)]
    if comparison_scope == "10 maiores taxas":
        comparison = comparison.nlargest(10, "Cadastros por 100 mil habitantes")
    elif comparison_scope == "10 menores taxas":
        comparison = comparison.nsmallest(10, "Cadastros por 100 mil habitantes")

    weighted_rate = (
        comparison["Registros"].sum()
        / comparison["População estimada"].sum()
        * 100_000
    )
    highest = comparison.nlargest(1, "Cadastros por 100 mil habitantes").iloc[0]
    lowest = comparison.nsmallest(1, "Cadastros por 100 mil habitantes").iloc[0]

    rate_a, rate_b, rate_c, rate_d = st.columns(4)
    rate_a.metric("Taxa ponderada da seleção", f"{format_rate(weighted_rate)} por 100 mil")
    rate_b.metric("UFs na comparação", len(comparison))
    rate_c.metric("Maior taxa", format_rate(highest["Cadastros por 100 mil habitantes"]))
    rate_c.caption(highest["UF"])
    rate_d.metric("Menor taxa", format_rate(lowest["Cadastros por 100 mil habitantes"]))
    rate_d.caption(lowest["UF"])

    rate_chart = (
        alt.Chart(comparison)
        .mark_bar(color="#2B716F")
        .encode(
            x=alt.X(
                "Cadastros por 100 mil habitantes:Q",
                title="Cadastros por 100 mil habitantes",
            ),
            y=alt.Y(
                "UF:N",
                sort=alt.SortField(
                    field="Cadastros por 100 mil habitantes",
                    order="descending",
                ),
                title=None,
            ),
            tooltip=[
                alt.Tooltip("UF:N"),
                alt.Tooltip("Registros:Q", format=",.0f"),
                alt.Tooltip("População estimada:Q", format=",.0f"),
                alt.Tooltip("Cadastros por 100 mil habitantes:Q", format=".0f"),
            ],
        )
        .properties(height=max(260, len(comparison) * 24))
    )
    rate_chart_tab, rate_table_tab = st.tabs(["Comparação visual", "Dados da seleção"])
    with rate_chart_tab:
        st.altair_chart(rate_chart, width="stretch")
    with rate_table_tab:
        st.dataframe(
            comparison[
                [
                    "UF",
                    "Registros",
                    "População estimada",
                    "Cadastros por 100 mil habitantes",
                ]
            ].sort_values("Cadastros por 100 mil habitantes", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "Registros": st.column_config.NumberColumn(format="localized"),
                "População estimada": st.column_config.NumberColumn(format="localized"),
                "Cadastros por 100 mil habitantes": st.column_config.NumberColumn(format="%.0f"),
            },
        )

    st.caption(
        f"CNES da execução atual e população estimada pelo IBGE para "
        f'{summary["population_reference_year"]}. A métrica descreve presença cadastral; '
        "não mede oferta, acesso ou capacidade assistencial."
    )
    render_traceability(audit, include_population=True)


def render_quality_panel(dashboard: dict, audit: dict) -> None:
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
    render_update_context(dashboard)

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
        detail_b.metric("Ocorrências", format_integer(int(detail["Ocorrências"])))
        detail_c.metric("Taxa de ocorrências", format_percent(detail["Taxa de ocorrências"]))

    chart_tab, table_tab = st.tabs(["Distribuição por UF", "Tabela completa"])
    with chart_tab:
        top_states = states.nlargest(10, "Registros").set_index("UF")
        st.bar_chart(top_states["Registros"], horizontal=True, color="#176B52")
        st.caption("Dez UFs com maior quantidade de registros na fonte mais recente verificada.")
    with table_tab:
        quality_states = states[["UF", "Registros", "Ocorrências", "Taxa de ocorrências"]]
        st.dataframe(
            quality_states,
            width="stretch",
            hide_index=True,
            column_config={
                "Registros": st.column_config.NumberColumn(format="localized"),
                "Ocorrências": st.column_config.NumberColumn(format="localized"),
                "Taxa de ocorrências": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=max(float(quality_states["Taxa de ocorrências"].max()), 0.01),
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

    render_traceability(audit)

    st.caption(
        "Os indicadores descrevem o cadastro processado. Não medem qualidade assistencial, "
        "conformidade sanitária ou disponibilidade atual de serviços."
    )


def render() -> None:
    st.set_page_config(
        page_title="CNES em Evidência",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
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
        [data-testid="stSidebar"] {background: #f4f7f5; border-right: 1px solid var(--line);}
        [data-testid="stSidebarNav"] a {border-radius: 0.55rem; margin: 0.2rem 0;}
        [data-testid="stSidebarNav"] a:hover {background: #e7f1ec;}
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
        dashboard, audit = load_data(published_data_version())
    except (OSError, json.JSONDecodeError, KeyError) as error:
        st.error("Os dados do painel não estão disponíveis nesta execução.")
        st.exception(error)
        st.stop()

    def quality_page_content() -> None:
        render_quality_panel(dashboard, audit)

    def population_page_content() -> None:
        render_population_panel(dashboard, audit)

    quality_page = st.Page(
        quality_page_content,
        title="1 · Qualidade cadastral",
        icon=":material/fact_check:",
        default=True,
    )
    population_page = st.Page(
        population_page_content,
        title="2 · Presença por população",
        icon=":material/compare_arrows:",
    )
    navigation = st.navigation(
        {"Painéis da série": [quality_page, population_page]},
        position="sidebar",
    )
    navigation.run()


if __name__ == "__main__":
    render()
