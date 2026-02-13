# UI/despesas_ui.py

import streamlit as st
import pandas as pd

from Data.CRUD import (
    inserir_despesa,
    listar_despesas,
    atualizar_despesa,
    deletar_despesa,
)
from Metrics.analytics_despesas import (
    despesa_total,
    despesa_media,
    despesa_por_categoria,
)
from UI.components import titulo_secao, card_kpi


def pagina_despesas():
    st.header("Despesas")

    df = listar_despesas()
    if not df.empty and "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"])

    # FILTRO
    col1, col2 = st.columns(2)
    with col1:
        ano = st.number_input("Ano", value=pd.Timestamp.today().year, key="ano_d")
    with col2:
        mes = st.number_input("Mês", min_value=1, max_value=12, value=pd.Timestamp.today().month, key="mes_d")

    df_mes = df.copy()
    if not df_mes.empty and "data" in df_mes.columns:
        df_mes = df_mes[
            (df_mes["data"].dt.year == int(ano)) &
            (df_mes["data"].dt.month == int(mes))
        ]

    # MÉTRICAS
    titulo_secao("Resumo")

    total = despesa_total(df_mes)
    media = despesa_media(df_mes)

    col1, col2 = st.columns(2)
    with col1:
        card_kpi("Despesa total", f"R$ {total:,.2f}")
    with col2:
        card_kpi("Despesa média", f"R$ {media:,.2f}")

    # GRÁFICO
    titulo_secao("Por categoria")

    if not df_mes.empty:
        categoria = despesa_por_categoria(df_mes)
        st.bar_chart(categoria)
    else:
        st.info("Sem dados no período.")

    # TABELA
    titulo_secao("Registros")
    df_tabela = df_mes.copy()
    if not df_tabela.empty and "data" in df_tabela.columns:
        df_tabela["data"] = df_tabela["data"].dt.date
    st.dataframe(df_tabela, width="stretch")

    # FORMULÁRIO
    titulo_secao("Adicionar Despesa")

    with st.form("form_despesa"):
        data = st.date_input("Data", key="data_d")
        categoria = st.text_input("Categoria")
        valor = st.number_input("Valor", min_value=0.0, key="valor_d")
        observacao = st.text_input("Observação", key="obs_d")

        submit = st.form_submit_button("Salvar")

        if submit:
            inserir_despesa(data.isoformat(), categoria, valor, observacao)
            st.success("Despesa salva.")
            st.rerun()

    # -----------------------------
    # EDITAR / EXCLUIR
    # -----------------------------
    titulo_secao("Editar / Excluir Despesa")

    if df_mes.empty:
        st.info("Sem dados no período para editar ou excluir.")
        return

    ids = df_mes["id"].tolist()
    despesa_id = st.selectbox("Selecione o ID", ids, key="edit_id_d")
    registro = df_mes[df_mes["id"] == despesa_id].iloc[0]

    with st.form("form_edit_despesa"):
        data_e = st.date_input("Data", value=registro["data"].date(), key="edit_data_d")
        categoria_e = st.text_input("Categoria", value=str(registro["categoria"]), key="edit_categoria_d")
        valor_e = st.number_input("Valor", min_value=0.0, value=float(registro["valor"]), key="edit_valor_d")
        observacao_e = st.text_input("Observação", value=str(registro.get("observacao", "")), key="edit_obs_d")

        col1, col2 = st.columns(2)
        with col1:
            salvar = st.form_submit_button("Atualizar")
        with col2:
            excluir = st.form_submit_button("Excluir")

        if salvar:
            atualizar_despesa(
                int(despesa_id),
                data_e.isoformat(),
                categoria_e,
                valor_e,
                observacao_e,
            )
            st.success("Despesa atualizada.")
            st.rerun()
        if excluir:
            deletar_despesa(int(despesa_id))
            st.success("Despesa excluída.")
            st.rerun()
