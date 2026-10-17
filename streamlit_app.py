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


def render_source_facts(items: list[tuple[str, str]]) -> None:
    facts = "".join(
        f'<div class="source-fact"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in items
    )
    st.markdown(f'<div class="source-grid">{facts}</div>', unsafe_allow_html=True)


def render_definition_grid(items: list[tuple[str, str]]) -> None:
    definitions = "".join(
        f'<div class="definition"><strong>{title}</strong><p>{description}</p></div>'
        for title, description in items
    )
    st.markdown(f'<div class="definition-grid">{definitions}</div>', unsafe_allow_html=True)


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
    render_source_facts(
        [
            (
                "Arquivo informado pela fonte",
                format_source_date(dashboard["metadata"]["source_last_modified"]),
            ),
            (
                "Painel atualizado",
                format_timestamp(dashboard["metadata"]["generated_at"]),
            ),
        ]
    )


def render_traceability(
    audit: dict,
    include_population: bool = False,
    include_beds: bool = False,
) -> None:
    with st.expander("Fontes e rastreabilidade"):
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
        if include_beds:
            st.write(f"**SHA-256 da fonte de leitos:** `{audit['beds_source']['sha256']}`")
            st.write(
                "**Linhas da competência:** "
                f"{format_integer(audit['beds_source']['rows_selected'])}"
            )
            st.link_button(
                "Consultar a fonte de leitos",
                audit["beds_source"]["catalog_url"],
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

    st.subheader("O que este painel responde")
    st.write(
        "O painel permite comparar a presença cadastral entre estados de tamanhos diferentes e "
        "identificar UFs que merecem uma investigação mais detalhada. A população funciona como "
        "referência para que a comparação não dependa apenas do volume absoluto de cadastros."
    )

    render_definition_grid(
        [
            (
                "Registros do CNES",
                "Cadastros encontrados no arquivo processado. Não representam atendimentos realizados.",
            ),
            (
                "População estimada",
                "Estimativa anual do IBGE usada para comparar estados de tamanhos diferentes.",
            ),
            (
                "Cadastros por 100 mil habitantes",
                "Taxa entre registros e população, apresentada sem casas decimais para facilitar a leitura.",
            ),
        ]
    )

    st.info(
        "Uma taxa maior não significa, por si só, melhor oferta ou acesso à saúde. O indicador "
        "mostra presença cadastral relativa e orienta onde aprofundar a análise."
    )

    st.subheader("Compare as UFs")
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
    rate_a.metric("Taxa ponderada", format_rate(weighted_rate))
    rate_a.caption("cadastros por 100 mil habitantes")
    rate_b.metric("UFs na comparação", len(comparison))
    rate_c.metric("Maior taxa", format_rate(highest["Cadastros por 100 mil habitantes"]))
    rate_c.caption(highest["UF"])
    rate_d.metric("Menor taxa", format_rate(lowest["Cadastros por 100 mil habitantes"]))
    rate_d.caption(lowest["UF"])
    st.caption(
        "A taxa ponderada divide o total de registros pela população total das UFs selecionadas; "
        "não é a média simples das taxas estaduais."
    )

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


def bed_table(states: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(states).rename(
        columns={
            "name": "UF",
            "beds": "Leitos existentes",
            "sus_beds": "Leitos destinados ao SUS",
            "uti_beds": "Leitos de UTI",
            "uti_sus_beds": "Leitos de UTI SUS",
            "population": "População estimada",
            "beds_per_100k": "Leitos por 100 mil habitantes",
            "sus_beds_per_100k": "Leitos SUS por 100 mil habitantes",
        }
    )


def render_bed_panel(dashboard: dict, audit: dict) -> None:
    summary = dashboard["beds"]["summary"]
    states = bed_table(dashboard["beds"]["by_state"])
    competence = str(summary["competence"])
    competence_label = f"{competence[4:]}/{competence[:4]}"

    st.markdown('<p class="eyebrow">Parte 3 · Capacidade hospitalar</p>', unsafe_allow_html=True)
    st.title("Leitos hospitalares por UF")
    st.markdown(
        '<p class="deck">Uma comparação da capacidade cadastrada, separando o total de '
        "leitos e a parcela destinada ao SUS.</p>",
        unsafe_allow_html=True,
    )
    render_source_facts(
        [
            ("Competência dos leitos", competence_label),
            (
                "Arquivo informado pela fonte",
                format_source_date(audit["beds_source"]["last_modified"]),
            ),
            (
                "Painel atualizado",
                format_timestamp(dashboard["metadata"]["generated_at"]),
            ),
        ]
    )

    st.subheader("O que este painel responde")
    st.write(
        "O painel permite comparar a capacidade hospitalar cadastrada entre as UFs e observar "
        "quanto desse total está destinado ao atendimento pelo SUS. A taxa por população evita "
        "que estados maiores apareçam como mais estruturados apenas por terem mais habitantes."
    )

    render_definition_grid(
        [
            (
                "Leitos existentes",
                "Quantidade total de leitos hospitalares informada para a competência selecionada.",
            ),
            (
                "Leitos destinados ao SUS",
                "Parte do total cadastrada para atendimento pelo Sistema Único de Saúde.",
            ),
            (
                "Competência",
                "Mês mais recente do arquivo anual. O recorte evita somar meses do mesmo estabelecimento.",
            ),
        ]
    )

    st.info(
        "O cadastro descreve capacidade instalada e não informa ocupação ou disponibilidade em tempo real. "
        "Uma taxa maior também não comprova acesso, suficiência ou qualidade."
    )

    st.subheader("Compare as UFs")
    filter_states, filter_scope = st.columns([2, 1])
    with filter_states:
        selected_ufs = st.multiselect(
            "UFs para comparar (vazio = Brasil completo)",
            states["UF"].tolist(),
            placeholder="Todas as UFs",
            key="bed_state_filter",
        )
    with filter_scope:
        comparison_scope = st.selectbox(
            "Recorte da comparação",
            ["Todas as UFs selecionadas", "10 maiores taxas", "10 menores taxas"],
            key="bed_scope_filter",
        )

    if not selected_ufs:
        selected_ufs = states["UF"].tolist()
    comparison = states.loc[states["UF"].isin(selected_ufs)]
    if comparison_scope == "10 maiores taxas":
        comparison = comparison.nlargest(10, "Leitos por 100 mil habitantes")
    elif comparison_scope == "10 menores taxas":
        comparison = comparison.nsmallest(10, "Leitos por 100 mil habitantes")

    selected_beds = int(comparison["Leitos existentes"].sum())
    selected_sus_beds = int(comparison["Leitos destinados ao SUS"].sum())
    selected_population = int(comparison["População estimada"].sum())
    selected_rate = selected_beds / selected_population * 100_000
    sus_share = selected_sus_beds / selected_beds if selected_beds else 0

    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric("Leitos existentes", format_integer(selected_beds))
    metric_b.metric("Leitos destinados ao SUS", format_integer(selected_sus_beds))
    metric_c.metric("Parcela destinada ao SUS", format_percent(sus_share))
    metric_d.metric("Leitos por 100 mil", format_rate(selected_rate))
    st.caption(
        "Os indicadores acima são recalculados para as UFs exibidas. Leitos SUS estão contidos "
        "no total de leitos existentes e não devem ser somados a ele."
    )

    chart_source = comparison.copy()
    chart_source["Total"] = chart_source["Leitos por 100 mil habitantes"].round().astype(int)
    chart_source["Leitos destinados ao SUS"] = (
        chart_source["Leitos SUS por 100 mil habitantes"].round().astype(int)
    )
    chart_source["Demais leitos cadastrados"] = (
        chart_source["Total"] - chart_source["Leitos destinados ao SUS"]
    ).clip(lower=0)
    chart_source["Percentual SUS"] = chart_source.apply(
        lambda row: (
            f'{row["Leitos destinados ao SUS"] / row["Total"]:.1%} SUS'.replace(".", ",")
            if row["Total"]
            else "0,0% SUS"
        ),
        axis=1,
    )
    chart_data = chart_source.melt(
        id_vars=["UF", "Total", "Percentual SUS"],
        value_vars=["Leitos destinados ao SUS", "Demais leitos cadastrados"],
        var_name="Composição",
        value_name="Taxa",
    )
    chart_data["Ordem"] = chart_data["Composição"].map(
        {"Leitos destinados ao SUS": 0, "Demais leitos cadastrados": 1}
    )
    state_order = chart_source.sort_values("Total", ascending=False)["UF"].tolist()
    bars = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Taxa:Q", stack="zero", title="Leitos por 100 mil habitantes"),
            y=alt.Y(
                "UF:N",
                sort=state_order,
                title=None,
            ),
            color=alt.Color(
                "Composição:N",
                scale=alt.Scale(
                    domain=["Leitos destinados ao SUS", "Demais leitos cadastrados"],
                    range=["#2B716F", "#D8E0DC"],
                ),
                legend=alt.Legend(
                    labelLimit=0,
                    orient="top",
                    direction="horizontal",
                    title="Composição do total",
                ),
            ),
            order=alt.Order("Ordem:Q", sort="ascending"),
            tooltip=[
                alt.Tooltip("UF:N"),
                alt.Tooltip("Total:Q", title="Total por 100 mil", format=".0f"),
                alt.Tooltip("Composição:N"),
                alt.Tooltip("Taxa:Q", title="Taxa por 100 mil", format=".0f"),
                alt.Tooltip("Percentual SUS:N"),
            ],
        )
    )
    labels = alt.Chart(chart_source).mark_text(align="right", dx=-6, color="#183A39").encode(
        x=alt.X("Total:Q", stack=None),
        y=alt.Y(
            "UF:N",
            sort=state_order,
            title=None,
        ),
        text=alt.Text("Percentual SUS:N"),
    )
    capacity_chart = (bars + labels).properties(height=max(280, len(comparison) * 28))
    chart_tab, table_tab = st.tabs(["Comparação visual", "Dados da seleção"])
    with chart_tab:
        st.caption(
            "Cada barra representa o total da UF. Verde escuro: leitos destinados ao SUS. "
            "Verde claro: demais leitos cadastrados. O número na barra mostra a parcela SUS."
        )
        st.altair_chart(capacity_chart, width="stretch")
    with table_tab:
        st.dataframe(
            comparison[
                [
                    "UF",
                    "Leitos existentes",
                    "Leitos destinados ao SUS",
                    "Leitos por 100 mil habitantes",
                    "Leitos SUS por 100 mil habitantes",
                ]
            ].sort_values("Leitos por 100 mil habitantes", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "Leitos existentes": st.column_config.NumberColumn(format="localized"),
                "Leitos destinados ao SUS": st.column_config.NumberColumn(format="localized"),
                    "Leitos por 100 mil habitantes": st.column_config.NumberColumn(format="%.0f"),
                    "Leitos SUS por 100 mil habitantes": st.column_config.NumberColumn(format="%.0f"),
            },
        )

    st.caption(
        f"Leitos do CNES na competência {competence_label} e população estimada pelo IBGE para "
        f'{dashboard["summary"]["population_reference_year"]}. A diferença de períodos permanece '
        "visível porque as duas fontes têm ciclos de atualização distintos."
    )
    render_traceability(audit, include_population=True, include_beds=True)


