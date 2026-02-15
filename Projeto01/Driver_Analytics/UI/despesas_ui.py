"""Despesas UI page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import format_currency, formatar_moeda, render_kpi, show_empty_data, titulo_secao


service = DashboardService()


def _normalizar_tipo_despesa(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "tipo_despesa" not in out.columns:
        out["tipo_despesa"] = "VARIAVEL"
    out["tipo_despesa"] = out["tipo_despesa"].fillna("VARIAVEL").astype(str).str.upper().str.strip()
    out.loc[~out["tipo_despesa"].isin(["VARIAVEL", "RECORRENTE", "FIXA"]), "tipo_despesa"] = "VARIAVEL"
    if "subcategoria_fixa" not in out.columns:
        out["subcategoria_fixa"] = ""
    out["subcategoria_fixa"] = out["subcategoria_fixa"].fillna("").astype(str).str.strip()
    if "esfera_despesa" not in out.columns:
        out["esfera_despesa"] = "NEGOCIO"
    out["esfera_despesa"] = out["esfera_despesa"].fillna("NEGOCIO").astype(str).str.upper().str.strip()
    out.loc[~out["esfera_despesa"].isin(["NEGOCIO", "PESSOAL"]), "esfera_despesa"] = "NEGOCIO"
    return out


def _intervalo_referencia(modo_periodo: str, ano: int | None, mes: int | None, data_inicial, data_final):
    if modo_periodo == "Mensal" and ano is not None and mes is not None:
        inicio = pd.Timestamp(year=int(ano), month=int(mes), day=1)
        fim = (inicio + pd.offsets.MonthEnd(1)).normalize()
        return inicio, fim
    return pd.to_datetime(data_inicial), pd.to_datetime(data_final)


def pagina_despesas() -> None:
    st.header("Despesas")
    st.info("Cadastros e edições agora ficam na página Cadastros.")

    df = service.listar_despesas()
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = _normalizar_tipo_despesa(df)

    modo_periodo = st.radio("Visualização", ["Mensal", "Personalizado"], horizontal=True, key="desp_modo_periodo")

    df_filtrado = df.copy()
    titulo_resumo = "Resumo do Mês"
    ano = None
    mes = None
    data_inicial = None
    data_final = None
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
    despesas_negocio = df_filtrado[df_filtrado["esfera_despesa"] == "NEGOCIO"].copy()
    despesas_pessoal = df_filtrado[df_filtrado["esfera_despesa"] == "PESSOAL"].copy()
    total_negocio = service.metrics.despesa_total(despesas_negocio)
    total_pessoal = service.metrics.despesa_total(despesas_pessoal)

    kpis = st.columns(4)
    with kpis[0]:
        render_kpi("Despesa total", format_currency(total))
    with kpis[1]:
        render_kpi("Despesa média", format_currency(media))
    with kpis[2]:
        render_kpi("Despesa negócio", format_currency(total_negocio))
    with kpis[3]:
        render_kpi("Despesa pessoal", format_currency(total_pessoal))
    st.caption("Despesa média = valor médio por lançamento registrado no período selecionado.")
    st.caption("Visão micro do negócio: foque em 'Despesa negócio'. Visão macro de gestão: use 'Despesa total' (negócio + pessoal).")

    inicio_ref, fim_ref = _intervalo_referencia(modo_periodo, ano, mes, data_inicial, data_final)
    dias_ref = max(1, int((pd.to_datetime(fim_ref) - pd.to_datetime(inicio_ref)).days + 1))

    titulo_secao("Projeções e Recorrência")
    recorrentes = df_filtrado[df_filtrado["tipo_despesa"] == "RECORRENTE"].copy()
    total_recorrente = float(pd.to_numeric(recorrentes.get("valor"), errors="coerce").fillna(0.0).sum()) if not recorrentes.empty else 0.0
    proj_semana = float(total_recorrente / dias_ref * 7.0)
    proj_mes = float(total_recorrente / dias_ref * 30.0)
    rec_negocio = recorrentes[recorrentes["esfera_despesa"] == "NEGOCIO"].copy()
    rec_pessoal = recorrentes[recorrentes["esfera_despesa"] == "PESSOAL"].copy()
    total_rec_negocio = float(pd.to_numeric(rec_negocio.get("valor"), errors="coerce").fillna(0.0).sum()) if not rec_negocio.empty else 0.0
    total_rec_pessoal = float(pd.to_numeric(rec_pessoal.get("valor"), errors="coerce").fillna(0.0).sum()) if not rec_pessoal.empty else 0.0

    cols_rec = st.columns(3)
    with cols_rec[0]:
        render_kpi("Recorrentes no período", format_currency(total_recorrente))
    with cols_rec[1]:
        render_kpi("Projeção semanal", format_currency(proj_semana))
    with cols_rec[2]:
        render_kpi("Projeção mensal", format_currency(proj_mes))

    st.caption("Despesas marcadas como recorrentes são projetadas por média diária para semana (7 dias) e mês (30 dias).")
    cols_rec_split = st.columns(2)
    with cols_rec_split[0]:
        render_kpi("Recorrentes negócio", format_currency(total_rec_negocio))
    with cols_rec_split[1]:
        render_kpi("Recorrentes pessoais", format_currency(total_rec_pessoal))

    titulo_secao("Por categoria")
    categoria = service.metrics.despesa_por_categoria(df_filtrado)
    if categoria.empty:
        show_empty_data()
    else:
        st.bar_chart(categoria)

    titulo_secao("Distribuição Negócio x Pessoal")
    esfera = (
        df_filtrado.groupby("esfera_despesa", as_index=False)["valor"].sum()
        if not df_filtrado.empty
        else pd.DataFrame(columns=["esfera_despesa", "valor"])
    )
    if esfera.empty:
        show_empty_data("Sem despesas no período selecionado.")
    else:
        esfera["esfera_despesa"] = esfera["esfera_despesa"].map({"NEGOCIO": "Negócio", "PESSOAL": "Pessoal"})
        st.bar_chart(esfera.set_index("esfera_despesa")["valor"])

    titulo_secao("Contas Fixas por Subcategoria")
    fixas = df_filtrado[df_filtrado["tipo_despesa"] == "FIXA"].copy()
    if fixas.empty:
        show_empty_data("Sem despesas fixas no período selecionado.")
    else:
        fixas["subcat"] = fixas["subcategoria_fixa"].where(fixas["subcategoria_fixa"].str.strip() != "", fixas["observacao"])
        fixas["subcat"] = fixas["subcat"].fillna("").astype(str).str.strip()
        fixas.loc[fixas["subcat"] == "", "subcat"] = "Sem subcategoria"
        fixas["valor"] = pd.to_numeric(fixas["valor"], errors="coerce").fillna(0.0)

        grupo = fixas.groupby("subcat", as_index=False)["valor"].sum().sort_values(by="valor", ascending=False)
        total_fixas = float(grupo["valor"].sum())
        grupo["percentual"] = grupo["valor"].apply(lambda v: 0.0 if total_fixas == 0 else float(v) / total_fixas * 100.0)

        cols_fixas = st.columns(2)
        with cols_fixas[0]:
            render_kpi("Total de fixas", format_currency(total_fixas))
        with cols_fixas[1]:
            render_kpi("Subcategorias fixas", int(grupo.shape[0]))

        plot = grupo.set_index("subcat")["valor"]
        st.bar_chart(plot)
        tabela_fixas = grupo.copy()
        tabela_fixas["valor"] = tabela_fixas["valor"].apply(formatar_moeda)
        tabela_fixas["percentual"] = tabela_fixas["percentual"].map(lambda x: f"{x:.1f}%")
        st.dataframe(tabela_fixas.rename(columns={"subcat": "subcategoria"}), width="stretch", hide_index=True)

    titulo_secao("Registros")
    df_tabela = df_filtrado.copy()
    if "data" in df_tabela.columns:
        df_tabela["data"] = pd.to_datetime(df_tabela["data"], errors="coerce").dt.date
    if "valor" in df_tabela.columns:
        df_tabela["valor"] = pd.to_numeric(df_tabela["valor"], errors="coerce").fillna(0.0).apply(formatar_moeda)
    if "tipo_despesa" in df_tabela.columns:
        mapa_tipo = {"VARIAVEL": "Variável", "RECORRENTE": "Recorrente", "FIXA": "Fixa"}
        df_tabela["tipo_despesa"] = df_tabela["tipo_despesa"].map(lambda x: mapa_tipo.get(str(x).upper(), "Variável"))
    if "esfera_despesa" in df_tabela.columns:
        mapa_esfera = {"NEGOCIO": "Negócio", "PESSOAL": "Pessoal"}
        df_tabela["esfera_despesa"] = df_tabela["esfera_despesa"].map(lambda x: mapa_esfera.get(str(x).upper(), "Negócio"))
    st.dataframe(df_tabela, width="stretch")
