"""Receitas UI page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import format_currency, format_percent, formatar_moeda, render_kpi, show_empty_data, titulo_secao


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

    modo_periodo = st.radio("Visualização", ["Mensal", "Personalizado"], horizontal=True, key="rec_modo_periodo")

    df_filtrado = df.copy()
    titulo_resumo = "Resumo do Mês"
    if modo_periodo == "Mensal":
        col1, col2 = st.columns(2)
        with col1:
            ano = st.number_input("Ano", min_value=2020, max_value=2100, value=pd.Timestamp.today().year, key="rec_ano")
        with col2:
            mes = st.number_input("Mês", min_value=1, max_value=12, value=pd.Timestamp.today().month, key="rec_mes")
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
                key="rec_data_inicio",
            )
        with col2:
            data_final = st.date_input(
                "Data final",
                value=max_data,
                min_value=min_data,
                max_value=max_data,
                key="rec_data_fim",
            )
        if pd.to_datetime(data_inicial) > pd.to_datetime(data_final):
            st.warning("A data inicial não pode ser maior que a data final.")
            return
        inicio = pd.to_datetime(data_inicial)
        fim = pd.to_datetime(data_final) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_filtrado = df_filtrado[(df_filtrado["data"] >= inicio) & (df_filtrado["data"] <= fim)]
        titulo_resumo = "Resumo do Período"

    titulo_secao(titulo_resumo)
    total = service.metrics.receita_total(df_filtrado)
    media = service.metrics.receita_media_diaria(df_filtrado)
    dias = service.metrics.dias_trabalhados(df_filtrado)
    meta_pct = service.metrics.percentual_meta_batida(df_filtrado)

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
    if not df_filtrado.empty and {"data", "valor"}.issubset(df_filtrado.columns):
        resumo = df_filtrado.groupby("data")["valor"].sum()
        st.line_chart(resumo)
    else:
        show_empty_data()

    titulo_secao("Evolução Semanal, Mensal e Anual")
    if not df_filtrado.empty and {"data", "valor"}.issubset(df_filtrado.columns):
        base = df_filtrado.copy()
        base["valor"] = pd.to_numeric(base["valor"], errors="coerce").fillna(0.0)
        base["data"] = pd.to_datetime(base["data"], errors="coerce")
        base = base.dropna(subset=["data"])

        if base.empty:
            show_empty_data("Sem dados suficientes para evolução por período.")
        else:
            semanal = (
                base.set_index("data")["valor"]
                .resample("W-SUN")
                .sum()
                .rename_axis("periodo")
            )
            mensal = (
                base.set_index("data")["valor"]
                .resample("M")
                .sum()
                .rename_axis("periodo")
            )
            anual = (
                base.set_index("data")["valor"]
                .resample("Y")
                .sum()
                .rename_axis("periodo")
            )

            col_sem, col_men, col_anu = st.columns(3)
            with col_sem:
                st.markdown("**Semanal**")
                st.line_chart(semanal)
            with col_men:
                st.markdown("**Mensal**")
                st.line_chart(mensal)
            with col_anu:
                st.markdown("**Anual**")
                st.line_chart(anual)
    else:
        show_empty_data("Sem dados para evolução semanal, mensal e anual.")

    titulo_secao("Registros")
    df_tabela = df_filtrado.copy()
    if "data" in df_tabela.columns:
        df_tabela["data"] = pd.to_datetime(df_tabela["data"], errors="coerce").dt.date
    if "valor" in df_tabela.columns:
        df_tabela["valor"] = pd.to_numeric(df_tabela["valor"], errors="coerce").fillna(0.0).apply(formatar_moeda)
    if "km" in df_tabela.columns:
        df_tabela["km"] = pd.to_numeric(df_tabela["km"], errors="coerce").fillna(0.0).map(lambda v: f"{float(v):.2f}")
    if "tempo trabalhado" in df_tabela.columns:
        df_tabela["tempo trabalhado"] = df_tabela["tempo trabalhado"].apply(_format_hms)
    st.dataframe(df_tabela, width="stretch")

    titulo_secao("Remuneração (CPF)")
    st.caption(
        "Remuneração bruta = lucro do negócio no período (receitas - despesas de negócio). "
        "Remuneração disponível considera aportes e retiradas de investimentos."
    )
    df_despesas = service.listar_despesas()
    if "data" in df_despesas.columns:
        df_despesas["data"] = pd.to_datetime(df_despesas["data"], errors="coerce")
    if "esfera_despesa" not in df_despesas.columns:
        df_despesas["esfera_despesa"] = "NEGOCIO"
    df_despesas["esfera_despesa"] = df_despesas["esfera_despesa"].fillna("NEGOCIO").astype(str).str.upper().str.strip()

    if modo_periodo == "Mensal":
        despesas_filtradas = df_despesas[
            (df_despesas["data"].dt.year == int(ano)) & (df_despesas["data"].dt.month == int(mes))
        ].copy() if not df_despesas.empty else pd.DataFrame()
    else:
        despesas_filtradas = df_despesas[
            (df_despesas["data"] >= inicio) & (df_despesas["data"] <= fim)
        ].copy() if not df_despesas.empty else pd.DataFrame()

    despesas_negocio = despesas_filtradas[despesas_filtradas["esfera_despesa"] == "NEGOCIO"].copy()
    despesas_pessoais = despesas_filtradas[despesas_filtradas["esfera_despesa"] == "PESSOAL"].copy()

    df_inv = service.listar_investimentos()
    if not df_inv.empty:
        data_inv_col = "data_fim" if "data_fim" in df_inv.columns else "data"
        df_inv[data_inv_col] = pd.to_datetime(df_inv[data_inv_col], errors="coerce")
        if modo_periodo == "Mensal":
            df_inv = df_inv[(df_inv[data_inv_col].dt.year == int(ano)) & (df_inv[data_inv_col].dt.month == int(mes))]
        else:
            df_inv = df_inv[(df_inv[data_inv_col] >= inicio) & (df_inv[data_inv_col] <= fim)]
        df_inv["aporte"] = pd.to_numeric(df_inv.get("aporte"), errors="coerce").fillna(0.0)

    despesa_negocio_total = service.metrics.despesa_total(despesas_negocio)
    despesa_pessoal_total = service.metrics.despesa_total(despesas_pessoais)
    lucro_negocio = float(total - despesa_negocio_total)
    aportes = float(df_inv[df_inv["aporte"] > 0]["aporte"].sum()) if not df_inv.empty else 0.0
    retiradas = float(abs(df_inv[df_inv["aporte"] < 0]["aporte"].sum())) if not df_inv.empty else 0.0
    remuneracao_disponivel = float(lucro_negocio - aportes + retiradas)
    saldo_cpf = float(remuneracao_disponivel - despesa_pessoal_total)

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        render_kpi("Remuneração bruta", format_currency(lucro_negocio))
    with col_r2:
        render_kpi("Remuneração disponível", format_currency(remuneracao_disponivel))
    with col_r3:
        render_kpi("Saldo CPF", format_currency(saldo_cpf))

    col_r4, col_r5, col_r6 = st.columns(3)
    with col_r4:
        render_kpi("Despesa pessoal", format_currency(despesa_pessoal_total))
    with col_r5:
        render_kpi("Aportes", format_currency(aportes))
    with col_r6:
        render_kpi("Retiradas", format_currency(retiradas))
