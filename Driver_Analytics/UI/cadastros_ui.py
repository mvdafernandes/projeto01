# UI/cadastros_ui.py

import streamlit as st
import pandas as pd

from Data.CRUD import (
    inserir_receita,
    inserir_despesa,
    inserir_investimento,
    recalcular_total_aportado,
)
from UI.components import titulo_secao


def pagina_cadastros():
    st.header("Cadastros")

    titulo_secao("Adicionar Receita")
    with st.form("cad_receita"):
        data = st.date_input("Data", key="cad_data_r")
        valor = st.number_input("Valor", min_value=0.0, key="cad_valor_r")
        km = st.number_input("KM", min_value=0.0, key="cad_km_r")
        tempo = st.time_input(
            "Tempo trabalhado (hh:mm:ss)",
            value=pd.Timestamp("00:00:00").time(),
            key="cad_tempo_r",
        )
        observacao = st.text_input("Observação", key="cad_obs_r")
        submit = st.form_submit_button("Salvar Receita")
        if submit:
            tempo_total = tempo.hour * 3600 + tempo.minute * 60 + tempo.second
            inserir_receita(data.isoformat(), valor, km, tempo_total, observacao)
            st.success("Receita salva.")
            st.rerun()

    titulo_secao("Adicionar Despesa")
    with st.form("cad_despesa"):
        data = st.date_input("Data", key="cad_data_d")
        categoria = st.text_input("Categoria", key="cad_categoria_d")
        valor = st.number_input("Valor", min_value=0.0, key="cad_valor_d")
        observacao = st.text_input("Observação", key="cad_obs_d")
        submit = st.form_submit_button("Salvar Despesa")
        if submit:
            inserir_despesa(data.isoformat(), categoria, valor, observacao)
            st.success("Despesa salva.")
            st.rerun()

    titulo_secao("Adicionar Investimento")
    with st.form("cad_invest"):
        data = st.date_input("Data", key="cad_data_i")
        aporte = st.number_input("Aporte", min_value=0.0, key="cad_aporte_i")
        rendimento = st.number_input("Rendimento", min_value=0.0, key="cad_rendimento_i")
        patrimonio_total = st.number_input("Patrimônio total", min_value=0.0, key="cad_patrimonio_total_i")
        submit = st.form_submit_button("Salvar Investimento")
        if submit:
            inserir_investimento(
                data.isoformat(),
                aporte,
                0.0,
                rendimento,
                patrimonio_total,
            )
            recalcular_total_aportado()
            st.success("Investimento salvo.")
            st.rerun()
