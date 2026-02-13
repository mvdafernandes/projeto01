"""Cadastros UI page."""

from __future__ import annotations

from datetime import time

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import titulo_secao


service = DashboardService()


def _safe_date_or_none(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def pagina_cadastros() -> None:
    st.header("Cadastros")

    titulo_secao("Adicionar Receita")
    with st.form("cad_receita"):
        data = st.date_input("Data", key="cad_data_r")
        valor = st.number_input("Valor", min_value=0.0, key="cad_valor_r")
        km = st.number_input("KM", min_value=0.0, key="cad_km_r")
        tempo = st.time_input("Tempo trabalhado (hh:mm:ss)", value=time(0, 0, 0), key="cad_tempo_r")
        observacao = st.text_input("Observação", key="cad_obs_r")
        submitted = st.form_submit_button("Salvar Receita")
        if submitted:
            data_valida = _safe_date_or_none(data)
            if data_valida is None:
                st.warning("Selecione uma data válida.")
                return
            tempo_total = tempo.hour * 3600 + tempo.minute * 60 + tempo.second
            service.criar_receita(data_valida.isoformat(), valor, km, tempo_total, observacao)
            st.success("Receita salva.")
            st.rerun()

    titulo_secao("Adicionar Despesa")
    with st.form("cad_despesa"):
        data = st.date_input("Data", key="cad_data_d")
        categoria = st.text_input("Categoria", key="cad_categoria_d")
        valor = st.number_input("Valor", min_value=0.0, key="cad_valor_d")
        observacao = st.text_input("Observação", key="cad_obs_d")
        submitted = st.form_submit_button("Salvar Despesa")
        if submitted:
            data_valida = _safe_date_or_none(data)
            if data_valida is None:
                st.warning("Selecione uma data válida.")
                return
            if not str(categoria).strip():
                st.warning("Informe uma categoria válida.")
                return
            service.criar_despesa(data_valida.isoformat(), categoria.strip(), valor, observacao)
            st.success("Despesa salva.")
            st.rerun()

    titulo_secao("Adicionar Investimento")
    with st.form("cad_invest"):
        data = st.date_input("Data", key="cad_data_i")
        aporte = st.number_input("Aporte", min_value=0.0, key="cad_aporte_i")
        rendimento = st.number_input("Rendimento", min_value=0.0, key="cad_rendimento_i")
        patrimonio_total = st.number_input("Patrimônio total", min_value=0.0, key="cad_patrimonio_total_i")
        submitted = st.form_submit_button("Salvar Investimento")
        if submitted:
            data_valida = _safe_date_or_none(data)
            if data_valida is None:
                st.warning("Selecione uma data válida.")
                return
            service.criar_investimento(data_valida.isoformat(), aporte, 0.0, rendimento, patrimonio_total)
            service.recalcular_total_aportado()
            st.success("Investimento salvo.")
            st.rerun()
