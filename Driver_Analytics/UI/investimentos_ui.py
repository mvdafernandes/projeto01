"""Investimentos UI page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from Metrics import analytics_investimentos as invest_metrics
from services.dashboard_service import DashboardService
from UI.components import format_currency, render_kpi, show_empty_data, titulo_secao


service = DashboardService()


def pagina_investimentos() -> None:
    st.header("Investimentos")
    st.info("Cadastros e edições agora ficam na página Cadastros.")

    df = service.listar_investimentos()
    if not df.empty and "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")

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

    titulo_secao("Registros")
    df_tabela = df.copy()
    if "data" in df_tabela.columns:
        df_tabela["data"] = pd.to_datetime(df_tabela["data"], errors="coerce").dt.date
    st.dataframe(df_tabela, width="stretch")
