"""Investimentos UI page (visualization only)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import format_currency, formatar_moeda, render_graph, render_kpi, show_empty_data, titulo_secao


service = DashboardService()
CATEGORIAS = ["Renda Fixa", "Renda Variável"]


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    """Format investment records for table display with BRL masks."""

    out = df.copy()
    for dt_col in ["data_inicio", "data_fim", "data"]:
        if dt_col in out.columns:
            out[dt_col] = pd.to_datetime(out[dt_col], errors="coerce").dt.date
    for col in ["aporte", "total aportado", "rendimento", "patrimonio total"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).apply(formatar_moeda)
    return out


def _prepare_base_df() -> pd.DataFrame:
    """Load and sanitize investment dataframe for downstream analysis."""

    df = service.listar_investimentos()
    if df.empty:
        return df

    safe_df = df.copy()
    safe_df["data"] = pd.to_datetime(safe_df.get("data"), errors="coerce")
    if "data_inicio" in safe_df.columns:
        safe_df["data_inicio"] = pd.to_datetime(safe_df["data_inicio"], errors="coerce")
    else:
        safe_df["data_inicio"] = safe_df["data"]
    if "data_fim" in safe_df.columns:
        safe_df["data_fim"] = pd.to_datetime(safe_df["data_fim"], errors="coerce")
    else:
        safe_df["data_fim"] = safe_df["data"]
    safe_df["data"] = safe_df["data_fim"].fillna(safe_df["data"])
    safe_df = safe_df.dropna(subset=["data"])
    if "categoria" not in safe_df.columns:
        safe_df["categoria"] = "Renda Fixa"
    safe_df["categoria"] = safe_df["categoria"].fillna("Renda Fixa").astype(str)
    if "tipo_movimentacao" not in safe_df.columns:
        safe_df["tipo_movimentacao"] = ""
    safe_df["tipo_movimentacao"] = safe_df["tipo_movimentacao"].fillna("").astype(str).str.upper().str.strip()

    for col in ["aporte", "rendimento", "patrimonio total"]:
        if col in safe_df.columns:
            safe_df[col] = pd.to_numeric(safe_df[col], errors="coerce").fillna(0.0)

    safe_df.loc[(safe_df["tipo_movimentacao"] == "") & (safe_df["aporte"] > 0), "tipo_movimentacao"] = "APORTE"
    safe_df.loc[(safe_df["tipo_movimentacao"] == "") & (safe_df["aporte"] < 0), "tipo_movimentacao"] = "RETIRADA"
    safe_df.loc[(safe_df["tipo_movimentacao"] == "") & (safe_df["aporte"] == 0), "tipo_movimentacao"] = "RENDIMENTO"

    return safe_df.sort_values(by=["data", "id"], ascending=[True, True])


def _apply_period(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Filter dataframe by selected interval."""

    if df.empty:
        return df
    start_ts = pd.to_datetime(start_date, errors="coerce")
    end_ts = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start_ts) or pd.isna(end_ts):
        return df
    return df[(df["data"] >= start_ts) & (df["data"] <= end_ts)]


