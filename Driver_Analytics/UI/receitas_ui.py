"""Receitas UI page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import format_currency, format_percent, render_kpi, show_empty_data, titulo_secao


service = DashboardService()


def _format_hms(total_seconds: float) -> str:
    seconds = int(total_seconds)
    horas = seconds // 3600
    minutos = (seconds % 3600) // 60
    segundos = seconds % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def pagina_receitas() -> None:
    st.header("Receitas")
    st.info("Cadastros e edições agora ficam na página Cadastros.")

    df = service.listar_receitas()
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    if "tempo trabalhado" in df.columns:
        df["tempo trabalhado"] = pd.to_numeric(df["tempo trabalhado"], errors="coerce").fillna(0).astype(int)

    col1, col2 = st.columns(2)
    with col1:
        ano = st.number_input("Ano", min_value=2020, max_value=2100, value=pd.Timestamp.today().year)
    with col2:
        mes = st.number_input("Mês", min_value=1, max_value=12, value=pd.Timestamp.today().month)

    df_mes = df.copy()
    if not df_mes.empty and "data" in df_mes.columns:
        df_mes = df_mes[(df_mes["data"].dt.year == int(ano)) & (df_mes["data"].dt.month == int(mes))]

    titulo_secao("Resumo do Mês")
    total = service.metrics.receita_total(df_mes)
    media = service.metrics.receita_media_diaria(df_mes)
    dias = service.metrics.dias_trabalhados(df_mes)
    meta_pct = service.metrics.percentual_meta_batida(df_mes)

    row1 = st.columns(2)
    with row1[0]:
        render_kpi("Total", format_currency(total))
    with row1[1]:
        render_kpi("Média diária", format_currency(media))

    row2 = st.columns(2)
    with row2[0]:
        render_kpi("Dias trabalhados", dias)
    with row2[1]:
        render_kpi("% Meta 300", format_percent(meta_pct))

    titulo_secao("Evolução Diária")
    if not df_mes.empty and {"data", "valor"}.issubset(df_mes.columns):
        resumo = df_mes.groupby("data")["valor"].sum()
        st.line_chart(resumo)
    else:
        show_empty_data()

    titulo_secao("Registros")
    df_tabela = df_mes.copy()
    if "data" in df_tabela.columns:
        df_tabela["data"] = pd.to_datetime(df_tabela["data"], errors="coerce").dt.date
    if "tempo trabalhado" in df_tabela.columns:
        df_tabela["tempo trabalhado"] = df_tabela["tempo trabalhado"].apply(_format_hms)
    st.dataframe(df_tabela, width="stretch")
