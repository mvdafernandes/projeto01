"""Investimentos UI page (visualization only)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from Metrics import analytics_investimentos as invest_metrics
from services.dashboard_service import DashboardService
from UI.components import format_currency, formatar_moeda, render_graph, render_kpi, show_empty_data, titulo_secao


service = DashboardService()
CATEGORIAS = ["Renda Fixa", "Renda Variável"]


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    """Format investment records for table display with BRL masks."""

    out = df.copy()
    if "data" in out.columns:
        out["data"] = pd.to_datetime(out["data"], errors="coerce").dt.date
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
    safe_df = safe_df.dropna(subset=["data"])
    if "categoria" not in safe_df.columns:
        safe_df["categoria"] = "Renda Fixa"
    safe_df["categoria"] = safe_df["categoria"].fillna("Renda Fixa").astype(str)

    for col in ["aporte", "rendimento", "patrimonio total"]:
        if col in safe_df.columns:
            safe_df[col] = pd.to_numeric(safe_df[col], errors="coerce").fillna(0.0)

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


def _rendimentos_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    """Use latest rendimento snapshot by category (RF/RV) with complete category set."""

    if df.empty:
        return pd.DataFrame({"categoria": CATEGORIAS, "rendimento": [0.0, 0.0]})

    ordered = df.sort_values(by=["data", "id"], ascending=[True, True])
    grouped = ordered.groupby("categoria", as_index=False)["rendimento"].last()
    grouped = grouped[grouped["categoria"].isin(CATEGORIAS)]

    # Guarantee both categories always appear in charts/cards.
    for cat in CATEGORIAS:
        if cat not in grouped["categoria"].tolist():
            grouped.loc[len(grouped)] = [cat, 0.0]

    grouped = grouped.sort_values(by="categoria")
    total = float(grouped["rendimento"].sum())
    grouped["participacao_pct"] = grouped["rendimento"].apply(lambda x: 0.0 if total == 0 else (float(x) / total) * 100)
    return grouped


def _media_aportes_mensal(df: pd.DataFrame) -> float:
    """Compute historical average monthly aporte from selected period."""

    if df.empty or "data" not in df.columns or "aporte" not in df.columns:
        return 0.0
    monthly = df.copy()
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

    proj = pd.DataFrame(rows)
    return proj


def pagina_investimentos() -> None:
    """Render investment dashboard with interval variation and RF/RV rendimento split."""

    st.header("Investimentos")
    st.info("Cadastros e edições agora ficam na página Cadastros.")

    df = _prepare_base_df()
    if df.empty:
        titulo_secao("Resumo")
        render_kpi("Patrimônio atual", format_currency(0.0))
        render_kpi("Total aportado", format_currency(0.0))
        render_kpi("Rendimento RF", format_currency(0.0))
        render_kpi("Rendimento RV", format_currency(0.0))
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

    df_metrics = df_periodo.rename(columns={"total aportado": "total_aportado", "patrimonio total": "patrimonio_total"})

    titulo_secao("Resumo")
    patrimonio = invest_metrics.patrimonio_atual(df_metrics)
    total_aporte = float(df_periodo["aporte"].sum())
    lucro = invest_metrics.lucro_acumulado(df_metrics)
    rent = invest_metrics.rentabilidade_percentual(df_metrics)

    rend_cat = _rendimentos_por_categoria(df_periodo)
    rend_rf = float(rend_cat[rend_cat["categoria"] == "Renda Fixa"]["rendimento"].sum())
    rend_rv = float(rend_cat[rend_cat["categoria"] == "Renda Variável"]["rendimento"].sum())

    st.caption("Total aportado = soma acumulada dos aportes registrados no intervalo (ex.: 1 + 2 = 3).")

    row1 = st.columns(2)
    with row1[0]:
        render_kpi("Patrimônio atual", format_currency(patrimonio))
    with row1[1]:
        render_kpi("Total aportado", format_currency(total_aporte))

    row2 = st.columns(2)
    with row2[0]:
        render_kpi("Lucro acumulado", format_currency(lucro))
    with row2[1]:
        render_kpi("Rentabilidade", f"{float(rent):.2f}%")

    row3 = st.columns(2)
    with row3[0]:
        render_kpi("Rendimento RF", format_currency(rend_rf))
    with row3[1]:
        render_kpi("Rendimento RV", format_currency(rend_rv))

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
        if base == 0:
            evol["variacao_pct"] = 0.0
        else:
            evol["variacao_pct"] = ((evol["patrimonio total"] / base) - 1.0) * 100.0

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
    if rend_cat.empty:
        show_empty_data("Sem rendimentos por categoria para mostrar.")
    else:
        rend_cat = rend_cat.copy()
        rend_cat["label"] = rend_cat.apply(
            lambda r: f"{formatar_moeda(r['rendimento'])} ({r['participacao_pct']:.1f}%)",
            axis=1,
        )
        fig_donut_rend = px.pie(
            rend_cat,
            values="rendimento",
            names="categoria",
            hole=0.55,
            color="categoria",
            color_discrete_map={"Renda Fixa": "#1f77b4", "Renda Variável": "#ff7f0e"},
        )
        fig_donut_rend.update_traces(textposition="inside", textinfo="percent+label")
        fig_donut_rend.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
        render_graph(fig_donut_rend, height=400, show_legend=True)

    titulo_secao("Comparativo de Rendimentos")
    rend_plot = rend_cat.copy()
    rend_plot["label"] = rend_plot.apply(lambda r: f"{formatar_moeda(r['rendimento'])} ({r['participacao_pct']:.1f}%)", axis=1)

    fig_bar = px.bar(
        rend_plot,
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

    titulo_secao("Projeção de Juros Compostos (10 anos)")
    patrimonio_atual = float(df_periodo.sort_values(by="data").iloc[-1]["patrimonio total"])
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

    df_proj = _projecao_juros_compostos(patrimonio_atual, float(taxa_anual_pct), float(aporte_mensal_proj), anos=10)

    # Yearly summary keeps the projection table concise for decision making.
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
