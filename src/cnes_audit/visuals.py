"""Comparable bed composition; keep arithmetic exact and round only labels."""
import altair as alt
import pandas as pd

VISUAL_VERSION = "pt-BR-1"


def bed_composition(total: int, sus: int):
    if not 0 <= sus <= total:
        raise ValueError("Composição de leitos inválida")
    frame = pd.DataFrame({
        "Linha": ["Leitos", "Leitos"],
        "Parcela": ["Destinados ao SUS", "Demais leitos"],
        "Inicio": [0, sus], "Fim": [sus, total],
        "Leitos": [sus, total - sus],
    })
    chart = alt.Chart(frame).mark_bar(size=40, orient="horizontal").encode(
        x=alt.X("Inicio:Q", title="Leitos cadastrados", scale=alt.Scale(domain=[0, max(total, 1)]), axis=alt.Axis(format=",.0f")),
        x2="Fim:Q",
        y=alt.Y("Linha:N", axis=None, title=None),
        color=alt.Color("Parcela:N", scale=alt.Scale(domain=["Destinados ao SUS", "Demais leitos"], range=["#176b52", "#c6d4cf"]), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Parcela:N", alt.Tooltip("Leitos:Q", format=",.0f")],
    ).properties(height=80)
    return frame, chart


def bed_comparison(rows: list[dict], proportional: bool = False) -> tuple[pd.DataFrame, alt.LayerChart]:
    frame = pd.DataFrame(rows).copy()
    if (frame["sus_beds"] > frame["beds"]).any() or (frame[["beds", "sus_beds"]] < 0).any().any():
        raise ValueError("Composição de leitos inválida")
    factor = 100_000 / frame["population"] if proportional else 1
    frame["Total"] = frame["beds"] * factor
    frame["SUS"] = frame["sus_beds"] * factor
    frame["Demais"] = (frame["beds"] - frame["sus_beds"]) * factor
    from cnes_audit.beds import UF_CODES
    abbreviations = {value: key for key, value in UF_CODES.items()}
    frame["UF"] = frame["code"].map(abbreviations)
    order = frame.sort_values("Total", ascending=False)["UF"].tolist()
    unit = "Leitos por 100 mil habitantes" if proportional else "Leitos cadastrados"
    tooltips = [alt.Tooltip("name:N", title="UF"), alt.Tooltip("Total:Q", format=",.0f"), alt.Tooltip("SUS:Q", format=",.0f"), alt.Tooltip("Demais:Q", title="Total menos SUS", format=",.0f")]
    bars = alt.Chart(frame).mark_bar(color="#cfdbd6", size=20).encode(x=alt.X("UF:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("Total:Q", title=unit, scale=alt.Scale(zero=True), axis=alt.Axis(format=",.0f")), tooltip=tooltips)
    melted = frame.melt(id_vars=["UF", "name"], value_vars=["SUS", "Demais"], var_name="Parcela", value_name="Leitos")
    lines = alt.Chart(melted).mark_line(point=True, strokeWidth=2.5).encode(x=alt.X("UF:N", sort=order), y=alt.Y("Leitos:Q", title=unit, scale=alt.Scale(zero=True)), color=alt.Color("Parcela:N", scale=alt.Scale(domain=["SUS", "Demais"], range=["#176b52", "#a35c25"]), legend=alt.Legend(orient="bottom", title=None)), strokeDash=alt.StrokeDash("Parcela:N", scale=alt.Scale(domain=["SUS", "Demais"], range=[[1,0],[6,3]]), legend=None), tooltip=[alt.Tooltip("name:N", title="UF"), "Parcela:N", alt.Tooltip("Leitos:Q", format=",.0f")])
    return frame, (bars + lines).properties(height=380)


def bed_history_chart(rows: list[dict]):
    frame = pd.DataFrame(rows).copy()
    frame["Mês"] = pd.to_datetime(frame["competence"], format="%Y%m")
    frame["Total"] = frame["beds"]
    frame["SUS"] = frame["sus_beds"]
    frame["Demais"] = frame["beds"] - frame["sus_beds"]
    bars = alt.Chart(frame).mark_bar(color="#cfdbd6", size=20).encode(x=alt.X("Mês:T", axis=alt.Axis(format="%m/%Y")), y=alt.Y("Total:Q", title="Leitos cadastrados", scale=alt.Scale(zero=True)), tooltip=[alt.Tooltip("Mês:T", format="%m/%Y"), alt.Tooltip("Total:Q", format=",.0f")])
    lines = alt.Chart(frame.melt(id_vars=["Mês"], value_vars=["SUS", "Demais"], var_name="Parcela", value_name="Leitos")).mark_line(point=True, strokeWidth=2.5).encode(x="Mês:T", y=alt.Y("Leitos:Q", title="Leitos cadastrados"), color=alt.Color("Parcela:N", scale=alt.Scale(domain=["SUS", "Demais"], range=["#176b52", "#a35c25"]), legend=alt.Legend(orient="bottom", title=None)), strokeDash=alt.StrokeDash("Parcela:N", scale=alt.Scale(domain=["SUS", "Demais"], range=[[1,0],[6,3]]), legend=None), tooltip=[alt.Tooltip("Mês:T", format="%m/%Y"), "Parcela:N", alt.Tooltip("Leitos:Q", format=",.0f")])
    return (bars + lines).properties(height=320)