def render_quality_panel(dashboard: dict, audit: dict) -> None:
    summary = dashboard["summary"]
    checks = dashboard["checks"]
    missing_location = next(item for item in checks if item["id"] == "coordinates_missing")
    approved_checks, _ = split_checks(checks)
    materiality = interpret_materiality(
        missing_location["id"], missing_location["failure_rate"]
    )

    st.markdown('<p class="eyebrow">Parte 1 · Qualidade cadastral</p>', unsafe_allow_html=True)
    st.title("CNES em Evidência")
    st.markdown(
        '<p class="deck">Uma leitura da qualidade cadastral antes de reutilizar a base '
        "em mapas, indicadores e estudos sobre a rede de saúde.</p>",
        unsafe_allow_html=True,
    )
    render_update_context(dashboard)

    st.subheader("O que este painel responde")
    st.write(
        "A primeira etapa verifica se os registros têm estrutura suficiente para sustentar "
        "as análises seguintes. Os controles procuram ausências, duplicidades e códigos fora "
        "do domínio esperado, sem transformar toda limitação em erro."
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

    st.subheader("Achado que muda o uso da base")
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
        initial_sidebar_state="auto",
    )
    st.markdown(
        """
        <style>
        :root {
            --ink: #17231f;
            --muted: #586760;
            --line: #d7dfda;
            --surface: #f7f9f7;
            --green: #176b52;
            --green-dark: #124c3c;
            --green-soft: #eaf3ee;
            --amber: #8b4a1d;
            --amber-soft: #fbf2e8;
        }
        .stApp {background: #fcfdfc;}
        .block-container {max-width: 1160px; padding-top: 3rem; padding-bottom: 5rem;}
        h1, h2, h3 {color: var(--ink); letter-spacing: -0.025em;}
        h1 {font-size: clamp(2.25rem, 5vw, 3.65rem); line-height: 1.02; margin-bottom: 0.75rem;}
        h2, h3 {margin-top: 2.4rem;}
        .eyebrow {color: var(--green); font-size: 0.72rem; font-weight: 750; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 0.65rem;}
        .deck {color: var(--muted); font-size: 1.12rem; line-height: 1.55; max-width: 780px; margin: 0 0 1.25rem;}
        .source-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); margin: 1.25rem 0 2.25rem;}
        .source-fact {background: var(--surface); padding: 0.85rem 1rem; min-height: 76px;}
        .source-fact span {display: block; color: var(--muted); font-size: 0.72rem; letter-spacing: 0.04em; margin-bottom: 0.3rem;}
        .source-fact strong {color: var(--ink); font-size: 0.92rem; font-weight: 650;}
        .definition-grid {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 1.35rem;}
        .definition {border: 1px solid var(--line); border-radius: 0.45rem; padding: 1.05rem 1.1rem; background: var(--surface);}
        .definition strong {display: block; color: var(--ink); margin-bottom: 0.45rem;}
        .definition p {color: var(--muted); font-size: 0.88rem; line-height: 1.55; margin: 0;}
        [data-testid="stMetric"] {border-top: 2px solid var(--green-dark); padding: 0.85rem 0.15rem 0;}
        [data-testid="stMetricLabel"] {color: var(--muted);}
        [data-testid="stMetricValue"] {color: var(--ink); font-size: clamp(1.75rem, 3vw, 2.2rem); letter-spacing: -0.035em;}
        [data-testid="stSidebar"] {background: #f3f6f4; border-right: 1px solid var(--line);}
        [data-testid="stSidebarNav"] a {border-radius: 0.35rem; margin: 0.25rem 0; min-height: 44px;}
        [data-testid="stSidebarNav"] a:hover {background: #e4eee8;}
        [data-testid="stTabs"] button {min-height: 44px;}
        [data-testid="stDataFrame"] {border: 1px solid var(--line); border-radius: 0.35rem; overflow: hidden;}
        .verdict {background: var(--green-soft); border-left: 4px solid var(--green); padding: 1.05rem 1.2rem; margin: 1.5rem 0 2rem;}
        .verdict strong {display: block; color: var(--ink); font-size: 1.2rem; margin: 0.2rem 0;}
        .finding {border: 1px solid #dfc8b4; background: var(--amber-soft); padding: 1.35rem; margin: 1rem 0 1.5rem;}
        .finding-grid {display: grid; grid-template-columns: minmax(110px, 0.35fr) 1fr; gap: 1.25rem; align-items: start;}
        .finding-rate {color: var(--amber); font-size: 2.5rem; font-weight: 750; line-height: 1;}
        .finding-title {color: var(--ink); font-size: 1.15rem; font-weight: 700; margin-bottom: 0.35rem;}
        .finding-copy {color: #4f4035; margin: 0.25rem 0;}
        .scope-note {border-top: 1px solid var(--line); color: var(--muted); font-size: 0.9rem; margin-top: 1rem; padding-top: 0.75rem;}
        @media (max-width: 640px) {
            .block-container {padding-top: 1.5rem;}
            .source-grid, .definition-grid {grid-template-columns: 1fr;}
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

    def bed_page_content() -> None:
        render_bed_panel(dashboard, audit)

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
    bed_page = st.Page(
        bed_page_content,
        title="3 · Capacidade hospitalar",
        icon=":material/bed:",
    )
    navigation = st.navigation(
        {"CNES em Evidência": [quality_page, population_page, bed_page]},
        position="sidebar",
    )
    navigation.run()


if __name__ == "__main__":
    render()
