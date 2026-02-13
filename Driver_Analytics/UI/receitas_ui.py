"""Receitas UI page."""

from __future__ import annotations

from datetime import time

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


def _safe_date_or_none(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def pagina_receitas() -> None:
    st.header("Receitas")

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

    titulo_secao("Adicionar Receita")
    with st.form("form_receita"):
        data = st.date_input("Data", key="data_r")
        valor = st.number_input("Valor", min_value=0.0, key="valor_r")
        km = st.number_input("KM", min_value=0.0, key="km_r")
        tempo = st.time_input("Tempo trabalhado (hh:mm:ss)", value=time(0, 0, 0), key="tempo_r")
        observacao = st.text_input("Observação", key="obs_r")
        submitted = st.form_submit_button("Salvar")

        if submitted:
            data_valida = _safe_date_or_none(data)
            if data_valida is None:
                st.warning("Selecione uma data válida.")
                return
            tempo_total = tempo.hour * 3600 + tempo.minute * 60 + tempo.second
            service.criar_receita(data_valida.isoformat(), valor, km, tempo_total, observacao)
            st.success("Receita salva.")
            st.rerun()
