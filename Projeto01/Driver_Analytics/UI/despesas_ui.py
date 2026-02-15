"""Despesas UI page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import format_currency, formatar_moeda, render_kpi, show_empty_data, titulo_secao


service = DashboardService()


def pagina_despesas() -> None:
    st.header("Despesas")
    st.info("Cadastros e edições agora ficam na página Cadastros.")

    df = service.listar_despesas()
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")

    modo_periodo = st.radio("Visualização", ["Mensal", "Personalizado"], horizontal=True, key="desp_modo_periodo")

    df_filtrado = df.copy()
    titulo_resumo = "Resumo do Mês"
    if modo_periodo == "Mensal":
        col1, col2 = st.columns(2)
        with col1:
            ano = st.number_input("Ano", value=pd.Timestamp.today().year, key="desp_ano")
        with col2:
            mes = st.number_input("Mês", min_value=1, max_value=12, value=pd.Timestamp.today().month, key="desp_mes")
        if not df_filtrado.empty and "data" in df_filtrado.columns:
            df_filtrado = df_filtrado[(df_filtrado["data"].dt.year == int(ano)) & (df_filtrado["data"].dt.month == int(mes))]
    else:
        if df_filtrado.empty or "data" not in df_filtrado.columns or df_filtrado["data"].dropna().empty:
            show_empty_data("Sem dados para aplicar filtro personalizado.")
            return

        min_data = df_filtrado["data"].min().date()
        max_data = df_filtrado["data"].max().date()
        col1, col2 = st.columns(2)
        with col1:
            data_inicial = st.date_input(
                "Data inicial",
                value=min_data,
                min_value=min_data,
                max_value=max_data,
                key="desp_data_inicio",
            )
        with col2:
            data_final = st.date_input(
                "Data final",
                value=max_data,
                min_value=min_data,
                max_value=max_data,
                key="desp_data_fim",
            )
        if pd.to_datetime(data_inicial) > pd.to_datetime(data_final):
            st.warning("A data inicial não pode ser maior que a data final.")
            return
        inicio = pd.to_datetime(data_inicial)
        fim = pd.to_datetime(data_final) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_filtrado = df_filtrado[(df_filtrado["data"] >= inicio) & (df_filtrado["data"] <= fim)]
        titulo_resumo = "Resumo do Período"

    titulo_secao(titulo_resumo)
    total = service.metrics.despesa_total(df_filtrado)
    media = service.metrics.despesa_media(df_filtrado)

    kpis = st.columns(2)
    with kpis[0]:
        render_kpi("Despesa total", format_currency(total))
    with kpis[1]:
        render_kpi("Despesa média", format_currency(media))

    titulo_secao("Por categoria")
    categoria = service.metrics.despesa_por_categoria(df_filtrado)
    if categoria.empty:
        show_empty_data()
    else:
        st.bar_chart(categoria)

    titulo_secao("Registros")
    df_tabela = df_filtrado.copy()
    if "data" in df_tabela.columns:
        df_tabela["data"] = pd.to_datetime(df_tabela["data"], errors="coerce").dt.date
    if "valor" in df_tabela.columns:
        df_tabela["valor"] = pd.to_numeric(df_tabela["valor"], errors="coerce").fillna(0.0).apply(formatar_moeda)
    st.dataframe(df_tabela, width="stretch")
