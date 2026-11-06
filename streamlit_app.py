from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from cnes_audit.presentation import (
    describe_controls,
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


def format_signed_integer(value: int) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{format_integer(value)}"


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def format_small_percent(value: float) -> str:
    return f"{value * 100:.3f}%".replace(".", ",")


def format_rate(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def style_chart(chart):
    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            domain=False,
            gridColor="#E3E9E5",
            gridOpacity=0.75,
            labelColor="#43534D",
            labelFontSize=12,
            tickColor="#BAC6C0",
            titleColor="#2B3934",
            titleFontSize=13,
            titleFontWeight=600,
            titlePadding=12,
        )
        .configure_legend(
            labelColor="#43534D",
            labelFontSize=12,
            titleColor="#2B3934",
            titleFontSize=12,
            symbolStrokeWidth=3,
        )
    )


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
    with st.expander("Como ler esta etapa"):
        st.markdown(
            f'<div class="definition-grid">{definitions}</div>',
            unsafe_allow_html=True,
        )


def render_panel_question(title: str, description: str, accent: str) -> None:
    st.markdown(
        (
            f'<section class="analysis-intro" style="--panel-accent: {accent}">'
            '<span>O que esta etapa responde</span>'
            f'<h2>{title}</h2>'
            f'<p>{description}</p>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_scope_note(description: str) -> None:
    st.markdown(
        (
            '<div class="scope-alert"><strong>Limite de leitura</strong>'
            f"<p>{description}</p></div>"
        ),
        unsafe_allow_html=True,
    )


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


def render_update_context(dashboard: dict, source_name: str) -> None:
    render_source_facts(
        [
            ("Fonte principal", source_name),
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
    include_teams: bool = False,
    include_services: bool = False,
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
        if include_teams:
            st.write(f"**SHA-256 da consulta de equipes:** `{audit['teams_source']['sha256']}`")
            st.write(
                "**Equipes reconciliadas:** "
                f"{format_integer(audit['teams_source']['total_teams'])}"
            )
            st.link_button(
                "Consultar equipes no TabNet",
                audit["teams_source"]["catalog_url"],
            )
        if include_services:
            st.write(
                "**SHA-256 da consulta de serviços:** "
                f"`{audit['services_source']['sha256']}`"
            )
            st.write(
                "**Registros reconciliados:** "
                f"{format_integer(audit['services_source']['total_service_records'])}"
            )
            st.link_button(
                "Consultar serviços no TabNet",
                audit["services_source"]["catalog_url"],
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
        '<p class="deck">A população entra como referência para comparar a presença cadastral '
        "entre UFs de tamanhos diferentes.</p>",
        unsafe_allow_html=True,
    )
    render_update_context(dashboard, "CNES Estabelecimentos + IBGE")

    render_panel_question(
        "O volume cadastrado acompanha o tamanho da população?",
        "A leitura combina os dois valores para separar estados grandes de estados com presença "
        "cadastral proporcionalmente alta ou baixa.",
        "#2F6F83",
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

    render_scope_note(
        "Uma taxa maior não significa, por si só, melhor oferta ou acesso à saúde. O indicador "
        "mostra presença cadastral relativa e orienta onde aprofundar a análise."
    )

    st.subheader("População e volume cadastral")
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

    selected_records = int(comparison["Registros"].sum())
    selected_population = int(comparison["População estimada"].sum())
    weighted_rate = selected_records / selected_population * 100_000
    highest = comparison.nlargest(1, "Cadastros por 100 mil habitantes").iloc[0]
    lowest = comparison.nsmallest(1, "Cadastros por 100 mil habitantes").iloc[0]
    rate_range = (
        float(highest["Cadastros por 100 mil habitantes"])
        - float(lowest["Cadastros por 100 mil habitantes"])
    )

    rate_a, rate_b, rate_c, rate_d = st.columns(4)
    rate_a.metric("Cadastros no recorte", format_integer(selected_records))
    rate_b.metric("População no recorte", format_integer(selected_population))
    rate_c.metric("Taxa ponderada", format_rate(weighted_rate))
    rate_c.caption("cadastros por 100 mil habitantes")
    rate_d.metric("Distância entre as taxas", format_rate(rate_range))
    rate_d.caption(f'{lowest["UF"]} a {highest["UF"]}')
    st.caption(
        "A taxa ponderada divide o total de registros pela população total das UFs selecionadas; "
        "não é a média simples das taxas estaduais."
    )

    reference = pd.DataFrame(
        {
            "População estimada": [
                int(comparison["População estimada"].min()),
                int(comparison["População estimada"].max()),
            ]
        }
    )
    reference["Cadastros de referência"] = (
        reference["População estimada"] * weighted_rate / 100_000
    )
    reference_line = (
        alt.Chart(reference)
        .mark_line(color="#82959B", strokeDash=[6, 5], strokeWidth=2)
        .encode(
            x=alt.X("População estimada:Q", scale=alt.Scale(type="log")),
            y=alt.Y("Cadastros de referência:Q", scale=alt.Scale(type="log")),
        )
    )
    population_points = (
        alt.Chart(comparison)
        .mark_circle(size=150, opacity=0.88, stroke="#FFFFFF", strokeWidth=1)
        .encode(
            x=alt.X(
                "População estimada:Q",
                title="População estimada (escala logarítmica)",
                scale=alt.Scale(type="log"),
                axis=alt.Axis(format="~s"),
            ),
            y=alt.Y(
                "Registros:Q",
                title="Cadastros no CNES (escala logarítmica)",
                scale=alt.Scale(type="log"),
                axis=alt.Axis(format="~s"),
            ),
            color=alt.Color(
                "Cadastros por 100 mil habitantes:Q",
                title="Cadastros por 100 mil",
                scale=alt.Scale(range=["#D7E8EC", "#2F6F83"]),
            ),
            tooltip=[
                alt.Tooltip("UF:N"),
                alt.Tooltip("Registros:Q", format=",.0f"),
                alt.Tooltip("População estimada:Q", format=",.0f"),
                alt.Tooltip("Cadastros por 100 mil habitantes:Q", format=".0f"),
            ],
        )
    )
    labels = (
        alt.Chart(comparison)
        .mark_text(dx=10, dy=-8, color="#29454F", fontSize=11)
        .encode(
            x=alt.X("População estimada:Q", scale=alt.Scale(type="log")),
            y=alt.Y("Registros:Q", scale=alt.Scale(type="log")),
            text="UF:N",
        )
        if len(comparison) <= 10
        else None
    )
    relationship_chart = reference_line + population_points
    if labels is not None:
        relationship_chart += labels
    relationship_chart = relationship_chart.properties(height=430)

    relationship_chart = style_chart(relationship_chart)

    relationship_tab, rate_table_tab = st.tabs(
        ["Relação entre população e cadastros", "Ranking e valores"]
    )
    with relationship_tab:
        st.caption(
            "A linha tracejada representa a taxa ponderada do recorte. Pontos acima dela têm "
            "mais cadastros por habitante; pontos abaixo têm menos."
        )
        st.altair_chart(relationship_chart, width="stretch", theme=None)
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
        '<p class="deck">Esta etapa mostra a capacidade cadastrada em cada UF e identifica '
        "quanto do total está destinado ao SUS.</p>",
        unsafe_allow_html=True,
    )
    render_source_facts(
        [
            ("Competência dos leitos", competence_label),
            ("Fonte principal", "CNES Leitos + IBGE"),
            (
                "Painel atualizado",
                format_timestamp(dashboard["metadata"]["generated_at"]),
            ),
        ]
    )

    render_panel_question(
        "Quanto da capacidade cadastrada está destinada ao SUS?",
        "Cada barra mantém o total de leitos da UF e destaca, dentro dele, a parcela informada "
        "para atendimento pelo SUS.",
        "#176B52",
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

    render_scope_note(
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
                    orient="bottom",
                    direction="vertical",
                    columns=1,
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
    labels = alt.Chart(chart_source).mark_text(align="left", dx=7, color="#183A39").encode(
        x=alt.X("Total:Q", stack=None),
        y=alt.Y(
            "UF:N",
            sort=state_order,
            title=None,
        ),
        text=alt.Text("Percentual SUS:N"),
    )
    capacity_chart = style_chart(
        (bars + labels).properties(height=max(300, len(comparison) * 29))
    )
    chart_tab, table_tab = st.tabs(["Comparação visual", "Dados da seleção"])
    with chart_tab:
        st.caption(
            "Cada barra representa o total da UF. Verde escuro: leitos destinados ao SUS. "
            "Verde claro: demais leitos cadastrados. O percentual ao lado mostra a parcela SUS."
        )
        st.altair_chart(capacity_chart, width="stretch", theme=None)
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


def bed_history_table(rows: list[dict], scope_label: str | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(rows).rename(
        columns={
            "competence": "Competência bruta",
            "name": "UF",
            "beds": "Leitos existentes",
            "sus_beds": "Leitos destinados ao SUS",
            "uti_beds": "Leitos de UTI",
            "uti_sus_beds": "Leitos de UTI SUS",
            "population": "População estimada",
            "beds_per_100k": "Leitos por 100 mil habitantes",
            "sus_beds_per_100k": "Leitos SUS por 100 mil habitantes",
            "uti_beds_per_100k": "Leitos de UTI por 100 mil habitantes",
            "uti_sus_beds_per_100k": "Leitos de UTI SUS por 100 mil habitantes",
        }
    )
    frame["Competência"] = frame["Competência bruta"].map(
        lambda value: f"{str(value)[4:]}/{str(value)[:4]}"
    )
    frame["Data"] = pd.to_datetime(frame["Competência bruta"], format="%Y%m")
    if "UF" not in frame.columns:
        frame["UF"] = scope_label or "Brasil"
    return frame


def render_bed_history_panel(dashboard: dict, audit: dict) -> None:
    history = dashboard["bed_history"]
    summary = history["summary"]
    national = bed_history_table(history["national"], scope_label="Brasil")
    states = bed_history_table(history["by_state"])
    first_competence = str(summary["first_competence"])
    latest_competence = str(summary["latest_competence"])
    first_label = f"{first_competence[4:]}/{first_competence[:4]}"
    latest_label = f"{latest_competence[4:]}/{latest_competence[:4]}"

    st.markdown('<p class="eyebrow">Parte 6 · Evolução mensal</p>', unsafe_allow_html=True)
    st.title("Evolução dos leitos cadastrados")
    st.markdown(
        '<p class="deck">Uma série por competência para acompanhar mudanças no cadastro de '
        "leitos sem somar meses do mesmo estabelecimento.</p>",
        unsafe_allow_html=True,
    )
    render_source_facts(
        [
            ("Período comparável", f"{first_label} a {latest_label}"),
            ("Fonte principal", "CNES Leitos + IBGE"),
            (
                "População de referência",
                str(summary["population_reference_year"]),
            ),
            (
                "Painel atualizado",
                format_timestamp(dashboard["metadata"]["generated_at"]),
            ),
        ]
    )

    render_panel_question(
        "O cadastro de leitos mudou entre uma competência e outra?",
        "A série acompanha o Brasil ou até cinco UFs sem acumular meses. Total, parcela SUS e "
        "leitos de UTI continuam como medidas separadas.",
        "#2B716F",
    )
    render_definition_grid(
        [
            (
                "Competência mensal",
                "Cada ponto usa somente os registros daquele mês, sem acumular competências.",
            ),
            (
                "Variação cadastral",
                "Diferença entre competências. Pode refletir abertura, fechamento, correção ou atualização.",
            ),
            (
                "Taxa por população",
                "Relação com a estimativa anual do IBGE, mantida constante em toda a série exibida.",
            ),
        ]
    )
    render_scope_note(
        "A série descreve mudanças no cadastro. Ela não informa ocupação, disponibilidade em "
        "tempo real, demanda, acesso ou qualidade da assistência."
    )

    metric_options = {
        "Leitos existentes": {
            "count": "Leitos existentes",
            "rate": "Leitos por 100 mil habitantes",
        },
        "Leitos destinados ao SUS": {
            "count": "Leitos destinados ao SUS",
            "rate": "Leitos SUS por 100 mil habitantes",
        },
        "Leitos de UTI": {
            "count": "Leitos de UTI",
            "rate": "Leitos de UTI por 100 mil habitantes",
        },
        "Leitos de UTI SUS": {
            "count": "Leitos de UTI SUS",
            "rate": "Leitos de UTI SUS por 100 mil habitantes",
        },
    }
    filter_metric, filter_scale = st.columns([2, 1])
    with filter_metric:
        selected_metric = st.selectbox(
            "Indicador",
            list(metric_options),
            key="bed_history_metric",
        )
    with filter_scale:
        selected_scale = st.selectbox(
            "Escala",
            ["Quantidade cadastrada", "Por 100 mil habitantes"],
            key="bed_history_scale",
        )
    selected_ufs = st.multiselect(
        "UFs para comparar (vazio = Brasil)",
        sorted(states["UF"].unique()),
        max_selections=5,
        placeholder="Brasil",
        key="bed_history_states",
    )

    count_column = metric_options[selected_metric]["count"]
    rate_column = metric_options[selected_metric]["rate"]
    value_column = count_column if selected_scale == "Quantidade cadastrada" else rate_column
    if selected_ufs:
        comparison = states.loc[states["UF"].isin(selected_ufs)].copy()
        summary_series = (
            comparison.groupby(
                ["Competência bruta", "Competência", "Data"], as_index=False
            )[
                [
                    "Leitos existentes",
                    "Leitos destinados ao SUS",
                    "Leitos de UTI",
                    "Leitos de UTI SUS",
                    "População estimada",
                ]
            ]
            .sum()
            .sort_values("Data")
        )
        summary_series[rate_column] = (
            summary_series[count_column]
            / summary_series["População estimada"]
            * 100_000
        )
    else:
        comparison = national.copy()
        summary_series = national.copy().sort_values("Data")

    comparison["Valor exibido"] = comparison[value_column].round().astype(int)
    summary_series["Valor exibido"] = summary_series[value_column].round().astype(int)
    latest_value = int(summary_series.iloc[-1]["Valor exibido"])
    previous_value = (
        int(summary_series.iloc[-2]["Valor exibido"])
        if len(summary_series) > 1
        else latest_value
    )
    first_value = int(summary_series.iloc[0]["Valor exibido"])
    latest_delta = latest_value - previous_value
    period_delta = latest_value - first_value
    unit_suffix = "" if selected_scale == "Quantidade cadastrada" else " por 100 mil"

    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric(
        f"{selected_metric} em {latest_label}",
        format_integer(latest_value),
        delta=f"{format_signed_integer(latest_delta)} vs. mês anterior{unit_suffix}",
    )
    metric_b.metric(
        f"Variação desde {first_label}",
        f"{format_signed_integer(period_delta)}{unit_suffix}",
    )
    metric_c.metric("Competências comparadas", int(summary["competences"]))
    metric_d.metric("Recorte", f"{len(selected_ufs)} UFs" if selected_ufs else "Brasil")
    st.caption(
        "As variações comparam valores cadastrados entre competências. Sinal positivo ou "
        "negativo não representa melhora ou piora assistencial."
    )

    color = alt.Color(
        "UF:N",
        title="UF" if selected_ufs else None,
        legend=alt.Legend(orient="top", columns=5) if selected_ufs else None,
        scale=alt.Scale(range=["#176B52", "#2F6F83", "#955A43", "#596A91", "#B77A2F"]),
    )
    history_lines = (
        alt.Chart(comparison)
        .mark_line(point=alt.OverlayMarkDef(size=55, filled=True), strokeWidth=2.8)
        .encode(
            x=alt.X(
                "Competência:O",
                title="Competência",
                sort=alt.SortField(field="Data", order="ascending"),
                axis=alt.Axis(labelAngle=-35),
            ),
            y=alt.Y(
                "Valor exibido:Q",
                title=value_column,
                axis=alt.Axis(format=".0f"),
                scale=alt.Scale(zero=False, padding=18),
            ),
            color=color,
            order=alt.Order("Data:T"),
            tooltip=[
                alt.Tooltip("Competência:N"),
                alt.Tooltip("UF:N"),
                alt.Tooltip("Valor exibido:Q", title=value_column, format=",.0f"),
            ],
        )
    )
    latest_rows = comparison.loc[comparison["Data"] == comparison["Data"].max()].copy()
    latest_rows["Rótulo final"] = latest_rows.apply(
        lambda row: (
            f'{row["UF"]} · {format_integer(int(row["Valor exibido"]))}'
            if selected_ufs
            else format_integer(int(row["Valor exibido"]))
        ),
        axis=1,
    )
    latest_labels = (
        alt.Chart(latest_rows)
        .mark_text(align="right", dx=-8, fontSize=12, fontWeight=600)
        .encode(
            x=alt.X(
                "Competência:O",
                sort=alt.SortField(field="Data", order="ascending"),
            ),
            y=alt.Y("Valor exibido:Q"),
            color=color,
            text=alt.Text("Rótulo final:N"),
        )
    )
    history_chart = style_chart((history_lines + latest_labels).properties(height=430))
    chart_tab, data_tab = st.tabs(["Evolução", "Dados da série"])
    with chart_tab:
        st.caption("A escala vertical acompanha a faixa observada para tornar as mudanças mensais legíveis.")
        st.altair_chart(history_chart, width="stretch", theme=None)
    with data_tab:
        table = comparison[["Competência", "UF", count_column, rate_column]].copy()
        table[count_column] = table[count_column].round().astype(int)
        table[rate_column] = table[rate_column].round().astype(int)
        st.dataframe(
            table.sort_values(["Competência", "UF"]),
            width="stretch",
            hide_index=True,
            column_config={
                count_column: st.column_config.NumberColumn(format="localized"),
                rate_column: st.column_config.NumberColumn(format="%.0f"),
            },
        )

    st.caption(
        f"Competências mensais do arquivo anual de leitos do CNES. As taxas usam a população "
        f"estimada pelo IBGE para {summary['population_reference_year']} em toda a série."
    )
    render_traceability(audit, include_population=True, include_beds=True)


def team_table(states: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(states).rename(
        columns={
            "name": "UF",
            "teams": "Equipes cadastradas",
            "population": "População estimada",
            "teams_per_100k": "Equipes por 100 mil habitantes",
        }
    )


def render_team_panel(dashboard: dict, audit: dict) -> None:
    summary = dashboard["teams"]["summary"]
    states = team_table(dashboard["teams"]["by_state"])
    state_types = pd.DataFrame(dashboard["teams"]["by_state_type"])
    competence = str(summary["competence"])
    competence_label = f"{competence[4:]}/{competence[:4]}"

    st.markdown('<p class="eyebrow">Parte 4 · Equipes de saúde</p>', unsafe_allow_html=True)
    st.title("Equipes de saúde por UF")
    st.markdown(
        '<p class="deck">Uma leitura dos registros de equipes ativas no CNES, com comparação '
        "entre estados e abertura pelos tipos informados na fonte.</p>",
        unsafe_allow_html=True,
    )
    render_source_facts(
        [
            ("Competência das equipes", competence_label),
            ("Fonte principal", "CNES Equipes + IBGE"),
            (
                "Painel atualizado",
                format_timestamp(dashboard["metadata"]["generated_at"]),
            ),
        ]
    )

    render_panel_question(
        "Quais tipos de equipe formam o recorte analisado?",
        "A composição por tipo vem primeiro. A comparação territorial entra depois, para mostrar "
        "onde esses registros estão mais ou menos presentes em relação à população.",
        "#596A91",
    )
    render_definition_grid(
        [
            (
                "Equipes cadastradas",
                "Registros ativos encontrados no CNES para a competência consultada.",
            ),
            (
                "Equipes por 100 mil habitantes",
                "Relação entre os registros de equipes e a estimativa populacional do IBGE.",
            ),
            (
                "Tipo de equipe",
                "Classificação mantida como aparece no TabNet, sem reunir categorias diferentes.",
            ),
        ]
    )
    render_scope_note(
        "O total reúne registros de equipes ativas e não representa quantidade de profissionais, "
        "atendimentos realizados, cobertura efetiva ou qualidade da assistência."
    )

    st.subheader("Monte o recorte de equipes")
    filter_states, filter_scope = st.columns([2, 1])
    with filter_states:
        selected_ufs = st.multiselect(
            "UFs para comparar (vazio = Brasil completo)",
            states["UF"].tolist(),
            placeholder="Todas as UFs",
            key="team_state_filter",
        )
    with filter_scope:
        comparison_scope = st.selectbox(
            "Recorte da comparação",
            ["Todas as UFs selecionadas", "10 maiores taxas", "10 menores taxas"],
            key="team_scope_filter",
        )

    if not selected_ufs:
        selected_ufs = states["UF"].tolist()
    comparison = states.loc[states["UF"].isin(selected_ufs)]
    if comparison_scope == "10 maiores taxas":
        comparison = comparison.nlargest(10, "Equipes por 100 mil habitantes")
    elif comparison_scope == "10 menores taxas":
        comparison = comparison.nsmallest(10, "Equipes por 100 mil habitantes")

    displayed_ufs = comparison["UF"].tolist()
    selected_types = state_types.loc[state_types["state_name"].isin(displayed_ufs)]
    type_totals = (
        selected_types.groupby(["team_code", "team_name"], as_index=False)["teams"]
        .sum()
        .sort_values("teams", ascending=False)
    )
    selected_teams = int(comparison["Equipes cadastradas"].sum())
    selected_population = int(comparison["População estimada"].sum())
    selected_rate = selected_teams / selected_population * 100_000
    top_type = type_totals.iloc[0]

    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric("Equipes cadastradas", format_integer(selected_teams))
    metric_b.metric("Equipes por 100 mil", format_rate(selected_rate))
    metric_c.metric("Tipos presentes", len(type_totals))
    metric_d.metric("Maior grupo", format_integer(int(top_type["teams"])))
    metric_d.caption(f'{top_type["team_code"]} · {top_type["team_name"].split(" - ", 1)[0]}')
    st.caption(
        "Os indicadores são recalculados para as UFs exibidas. A taxa usa a soma das equipes "
        "e da população do recorte, sem média simples entre estados."
    )

    state_chart_source = comparison.copy()
    state_chart_source["Início"] = 0
    state_order = state_chart_source.sort_values(
        "Equipes por 100 mil habitantes", ascending=False
    )["UF"].tolist()
    state_rules = (
        alt.Chart(state_chart_source)
        .mark_rule(color="#C8D0DD", strokeWidth=3)
        .encode(
            x=alt.X("Início:Q", title="Equipes por 100 mil habitantes"),
            x2=alt.X2("Equipes por 100 mil habitantes:Q"),
            y=alt.Y("UF:N", sort=state_order, title=None),
        )
    )
    state_points = (
        alt.Chart(state_chart_source)
        .mark_point(color="#596A91", filled=True, size=105)
        .encode(
            x=alt.X(
                "Equipes por 100 mil habitantes:Q",
                title="Equipes por 100 mil habitantes",
            ),
            y=alt.Y("UF:N", sort=state_order, title=None),
            tooltip=[
                alt.Tooltip("UF:N"),
                alt.Tooltip("Equipes cadastradas:Q", format=",.0f"),
                alt.Tooltip("População estimada:Q", format=",.0f"),
                alt.Tooltip("Equipes por 100 mil habitantes:Q", format=".0f"),
            ],
        )
    )
    state_chart = style_chart(
        (state_rules + state_points).properties(height=max(300, len(comparison) * 26))
    )
    type_chart_data = type_totals.head(10).copy()
    if len(type_totals) > 10:
        remaining = pd.DataFrame(
            [
                {
                    "team_code": "—",
                    "team_name": f"Demais {len(type_totals) - 10} tipos",
                    "teams": int(type_totals.iloc[10:]["teams"].sum()),
                }
            ]
        )
        type_chart_data = pd.concat([type_chart_data, remaining], ignore_index=True)
    type_chart_data["Participação"] = (
        type_chart_data["teams"] / selected_teams if selected_teams else 0
    )
    type_chart_data["Tipo"] = type_chart_data.apply(
        lambda row: (
            row["team_name"]
            if row["team_code"] == "—"
            else f'{row["team_code"]} · {row["team_name"].split(" - ", 1)[0]}'
        ),
        axis=1,
    )
    type_chart_data["Rótulo"] = type_chart_data.apply(
        lambda row: (
            f'{format_integer(int(row["teams"]))} · {format_percent(row["Participação"])}'
        ),
        axis=1,
    )
    type_order = type_chart_data.sort_values("teams", ascending=False)["Tipo"].tolist()
    type_bars = (
        alt.Chart(type_chart_data)
        .mark_bar(color="#596A91", cornerRadiusEnd=4)
        .encode(
            x=alt.X("teams:Q", title="Equipes cadastradas"),
            y=alt.Y(
                "Tipo:N",
                sort=type_order,
                title=None,
            ),
            tooltip=[
                alt.Tooltip("team_code:N", title="Código"),
                alt.Tooltip("team_name:N", title="Tipo informado"),
                alt.Tooltip("teams:Q", title="Equipes", format=",.0f"),
                alt.Tooltip("Participação:Q", title="Participação no recorte", format=".1%"),
            ],
        )
    )
    type_labels = (
        alt.Chart(type_chart_data)
        .mark_text(align="left", dx=7, color="#34403C", fontSize=11)
        .encode(
            x=alt.X("teams:Q"),
            y=alt.Y(
                "Tipo:N",
                sort=type_order,
            ),
            text=alt.Text("Rótulo:N"),
        )
    )
    type_chart = style_chart(
        (type_bars + type_labels).properties(height=max(350, len(type_chart_data) * 36))
    )

    type_tab, state_tab, data_tab = st.tabs(
        ["Composição por tipo", "Distribuição por UF", "Dados da seleção"]
    )
    with type_tab:
        st.caption(
            "Os tipos aparecem exatamente como publicados no TabNet. Categorias históricas e "
            "atuais continuam separadas para não alterar o significado da fonte."
        )
        st.altair_chart(type_chart, width="stretch", theme=None)
    with state_tab:
        st.caption(
            "Cada ponto representa uma UF. A posição mostra os registros de equipes em relação "
            "à população estimada."
        )
        st.altair_chart(state_chart, width="stretch", theme=None)
    with data_tab:
        st.dataframe(
            comparison[
                [
                    "UF",
                    "Equipes cadastradas",
                    "População estimada",
                    "Equipes por 100 mil habitantes",
                ]
            ].sort_values("Equipes por 100 mil habitantes", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "Equipes cadastradas": st.column_config.NumberColumn(format="localized"),
                "População estimada": st.column_config.NumberColumn(format="localized"),
                "Equipes por 100 mil habitantes": st.column_config.NumberColumn(format="%.0f"),
            },
        )

    st.caption(
        f"Equipes ativas do CNES na competência {competence_label} e população estimada "
        f'pelo IBGE para {dashboard["summary"]["population_reference_year"]}. Os ciclos das '
        "fontes são diferentes e permanecem identificados."
    )
    render_traceability(audit, include_population=True, include_teams=True)


def service_table(states: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(states).rename(
        columns={
            "name": "UF",
            "service_records": "Registros de serviço/classificação",
            "population": "População estimada",
            "service_records_per_100k": "Registros por 100 mil habitantes",
        }
    )


def render_service_panel(dashboard: dict, audit: dict) -> None:
    summary = dashboard["services"]["summary"]
    states = service_table(dashboard["services"]["by_state"])
    state_classifications = pd.DataFrame(
        dashboard["services"]["by_state_classification"]
    )
    competence = str(summary["competence"])
    competence_label = f"{competence[4:]}/{competence[:4]}"

    st.markdown('<p class="eyebrow">Parte 5 · Serviços cadastrados</p>', unsafe_allow_html=True)
    st.title("Serviços de saúde registrados no CNES")
    st.markdown(
        '<p class="deck">Escolha uma classificação e veja como seus registros se distribuem '
        "entre as unidades federativas.</p>",
        unsafe_allow_html=True,
    )
    render_source_facts(
        [
            ("Competência dos serviços", competence_label),
            ("Fonte principal", "CNES Serviços + IBGE"),
            ("Painel atualizado", format_timestamp(dashboard["metadata"]["generated_at"])),
        ]
    )

    render_panel_question(
        "Onde uma classificação de serviço aparece no cadastro?",
        "Em vez de resumir todas as classificações em uma única taxa, esta etapa permite escolher "
        "uma delas e observar sua distribuição entre as UFs.",
        "#955A43",
    )
    render_definition_grid(
        [
            (
                "Registros de serviço/classificação",
                "Quantidade informada pelo TabNet para cada combinação de serviço e classificação.",
            ),
            (
                "Registros por 100 mil habitantes",
                "Relação entre esses registros e a estimativa populacional do IBGE.",
            ),
            (
                "Classificação",
                "Detalhamento mantido com o código e a descrição publicados pelo CNES.",
            ),
        ]
    )
    render_scope_note(
        "O cadastro indica que uma classificação foi informada ao CNES. "
        "Ele não comprova atendimento realizado, disponibilidade operacional, "
        "capacidade instalada ou produção."
    )

    classification_totals = (
        state_classifications.groupby(
            [
                "classification_code",
                "service_code",
                "service_name",
                "classification_name",
            ],
            as_index=False,
        )["service_records"]
        .sum()
        .sort_values("service_records", ascending=False)
    )
    classification_totals["Opção"] = classification_totals.apply(
        lambda row: (
            f'{row["classification_code"]} · {str(row["service_name"]).title()} / '
            f'{str(row["classification_name"]).title()}'
        ),
        axis=1,
    )

    st.subheader("Explore uma classificação")
    classification_filter, scope_filter = st.columns([2, 1])
    with classification_filter:
        selected_option = st.selectbox(
            "Classificação do serviço",
            classification_totals["Opção"].tolist(),
            key="service_classification_filter",
        )
    with scope_filter:
        comparison_scope = st.selectbox(
            "Estados exibidos",
            ["Todas as UFs", "10 maiores taxas", "10 maiores volumes"],
            key="service_scope_filter",
        )

    selected_definition = classification_totals.loc[
        classification_totals["Opção"] == selected_option
    ].iloc[0]
    selected_rows = state_classifications.loc[
        (state_classifications["classification_code"] == selected_definition["classification_code"])
        & (state_classifications["service_code"] == selected_definition["service_code"])
    ][["state_name", "service_records"]].rename(
        columns={"state_name": "UF", "service_records": "Registros da classificação"}
    )
    classification_states = states[["UF", "População estimada"]].merge(
        selected_rows,
        on="UF",
        how="left",
    )
    classification_states["Registros da classificação"] = (
        classification_states["Registros da classificação"].fillna(0).astype(int)
    )
    classification_states["Registros por 100 mil habitantes"] = (
        classification_states["Registros da classificação"]
        / classification_states["População estimada"]
        * 100_000
    )
    classification_comparison = classification_states.copy()
    if comparison_scope == "10 maiores taxas":
        classification_comparison = classification_comparison.nlargest(
            10, "Registros por 100 mil habitantes"
        )
    elif comparison_scope == "10 maiores volumes":
        classification_comparison = classification_comparison.nlargest(
            10, "Registros da classificação"
        )

    selected_records = int(classification_states["Registros da classificação"].sum())
    selected_population = int(states["População estimada"].sum())
    selected_rate = selected_records / selected_population * 100_000
    states_with_records = int(
        (classification_states["Registros da classificação"] > 0).sum()
    )

    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Registros da classificação", format_integer(selected_records))
    metric_b.metric("UFs com registro", states_with_records)
    metric_c.metric("Taxa nacional", format_rate(selected_rate))
    metric_c.caption("registros por 100 mil habitantes")
    st.caption(
        f'Serviço {selected_definition["service_code"]} · '
        f'{str(selected_definition["service_name"]).title()}. '
        f'{len(classification_totals)} classificações estão disponíveis. '
        "Ausência de registro não comprova ausência do serviço."
    )

    classification_chart_data = classification_comparison.copy()
    classification_chart_data["Início"] = 0
    classification_chart_data["Posição"] = classification_chart_data[
        "Registros por 100 mil habitantes"
    ].apply(
        lambda value: "Acima da taxa nacional"
        if value >= selected_rate
        else "Abaixo da taxa nacional"
    )
    classification_order = classification_chart_data.sort_values(
        "Registros por 100 mil habitantes", ascending=False
    )["UF"].tolist()
    classification_rules = (
        alt.Chart(classification_chart_data)
        .mark_rule(color="#E1D2CB", strokeWidth=3)
        .encode(
            x=alt.X(
                "Início:Q",
                title="Registros da classificação por 100 mil habitantes",
            ),
            x2=alt.X2("Registros por 100 mil habitantes:Q"),
            y=alt.Y("UF:N", sort=classification_order, title=None),
        )
    )
    classification_points = (
        alt.Chart(classification_chart_data)
        .mark_point(filled=True, size=105)
        .encode(
            x=alt.X(
                "Registros por 100 mil habitantes:Q",
                title="Registros da classificação por 100 mil habitantes",
            ),
            y=alt.Y("UF:N", sort=classification_order, title=None),
            color=alt.Color(
                "Posição:N",
                scale=alt.Scale(
                    domain=["Acima da taxa nacional", "Abaixo da taxa nacional"],
                    range=["#955A43", "#C8A99A"],
                ),
                legend=alt.Legend(
                    orient="bottom", direction="vertical", columns=1, title=None
                ),
            ),
            tooltip=[
                alt.Tooltip("UF:N"),
                alt.Tooltip("Registros da classificação:Q", format=",.0f"),
                alt.Tooltip("População estimada:Q", format=",.0f"),
                alt.Tooltip("Registros por 100 mil habitantes:Q", format=".0f"),
            ],
        )
    )
    national_reference = (
        alt.Chart(pd.DataFrame({"Taxa nacional": [selected_rate]}))
        .mark_rule(color="#603927", strokeDash=[6, 4], strokeWidth=2)
        .encode(x=alt.X("Taxa nacional:Q"))
    )
    classification_state_chart = style_chart(
        (classification_rules + classification_points + national_reference).properties(
            height=max(320, len(classification_comparison) * 26)
        )
    )

    location_tab, overview_tab, data_tab = st.tabs(
        ["Onde aparece", "Visão geral da fonte", "Dados da classificação"]
    )
    with location_tab:
        st.caption(
            "O gráfico usa somente a classificação escolhida. Os valores são proporcionais à "
            "população para permitir comparação entre estados de tamanhos diferentes."
        )
        st.caption("A linha tracejada marca a taxa nacional da classificação selecionada.")
        st.altair_chart(classification_state_chart, width="stretch", theme=None)
    with overview_tab:
        st.caption(
            "As doze classificações com mais registros ajudam a dimensionar a fonte, mas não "
            "substituem a análise individual de cada categoria."
        )
        overview_data = classification_totals.head(12).copy()
        st.dataframe(
            overview_data[
                ["classification_code", "service_name", "classification_name", "service_records"]
            ].rename(
                columns={
                    "classification_code": "Código",
                    "service_name": "Serviço",
                    "classification_name": "Classificação",
                    "service_records": "Registros",
                }
            ),
            width="stretch",
            hide_index=True,
            column_config={"Registros": st.column_config.NumberColumn(format="localized")},
        )
    with data_tab:
        table = classification_states.copy()
        table["Registros por 100 mil habitantes"] = (
            table["Registros por 100 mil habitantes"].round().astype(int)
        )
        st.dataframe(
            table.sort_values("Registros por 100 mil habitantes", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "Registros da classificação": st.column_config.NumberColumn(
                    format="localized"
                ),
                "População estimada": st.column_config.NumberColumn(format="localized"),
                "Registros por 100 mil habitantes": st.column_config.NumberColumn(
                    format="%.0f"
                ),
            },
        )

    st.caption(
        f"Serviços e classificações do CNES na competência {competence_label} e população "
        f'estimada pelo IBGE para {dashboard["summary"]["population_reference_year"]}. '
        "As referências temporais permanecem identificadas porque as fontes têm ciclos próprios."
    )
    render_traceability(audit, include_population=True, include_services=True)


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
        '<p class="deck">Antes de usar o CNES em mapas ou indicadores, esta etapa verifica '
        "se os campos necessários sustentam a análise.</p>",
        unsafe_allow_html=True,
    )
    render_update_context(dashboard, "CNES Estabelecimentos")

    render_panel_question(
        "A base sustenta as análises que vêm depois?",
        "Os controles procuram ausências, duplicidades e códigos fora do domínio esperado. "
        "O objetivo é separar o que pode ser usado do que exige cuidado adicional.",
        "#8B4A1D",
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

    states["Início"] = 0
    states["Leitura"] = states["Taxa de ocorrências"].apply(
        lambda value: "Acima da taxa nacional"
        if value >= missing_location["failure_rate"]
        else "Abaixo da taxa nacional"
    )
    quality_order = states.sort_values("Taxa de ocorrências", ascending=False)["UF"].tolist()
    quality_rules = (
        alt.Chart(states)
        .mark_rule(color="#E2D2C4", strokeWidth=3)
        .encode(
            x=alt.X("Início:Q", title="Registros sem o par completo de coordenadas"),
            x2=alt.X2("Taxa de ocorrências:Q"),
            y=alt.Y("UF:N", sort=quality_order, title=None),
        )
    )
    quality_points = (
        alt.Chart(states)
        .mark_point(filled=True, size=105)
        .encode(
            x=alt.X(
                "Taxa de ocorrências:Q",
                title="Registros sem o par completo de coordenadas",
                axis=alt.Axis(format=".0%"),
            ),
            y=alt.Y("UF:N", sort=quality_order, title=None),
            color=alt.Color(
                "Leitura:N",
                scale=alt.Scale(
                    domain=["Acima da taxa nacional", "Abaixo da taxa nacional"],
                    range=["#8B4A1D", "#D3AD8E"],
                ),
                legend=alt.Legend(
                    orient="bottom", direction="vertical", columns=1, title=None
                ),
            ),
            tooltip=[
                alt.Tooltip("UF:N"),
                alt.Tooltip("Registros:Q", format=",.0f"),
                alt.Tooltip("Ocorrências:Q", format=",.0f"),
                alt.Tooltip("Taxa de ocorrências:Q", format=".1%"),
            ],
        )
    )
    quality_reference = (
        alt.Chart(pd.DataFrame({"Taxa nacional": [missing_location["failure_rate"]]}))
        .mark_rule(color="#5E3217", strokeDash=[6, 4], strokeWidth=2)
        .encode(x=alt.X("Taxa nacional:Q"))
    )
    quality_chart = style_chart(
        (quality_rules + quality_points + quality_reference).properties(height=620)
    )

    chart_tab, table_tab = st.tabs(["Impacto geográfico por UF", "Tabela completa"])
    with chart_tab:
        st.caption(
            "Cada ponto mostra a parcela de registros sem latitude e longitude completas. "
            "A linha tracejada representa a taxa nacional."
        )
        st.altair_chart(quality_chart, width="stretch", theme=None)
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
    management = pd.DataFrame(management_rows)
    management["Participação"] = management["records"] / summary["total_records"]
    management["Rótulo"] = management.apply(
        lambda row: (
            f'{format_integer(int(row["records"]))} · {format_percent(row["Participação"])}'
        ),
        axis=1,
    )
    management["Situação"] = management["code"].map(
        lambda code: "Sem informação" if code == "S" else "Gestão informada"
    )
    management_order = management.sort_values("records", ascending=False)["label"].tolist()
    management_bars = (
        alt.Chart(management)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("records:Q", title="Registros"),
            y=alt.Y(
                "label:N",
                sort=management_order,
                title=None,
            ),
            color=alt.Color(
                "Situação:N",
                scale=alt.Scale(
                    domain=["Gestão informada", "Sem informação"],
                    range=["#2B716F", "#B26A3B"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("label:N", title="Tipo de gestão"),
                alt.Tooltip("records:Q", title="Registros", format=",.0f"),
                alt.Tooltip("Participação:Q", format=".3%"),
            ],
        )
    )
    management_labels = (
        alt.Chart(management)
        .mark_text(align="left", dx=7, color="#34403C", fontSize=11)
        .encode(
            x=alt.X("records:Q"),
            y=alt.Y(
                "label:N",
                sort=management_order,
            ),
            text=alt.Text("Rótulo:N"),
        )
    )
    management_distribution = style_chart(
        (management_bars + management_labels).properties(height=220)
    )
    management_chart, management_note = st.columns([3, 1])
    with management_chart:
        st.altair_chart(management_distribution, width="stretch", theme=None)
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
            --line: #cfd8d3;
            --surface: #f5f4ef;
            --green: #176b52;
            --green-dark: #124c3c;
            --green-soft: #eaf3ee;
            --amber: #8b4a1d;
            --amber-soft: #fbf2e8;
        }
        .stApp {background: #fbfaf6;}
        .block-container {max-width: 1240px; padding-top: 3.4rem; padding-bottom: 5rem;}
        h1, h2, h3 {color: var(--ink); letter-spacing: -0.025em;}
        h1 {font-size: clamp(2.35rem, 5vw, 4rem); line-height: 1; margin-bottom: 0.85rem; max-width: 930px;}
        h2, h3 {margin-top: 2.7rem;}
        .eyebrow {color: var(--green); font-size: 0.72rem; font-weight: 750; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 0.65rem;}
        .deck {color: var(--muted); font-size: 1.12rem; line-height: 1.55; max-width: 780px; margin: 0 0 1.25rem;}
        .analysis-intro {border-top: 2px solid var(--panel-accent); border-bottom: 1px solid var(--line); padding: 1.2rem 0 1.35rem; margin: 2.2rem 0 1rem; display: grid; grid-template-columns: minmax(150px,.34fr) minmax(0,1fr); column-gap: 2rem;}
        .analysis-intro span {color: var(--panel-accent); display: block; font-size: 0.68rem; font-weight: 750; letter-spacing: 0.12em; text-transform: uppercase; padding-top: .3rem;}
        .analysis-intro h2 {font-size: 1.55rem; line-height: 1.22; margin: 0;}
        .analysis-intro p {color: var(--muted); line-height: 1.55; margin: 0.6rem 0 0; max-width: 860px; grid-column: 2;}
        .source-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); margin: 1.4rem 0 2.4rem;}
        .source-fact {padding: 0.9rem 1rem 0.9rem 0; min-height: 72px;}
        .source-fact + .source-fact {border-left: 1px solid var(--line); padding-left: 1rem;}
        .source-fact span {display: block; color: var(--muted); font-size: 0.72rem; letter-spacing: 0.04em; margin-bottom: 0.3rem;}
        .source-fact strong {color: var(--ink); font-size: 0.92rem; font-weight: 650;}
        .definition-grid {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.3rem; margin: 0.4rem 0 0.7rem;}
        .definition {border-top: 2px solid var(--line); padding: 0.85rem 0 0;}
        .definition strong {display: block; color: var(--ink); margin-bottom: 0.45rem;}
        .definition p {color: var(--muted); font-size: 0.88rem; line-height: 1.55; margin: 0;}
        .scope-alert {border-left: 3px solid var(--amber); margin: 1.1rem 0 1.8rem; padding: .2rem 0 .2rem 1rem; max-width: 980px;}
        .scope-alert strong {color: var(--amber); display: block; font-size: .72rem; letter-spacing: .09em; text-transform: uppercase; margin-bottom: .25rem;}
        .scope-alert p {color: var(--muted); line-height: 1.55; margin: 0;}
        [data-testid="stMetric"] {border-top: 2px solid var(--green-dark); padding: 0.9rem 0.15rem 0;}
        [data-testid="stMetricLabel"] {color: var(--muted);}
        [data-testid="stMetricValue"] {color: var(--ink); font-size: clamp(1.75rem, 3vw, 2.2rem); letter-spacing: -0.035em;}
        [data-testid="stSidebar"] {background: #f3f6f4; border-right: 1px solid var(--line);}
        [data-testid="stSidebarNav"] a {border-radius: 0.35rem; margin: 0.25rem 0; min-height: 44px;}
        [data-testid="stSidebarNav"] a:hover {background: #e4eee8;}
        [data-testid="stTabs"] button {min-height: 44px; font-weight: 650;}
        [data-testid="stExpander"] {border: 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); border-radius: 0; background: transparent; margin: 1rem 0 1.2rem;}
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
            .block-container {padding-top: 3.25rem;}
            .source-grid, .definition-grid {grid-template-columns: 1fr;}
            .source-fact + .source-fact {border-left: 0; border-top: 1px solid var(--line); padding-left: 0;}
            .analysis-intro {grid-template-columns: 1fr; gap: .45rem;}
            .analysis-intro p {grid-column: 1;}
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

    def team_page_content() -> None:
        render_team_panel(dashboard, audit)

    def service_page_content() -> None:
        render_service_panel(dashboard, audit)

    def bed_history_page_content() -> None:
        render_bed_history_panel(dashboard, audit)

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
    team_page = st.Page(
        team_page_content,
        title="4 · Equipes de saúde",
        icon=":material/groups:",
    )
    service_page = st.Page(
        service_page_content,
        title="5 · Serviços cadastrados",
        icon=":material/medical_services:",
    )
    bed_history_page = st.Page(
        bed_history_page_content,
        title="6 · Evolução mensal de leitos",
        icon=":material/timeline:",
    )
    navigation = st.navigation(
        {
            "CNES em Evidência": [
                quality_page,
                population_page,
                bed_page,
                team_page,
                service_page,
                bed_history_page,
            ]
        },
        position="sidebar",
    )
    navigation.run()


if __name__ == "__main__":
    render()
