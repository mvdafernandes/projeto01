"""Investimentos UI page (visualization only)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from Metrics import analytics_investimentos as invest_metrics
from services.dashboard_service import DashboardService
from UI.components import format_currency, formatar_moeda, render_graph, render_kpi, show_empty_data, titulo_secao


service = DashboardService()


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "data" in out.columns:
        out["data"] = pd.to_datetime(out["data"], errors="coerce").dt.date
    for col in ["aporte", "total aportado", "rendimento", "patrimonio total"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).apply(formatar_moeda)
    return out


def pagina_investimentos() -> None:
    st.header("Investimentos")
    st.info("Cadastros e edições agora ficam na página Cadastros.")

    df = service.listar_investimentos()
    if not df.empty and "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    if "categoria" not in df.columns and not df.empty:
        df["categoria"] = "Renda Fixa"

    df_metrics = df.rename(columns={"total aportado": "total_aportado", "patrimonio total": "patrimonio_total"})

    titulo_secao("Resumo")
    if df_metrics.empty:
        patrimonio = 0.0
        total_aporte = 0.0
        lucro = 0.0
        rent = 0.0
    else:
        patrimonio = invest_metrics.patrimonio_atual(df_metrics)
        total_aporte = invest_metrics.total_aportado(df_metrics)
        lucro = invest_metrics.lucro_acumulado(df_metrics)
        rent = invest_metrics.rentabilidade_percentual(df_metrics)

    row1 = st.columns(2)
    with row1[0]:
        render_kpi("Patrimônio atual", format_currency(patrimonio))
    with row1[1]:
        render_kpi("Total aportado", format_currency(total_aporte))

    row2 = st.columns(2)
    with row2[0]:
        render_kpi("Lucro acumulado", format_currency(lucro))
    with row2[1]:
        render_kpi("Rentabilidade", f"{float(rent):.2f}%")

    titulo_secao("Evolução")
    if not df_metrics.empty and {"data", "patrimonio_total"}.issubset(df_metrics.columns):
        resumo = df_metrics.groupby("data")["patrimonio_total"].last()
        st.line_chart(resumo)
    else:
        show_empty_data()

    titulo_secao("Composição RF x RV")
    if not df_metrics.empty and {"categoria", "patrimonio_total"}.issubset(df_metrics.columns):
        comp = df_metrics.copy()
        comp["categoria"] = comp["categoria"].fillna("Renda Fixa").astype(str)
        comp["patrimonio_total"] = pd.to_numeric(comp["patrimonio_total"], errors="coerce").fillna(0.0)
        comp = comp.groupby("categoria", as_index=False)["patrimonio_total"].sum()
        comp = comp[comp["categoria"].isin(["Renda Fixa", "Renda Variável"])]

        if comp.empty:
            show_empty_data("Sem dados de categoria para compor o gráfico.")
        else:
            fig_donut = px.pie(
                comp,
                values="patrimonio_total",
                names="categoria",
                hole=0.55,
                color="categoria",
                color_discrete_map={"Renda Fixa": "#1f77b4", "Renda Variável": "#ff7f0e"},
            )
            fig_donut.update_traces(textposition="inside", textinfo="percent+label")
            fig_donut.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
            render_graph(fig_donut, height=400, show_legend=True)

    titulo_secao("Comparativo de Rendimentos")
    if not df_metrics.empty and {"categoria", "rendimento"}.issubset(df_metrics.columns):
        rend = df_metrics.copy()
        rend["categoria"] = rend["categoria"].fillna("Renda Fixa").astype(str)
        rend["rendimento"] = pd.to_numeric(rend["rendimento"], errors="coerce").fillna(0.0)
        rend = rend.groupby("categoria", as_index=False)["rendimento"].sum()
        rend = rend[rend["categoria"].isin(["Renda Fixa", "Renda Variável"])]

        if rend.empty:
            show_empty_data("Sem rendimentos por categoria para mostrar.")
        else:
            total_rend = float(rend["rendimento"].sum())
            rend["participacao_pct"] = rend["rendimento"].apply(lambda x: 0.0 if total_rend == 0 else (float(x) / total_rend) * 100)
            rend["label"] = rend.apply(lambda r: f"{formatar_moeda(r['rendimento'])} ({r['participacao_pct']:.1f}%)", axis=1)

            fig_bar = px.bar(
                rend,
                x="categoria",
                y="rendimento",
                color="categoria",
                text="label",
                color_discrete_map={"Renda Fixa": "#1f77b4", "Renda Variável": "#ff7f0e"},
            )
            fig_bar.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), xaxis_title=None, yaxis_title="Rendimento (R$)")
            fig_bar.update_traces(textposition="outside")
            render_graph(fig_bar, height=400, show_legend=False)

    titulo_secao("Registros")
    st.dataframe(_format_table(df), width="stretch")
