"""Despesas UI page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import format_currency, render_kpi, show_empty_data, titulo_secao


service = DashboardService()


def pagina_despesas() -> None:
    st.header("Despesas")

    df = service.listar_despesas()
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")

    col1, col2 = st.columns(2)
    with col1:
        ano = st.number_input("Ano", value=pd.Timestamp.today().year, key="ano_d")
    with col2:
        mes = st.number_input("Mês", min_value=1, max_value=12, value=pd.Timestamp.today().month, key="mes_d")

    df_mes = df.copy()
    if not df_mes.empty and "data" in df_mes.columns:
        df_mes = df_mes[(df_mes["data"].dt.year == int(ano)) & (df_mes["data"].dt.month == int(mes))]

    titulo_secao("Resumo")
    total = service.metrics.despesa_total(df_mes)
    media = service.metrics.despesa_media(df_mes)

    kpis = st.columns(2)
    with kpis[0]:
        render_kpi("Despesa total", format_currency(total))
    with kpis[1]:
        render_kpi("Despesa média", format_currency(media))

    titulo_secao("Por categoria")
    categoria = service.metrics.despesa_por_categoria(df_mes)
    if categoria.empty:
        show_empty_data()
    else:
        st.bar_chart(categoria)

    titulo_secao("Registros")
    df_tabela = df_mes.copy()
    if "data" in df_tabela.columns:
        df_tabela["data"] = pd.to_datetime(df_tabela["data"], errors="coerce").dt.date
    st.dataframe(df_tabela, width="stretch")

    titulo_secao("Adicionar Despesa")
    with st.form("form_despesa"):
        data = st.date_input("Data", key="data_d")
        categoria_input = st.text_input("Categoria", key="categoria_d")
        valor = st.number_input("Valor", min_value=0.0, key="valor_d")
        observacao = st.text_input("Observação", key="obs_d")
        submitted = st.form_submit_button("Salvar")

        if submitted:
            data_valida = pd.to_datetime(data, errors="coerce")
            if pd.isna(data_valida):
                st.warning("Selecione uma data válida.")
                return
            if not str(categoria_input).strip():
                st.warning("Informe uma categoria válida.")
                return
            service.criar_despesa(data_valida.date().isoformat(), categoria_input.strip(), valor, observacao)
            st.success("Despesa salva.")
            st.rerun()
