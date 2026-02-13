# UI/dashboard_ui.py

import streamlit as st
import pandas as pd
import plotly.express as px

from Data.CRUD import listar_receitas, listar_despesas
from Metrics.analytics_dashboard import resumo_mensal, score_mensal
from UI.components import titulo_secao, card_kpi


def pagina_dashboard():
    st.header("Dashboard Geral")

    df_receitas = listar_receitas()
    df_despesas = listar_despesas()

    if not df_receitas.empty:
        df_receitas["data"] = pd.to_datetime(df_receitas["data"])
    if not df_despesas.empty:
        df_despesas["data"] = pd.to_datetime(df_despesas["data"])

    # -----------------------------
    # RESUMO CONSOLIDADO
    # -----------------------------
    titulo_secao("Resumo Consolidado")

    resumo = resumo_mensal(df_receitas.copy(), df_despesas.copy())
    score = score_mensal(df_receitas.copy(), df_despesas.copy())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        card_kpi("Receita total", f"R$ {resumo['receita_total']:,.2f}")
    with col2:
        card_kpi("Despesa total", f"R$ {resumo['despesa_total']:,.2f}")
    with col3:
        card_kpi("Lucro", f"R$ {resumo['lucro']:,.2f}")
    with col4:
        card_kpi("Margem", f"{resumo['margem_%']:.1f}%")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        card_kpi("Dias trabalhados", resumo["dias_trabalhados"])
    with col2:
        card_kpi("% Meta batida", f"{resumo['%_meta_batida']:.1f}%")
    with col3:
        card_kpi("Receita/KM", f"R$ {resumo['receita_por_km']:,.2f}")
    with col4:
        card_kpi("Lucro/KM", f"R$ {resumo['lucro_por_km']:,.2f}")

    titulo_secao("Score do Mês")
    card_kpi("Pontuação", score, "Baseado em margem, meta e lucro")

    # -----------------------------
    # GRÁFICO INTERATIVO
    # -----------------------------
    titulo_secao("Gráfico de Lucro")
    mostrar_grafico = st.checkbox("Mostrar gráfico de lucro", value=False)

    if mostrar_grafico:
        if resumo["receita_total"] == 0 and resumo["despesa_total"] == 0:
            st.info("Sem dados para gerar o gráfico.")
        else:
            df_chart = pd.DataFrame(
                [
                    {"Métrica": "Lucro (R$)", "Valor": resumo["lucro"], "Cor": "Lucro"},
                    {"Métrica": "Margem (%)", "Valor": resumo["margem_%"], "Cor": "Margem"},
                    {"Métrica": "Lucro/KM (R$)", "Valor": resumo["lucro_por_km"], "Cor": "Lucro/KM"},
                ]
            )
            fig = px.bar(
                df_chart,
                x="Métrica",
                y="Valor",
                color="Cor",
                color_discrete_sequence=["#2ecc71", "#f1c40f", "#3498db"],
                text="Valor",
            )
            fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title=None, height=360)
            st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # TABELAS RÁPIDAS
    # -----------------------------
    col1, col2 = st.columns(2)
    with col1:
        titulo_secao("Receitas recentes")
        df_r = df_receitas.sort_values("data", ascending=False).head(10).copy()
        if not df_r.empty:
            df_r["data"] = df_r["data"].dt.date
        st.dataframe(df_r, width="stretch")
    with col2:
        titulo_secao("Despesas recentes")
        df_d = df_despesas.sort_values("data", ascending=False).head(10).copy()
        if not df_d.empty:
            df_d["data"] = df_d["data"].dt.date
        st.dataframe(df_d, width="stretch")
