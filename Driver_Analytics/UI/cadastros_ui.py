"""Cadastros UI page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import titulo_secao


service = DashboardService()


def pagina_cadastros() -> None:
    st.header("Cadastros")

    titulo_secao("Adicionar Receita")
    with st.form("cad_receita"):
        data = st.date_input("Data", key="cad_data_r")
        valor = st.number_input("Valor", min_value=0.0, key="cad_valor_r")
        km = st.number_input("KM", min_value=0.0, key="cad_km_r")
        tempo = st.time_input("Tempo trabalhado (hh:mm:ss)", value=pd.Timestamp("00:00:00").time(), key="cad_tempo_r")
        observacao = st.text_input("Observação", key="cad_obs_r")
        if st.form_submit_button("Salvar Receita"):
            tempo_total = tempo.hour * 3600 + tempo.minute * 60 + tempo.second
            service.criar_receita(data.isoformat(), valor, km, tempo_total, observacao)
            st.success("Receita salva.")
            st.rerun()

    titulo_secao("Adicionar Despesa")
    with st.form("cad_despesa"):
        data = st.date_input("Data", key="cad_data_d")
        categoria = st.text_input("Categoria", key="cad_categoria_d")
        valor = st.number_input("Valor", min_value=0.0, key="cad_valor_d")
        observacao = st.text_input("Observação", key="cad_obs_d")
        if st.form_submit_button("Salvar Despesa"):
            service.criar_despesa(data.isoformat(), categoria, valor, observacao)
            st.success("Despesa salva.")
            st.rerun()

    titulo_secao("Adicionar Investimento")
    with st.form("cad_invest"):
        data = st.date_input("Data", key="cad_data_i")
        aporte = st.number_input("Aporte", min_value=0.0, key="cad_aporte_i")
        rendimento = st.number_input("Rendimento", min_value=0.0, key="cad_rendimento_i")
        patrimonio_total = st.number_input("Patrimônio total", min_value=0.0, key="cad_patrimonio_total_i")
        if st.form_submit_button("Salvar Investimento"):
            service.criar_investimento(data.isoformat(), aporte, 0.0, rendimento, patrimonio_total)
            service.recalcular_total_aportado()
            st.success("Investimento salvo.")
            st.rerun()