def _ensure_categorias(df_agg: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Guarantee RF and RV rows for consistent charts/cards."""

    out = df_agg.copy()
    for cat in CATEGORIAS:
        if cat not in out["categoria"].tolist():
            out.loc[len(out)] = [cat, 0.0]
    out = out[out["categoria"].isin(CATEGORIAS)].sort_values(by="categoria")
    total = float(out[value_col].sum())
    out["participacao_pct"] = out[value_col].apply(lambda x: 0.0 if total == 0 else (float(x) / total) * 100)
    return out


def _aportes_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate aporte totals by category (only rows with aporte > 0)."""

    if df.empty:
        return pd.DataFrame({"categoria": CATEGORIAS, "aporte": [0.0, 0.0], "participacao_pct": [0.0, 0.0]})
    aportes = df[df["tipo_movimentacao"] == "APORTE"].groupby("categoria", as_index=False)["aporte"].sum()
    if aportes.empty:
        aportes = pd.DataFrame(columns=["categoria", "aporte"])
    return _ensure_categorias(aportes, "aporte")


def _rendimentos_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate rendimento totals by category from all rows with rendimento != 0."""

    if df.empty:
        return pd.DataFrame({"categoria": CATEGORIAS, "rendimento": [0.0, 0.0], "participacao_pct": [0.0, 0.0]})
    rend = df[df["tipo_movimentacao"] == "RENDIMENTO"].groupby("categoria", as_index=False)["rendimento"].sum()
    if rend.empty:
        rend = pd.DataFrame(columns=["categoria", "rendimento"])
    return _ensure_categorias(rend, "rendimento")


def _patrimonio_base_periodo(df_full: pd.DataFrame, data_inicial) -> float:
    """Use patrimônio immediately before interval start as rentability baseline."""

    if df_full.empty:
        return 0.0
    start_ts = pd.to_datetime(data_inicial, errors="coerce")
    if pd.isna(start_ts):
        return 0.0

    anteriores = df_full[df_full["data"] < start_ts]
    if anteriores.empty:
        return 0.0

    ult = anteriores.sort_values(by=["data", "id"], ascending=[True, True]).iloc[-1]
    return float(ult.get("patrimonio total", 0.0))


def _patrimonio_atual_global(df: pd.DataFrame) -> float:
    """Return latest patrimônio total regardless of date filter."""

    if df.empty:
        return 0.0
    return float(df.sort_values(by=["data", "id"], ascending=[True, True]).iloc[-1]["patrimonio total"])


def _media_aportes_mensal(df: pd.DataFrame) -> float:
    """Compute historical average monthly aporte from selected period."""

    if df.empty or "data" not in df.columns or "aporte" not in df.columns:
        return 0.0
    monthly = df[df["aporte"] > 0].copy()
    if monthly.empty:
        return 0.0
    monthly["ano_mes"] = monthly["data"].dt.to_period("M").astype(str)
    monthly_totals = monthly.groupby("ano_mes")["aporte"].sum()
    if monthly_totals.empty:
        return 0.0
    return float(monthly_totals.mean())


def _projecao_juros_compostos(
    patrimonio_inicial: float, taxa_anual_pct: float, aporte_mensal: float, anos: int = 10
) -> pd.DataFrame:
    """Project portfolio growth using compound interest and fixed monthly contributions."""

    meses = int(anos * 12)
    taxa_anual = max(float(taxa_anual_pct), 0.0) / 100.0
    taxa_mensal = (1 + taxa_anual) ** (1 / 12) - 1 if taxa_anual > 0 else 0.0

    saldo = max(float(patrimonio_inicial), 0.0)
    aporte_acumulado = 0.0
    rows = []

    for mes in range(1, meses + 1):
        saldo = (saldo * (1 + taxa_mensal)) + max(float(aporte_mensal), 0.0)
        aporte_acumulado += max(float(aporte_mensal), 0.0)
        juros_acumulados = saldo - float(patrimonio_inicial) - aporte_acumulado
        rows.append(
            {
                "mes": mes,
                "ano": (mes - 1) // 12 + 1,
                "patrimonio_projetado": saldo,
                "aporte_acumulado": aporte_acumulado,
                "juros_acumulados": juros_acumulados,
            }
        )

    return pd.DataFrame(rows)


def _projecao_sem_aportes(patrimonio_inicial: float, taxa_anual_pct: float, anos: int = 10) -> pd.DataFrame:
    """Project compound growth from a single initial amount without monthly contributions."""

    meses = int(anos * 12)
    taxa_anual = max(float(taxa_anual_pct), 0.0) / 100.0
    taxa_mensal = (1 + taxa_anual) ** (1 / 12) - 1 if taxa_anual > 0 else 0.0
    saldo = max(float(patrimonio_inicial), 0.0)
    rows = []

    for mes in range(1, meses + 1):
        saldo = saldo * (1 + taxa_mensal)
        juros_acumulados = saldo - max(float(patrimonio_inicial), 0.0)
        rows.append(
            {
                "mes": mes,
                "ano": (mes - 1) // 12 + 1,
                "patrimonio_projetado": saldo,
                "capital_inicial": max(float(patrimonio_inicial), 0.0),
                "juros_acumulados": juros_acumulados,
            }
        )
    return pd.DataFrame(rows)


def pagina_investimentos() -> None:
    """Render investment dashboard aligned to aporte/rendimento split model."""

    st.header("Investimentos")
    st.info("Cadastros e edições agora ficam na página Cadastros.")

    df = _prepare_base_df()
    if df.empty:
        titulo_secao("Resumo")
        render_kpi("Patrimônio atual", format_currency(0.0))
        render_kpi("Total aportado", format_currency(0.0))
        render_kpi("Lucro do período", format_currency(0.0))
        render_kpi("Rentabilidade do período", "0.00%")
        show_empty_data("Sem dados de investimentos para o período.")
        return

    min_date = df["data"].min().date()
    max_date = df["data"].max().date()

    colf1, colf2 = st.columns(2)
    with colf1:
        data_inicial = st.date_input("Data inicial", value=min_date, min_value=min_date, max_value=max_date, key="invest_start")
    with colf2:
        data_final = st.date_input("Data final", value=max_date, min_value=min_date, max_value=max_date, key="invest_end")

    if pd.to_datetime(data_inicial) > pd.to_datetime(data_final):
        st.warning("A data inicial não pode ser maior que a data final.")
        return

    df_periodo = _apply_period(df, data_inicial, data_final)
    if df_periodo.empty:
        show_empty_data("Sem registros no intervalo selecionado.")
        return

    titulo_secao("Resumo")
    patrimonio_global = _patrimonio_atual_global(df)
    patrimonio_periodo_final = float(df_periodo.sort_values(by=["data", "id"]).iloc[-1]["patrimonio total"])
    aportes_brutos = float(df_periodo[df_periodo["tipo_movimentacao"] == "APORTE"]["aporte"].sum())
    retiradas_total = float(abs(df_periodo[df_periodo["tipo_movimentacao"] == "RETIRADA"]["aporte"].sum()))
    aportes_liquidos = float(aportes_brutos - retiradas_total)
    lucro_periodo = float(df_periodo[df_periodo["tipo_movimentacao"] == "RENDIMENTO"]["rendimento"].sum())
    patrimonio_base = _patrimonio_base_periodo(df, data_inicial)
    capital_base_rent = float(patrimonio_base + (aportes_liquidos / 2.0))
    rent_periodo = (lucro_periodo / capital_base_rent) * 100.0 if capital_base_rent > 0 else 0.0

    aportes_cat = _aportes_por_categoria(df_periodo)
    rend_cat = _rendimentos_por_categoria(df_periodo)

    aporte_rf = float(aportes_cat[aportes_cat["categoria"] == "Renda Fixa"]["aporte"].sum())
    aporte_rv = float(aportes_cat[aportes_cat["categoria"] == "Renda Variável"]["aporte"].sum())
    rend_rf = float(rend_cat[rend_cat["categoria"] == "Renda Fixa"]["rendimento"].sum())
    rend_rv = float(rend_cat[rend_cat["categoria"] == "Renda Variável"]["rendimento"].sum())

    st.caption(
        "Patrimônio total é automático (aportes + rendimentos - retiradas). "
        "Rentabilidade usa rendimento do período sobre capital base do intervalo."
    )

    row1 = st.columns(3)
    with row1[0]:
        render_kpi("Patrimônio atual", format_currency(patrimonio_global))
    with row1[1]:
        render_kpi("Patrimônio fim do período", format_currency(patrimonio_periodo_final))
    with row1[2]:
        render_kpi("Aportes no período", format_currency(aportes_brutos))

    row2 = st.columns(3)
    with row2[0]:
        render_kpi("Lucro do período", format_currency(lucro_periodo))
    with row2[1]:
        render_kpi("Rentabilidade do período", f"{float(rent_periodo):.2f}%")
    with row2[2]:
        render_kpi("Retiradas no período", format_currency(retiradas_total))

    row3 = st.columns(2)
    with row3[0]:
        render_kpi("Aportes líquidos", format_currency(aportes_liquidos))
    with row3[1]:
        render_kpi("Base da rentabilidade", format_currency(capital_base_rent))

    row4 = st.columns(2)
    with row4[0]:
        render_kpi("Aportes RF/RV", f"{formatar_moeda(aporte_rf)} / {formatar_moeda(aporte_rv)}")
    with row4[1]:
        render_kpi("Rendimento RF/RV", f"{formatar_moeda(rend_rf)} / {formatar_moeda(rend_rv)}")

    titulo_secao("Evolução no Intervalo")
    evol = (
        df_periodo.groupby("data", as_index=False)["patrimonio total"]
        .last()
        .sort_values(by="data")
    )

    if evol.empty:
        show_empty_data("Sem dados para evolução no intervalo.")
    else:
        base = float(evol.iloc[0]["patrimonio total"])
        evol["variacao_pct"] = 0.0 if base == 0 else ((evol["patrimonio total"] / base) - 1.0) * 100.0

        colg1, colg2 = st.columns(2)
        with colg1:
            fig_patr = px.line(evol, x="data", y="patrimonio total", markers=True)
            fig_patr.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), xaxis_title=None, yaxis_title="Patrimônio (R$)")
            render_graph(fig_patr, height=400)
        with colg2:
            fig_var = px.line(evol, x="data", y="variacao_pct", markers=True)
            fig_var.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), xaxis_title=None, yaxis_title="Variação (%)")
            render_graph(fig_var, height=400)

    titulo_secao("Donut de Rendimentos RF vs RV")
    rend_cat_plot = rend_cat.copy()
    rend_cat_plot["label"] = rend_cat_plot.apply(
        lambda r: f"{formatar_moeda(r['rendimento'])} ({r['participacao_pct']:.1f}%)",
        axis=1,
    )
    rend_cat_donut = rend_cat_plot.copy()
    rend_cat_donut["rendimento_abs"] = rend_cat_donut["rendimento"].abs()
    if float(rend_cat_donut["rendimento_abs"].sum()) <= 0:
        show_empty_data("Sem rendimentos para exibir no donut no período selecionado.")
    else:
        fig_donut_rend = px.pie(
            rend_cat_donut,
            values="rendimento_abs",
            names="categoria",
            hole=0.55,
            color="categoria",
            color_discrete_map={"Renda Fixa": "#1f77b4", "Renda Variável": "#ff7f0e"},
        )
        fig_donut_rend.update_traces(textposition="inside", textinfo="percent+label")
        fig_donut_rend.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
        render_graph(fig_donut_rend, height=400, show_legend=True)

    titulo_secao("Comparativo de Rendimentos")
    fig_bar = px.bar(
        rend_cat_plot,
        x="categoria",
        y="rendimento",
        color="categoria",
        text="label",
        color_discrete_map={"Renda Fixa": "#1f77b4", "Renda Variável": "#ff7f0e"},
    )
    fig_bar.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), xaxis_title=None, yaxis_title="Rendimento (R$)")
    fig_bar.update_traces(textposition="outside")
    render_graph(fig_bar, height=400, show_legend=False)

    titulo_secao("Registros")
    st.dataframe(_format_table(df_periodo), width="stretch")

    anos_proj = int(
        st.number_input(
            "Horizonte da projeção com aportes (anos)",
            min_value=1,
            max_value=50,
            step=1,
            value=10,
            key="inv_proj_horizonte_anos",
        )
    )
    titulo_secao(f"Projeção de Juros Compostos ({anos_proj} anos)")
    patrimonio_atual = float(df_periodo.sort_values(by=["data", "id"]).iloc[-1]["patrimonio total"])
    media_aportes = _media_aportes_mensal(df_periodo)

    colp1, colp2 = st.columns(2)
    with colp1:
        taxa_anual_pct = st.number_input(
            "Percentual ao ano (%)",
            min_value=0.0,
            step=0.1,
            value=10.0,
            key="inv_proj_taxa_anual",
        )
    with colp2:
        aporte_mensal_proj = st.number_input(
            "Média mensal de aportes (R$)",
            min_value=0.0,
            step=1.0,
            value=float(media_aportes),
            key="inv_proj_aporte_mensal",
        )

    st.caption(
        f"Base atual: patrimônio {formatar_moeda(patrimonio_atual)} | "
        f"média histórica mensal de aportes: {formatar_moeda(media_aportes)}"
    )

    df_proj = _projecao_juros_compostos(
        patrimonio_atual,
        float(taxa_anual_pct),
        float(aporte_mensal_proj),
        anos=anos_proj,
    )

    proj_ano = (
        df_proj.groupby("ano", as_index=False)
        .agg(
            patrimonio_projetado=("patrimonio_projetado", "last"),
            aporte_acumulado=("aporte_acumulado", "last"),
            juros_acumulados=("juros_acumulados", "last"),
        )
    )
    tabela_proj = proj_ano.copy()
    for col in ["patrimonio_projetado", "aporte_acumulado", "juros_acumulados"]:
        tabela_proj[col] = tabela_proj[col].apply(formatar_moeda)
    st.dataframe(tabela_proj, width="stretch", hide_index=True)

    fig_proj = px.line(
        proj_ano,
        x="ano",
        y=["patrimonio_projetado", "aporte_acumulado", "juros_acumulados"],
        markers=True,
        labels={
            "value": "Valor (R$)",
            "variable": "Série",
            "ano": "Ano",
        },
    )
    fig_proj.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
    render_graph(fig_proj, height=420, show_legend=True)

    anos_proj_sem_aporte = int(
        st.number_input(
            "Horizonte da projeção sem aportes (anos)",
            min_value=1,
            max_value=50,
            step=1,
            value=10,
            key="inv_proj_horizonte_sem_aporte_anos",
        )
    )
    titulo_secao(f"Projeção de Juros Compostos sem Novos Aportes ({anos_proj_sem_aporte} anos)")
    colu1, colu2 = st.columns(2)
    with colu1:
        taxa_anual_sem_aporte = st.number_input(
            "Percentual ao ano (%) - sem aportes",
            min_value=0.0,
            step=0.1,
            value=float(taxa_anual_pct),
            key="inv_proj_taxa_sem_aporte",
        )
    with colu2:
        valor_unitario = st.number_input(
            "Valor unitário inicial (R$)",
            min_value=0.0,
            step=1.0,
            value=float(patrimonio_atual),
            key="inv_proj_valor_unitario",
        )

    st.caption(
        "Simulação com aporte único inicial e sem novos aportes mensais durante todo o período de projeção."
    )

    df_proj_sem_aporte = _projecao_sem_aportes(
        patrimonio_inicial=float(valor_unitario),
        taxa_anual_pct=float(taxa_anual_sem_aporte),
        anos=anos_proj_sem_aporte,
    )
    proj_sem_aporte_ano = (
        df_proj_sem_aporte.groupby("ano", as_index=False)
        .agg(
            patrimonio_projetado=("patrimonio_projetado", "last"),
            capital_inicial=("capital_inicial", "last"),
            juros_acumulados=("juros_acumulados", "last"),
        )
    )

    tabela_sem_aporte = proj_sem_aporte_ano.copy()
    for col in ["patrimonio_projetado", "capital_inicial", "juros_acumulados"]:
        tabela_sem_aporte[col] = tabela_sem_aporte[col].apply(formatar_moeda)
    st.dataframe(tabela_sem_aporte, width="stretch", hide_index=True)

    fig_sem_aporte = px.line(
        proj_sem_aporte_ano,
        x="ano",
        y=["patrimonio_projetado", "capital_inicial", "juros_acumulados"],
        markers=True,
        labels={
            "value": "Valor (R$)",
            "variable": "Série",
            "ano": "Ano",
        },
    )
    fig_sem_aporte.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
    render_graph(fig_sem_aporte, height=420, show_legend=True)
