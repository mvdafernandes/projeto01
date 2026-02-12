# UI/investimentos_ui.py

import streamlit as st
import pandas as pd

from Data.CRUD import (
    inserir_investimento,
    listar_investimentos,
    atualizar_investimento,
    deletar_investimento,
    recalcular_total_aportado,
)
from Metrics import analytics_investimentos as invest_metrics
from UI.components import titulo_secao, card_kpi


def pagina_investimentos(conn):
    st.header("Investimentos")

    df = listar_investimentos()
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])

    df_metrics = df.copy()
    if not df_metrics.empty:
        df_metrics = df_metrics.rename(
            columns={
                "total aportado": "total_aportado",
                "patrimonio total": "patrimonio_total",
            }
        )

    # MÉTRICAS
    titulo_secao("Resumo")

    if df_metrics.empty:
        patrimonio = 0
        total_aporte = 0
        lucro = 0
        rent = 0
    else:
        patrimonio = invest_metrics.patrimonio_atual(df_metrics)
        total_aporte = invest_metrics.total_aportado(df_metrics)
        lucro = invest_metrics.lucro_acumulado(df_metrics)
        rent = invest_metrics.rentabilidade_percentual(df_metrics)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        card_kpi("Patrimônio atual", f"R$ {patrimonio:,.2f}")
    with col2:
        card_kpi("Total aportado", f"R$ {total_aporte:,.2f}")
    with col3:
        card_kpi("Lucro acumulado", f"R$ {lucro:,.2f}")
    with col4:
        card_kpi("Rentabilidade", f"{rent:.2f}%")

    # GRÁFICO
    titulo_secao("Evolução")

    if not df_metrics.empty:
        resumo = df_metrics.groupby("data")["patrimonio_total"].last()
        st.line_chart(resumo)
    else:
        st.info("Sem dados.")

    # TABELA
    titulo_secao("Registros")
    df_tabela = df.copy()
    if not df_tabela.empty:
        df_tabela["data"] = df_tabela["data"].dt.date
    st.dataframe(df_tabela, width="stretch")

    # FORMULÁRIO
    titulo_secao("Adicionar Investimento")

    with st.form("form_invest"):
        data = st.date_input("Data", key="data_i")
        aporte = st.number_input("Aporte", min_value=0.0, key="aporte_i")
        rendimento = st.number_input("Rendimento", min_value=0.0, key="rendimento_i")
        patrimonio_total = st.number_input("Patrimônio total", min_value=0.0, key="patrimonio_total_i")

        submit = st.form_submit_button("Salvar")

        if submit:
            total_aportado = float(df["aporte"].sum()) + float(aporte) if not df.empty else float(aporte)
            inserir_investimento(
                data.isoformat(),
                aporte,
                total_aportado,
                rendimento,
                patrimonio_total,
            )
            recalcular_total_aportado()
            st.success("Investimento salvo.")
            st.rerun()

    # -----------------------------
    # EDITAR / EXCLUIR
    # -----------------------------
    titulo_secao("Editar / Excluir Investimento")

    if df.empty:
        st.info("Sem dados para editar ou excluir.")
        return

    ids = df["id"].tolist()
    invest_id = st.selectbox("Selecione o ID", ids, key="edit_id_i")
    registro = df[df["id"] == invest_id].iloc[0]

    with st.form("form_edit_invest"):
        data_e = st.date_input("Data", value=pd.to_datetime(registro["data"]).date(), key="edit_data_i")
        aporte_e = st.number_input("Aporte", min_value=0.0, value=float(registro["aporte"]), key="edit_aporte_i")
        rendimento_e = st.number_input(
            "Rendimento",
            min_value=0.0,
            value=float(registro["rendimento"]),
            key="edit_rendimento_i",
        )
        patrimonio_total_e = st.number_input(
            "Patrimônio total",
            min_value=0.0,
            value=float(registro["patrimonio total"]),
            key="edit_patrimonio_total_i",
        )

        col1, col2 = st.columns(2)
        with col1:
            salvar = st.form_submit_button("Atualizar")
        with col2:
            excluir = st.form_submit_button("Excluir")

        if salvar:
            atualizar_investimento(
                int(invest_id),
                data_e.isoformat(),
                aporte_e,
                float(registro["total aportado"]),
                rendimento_e,
                patrimonio_total_e,
            )
            recalcular_total_aportado()
            st.success("Investimento atualizado.")
            st.rerun()
        if excluir:
            deletar_investimento(int(invest_id))
            recalcular_total_aportado()
            st.success("Investimento excluído.")
            st.rerun()
