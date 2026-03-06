"""Responsive dashboard page for Driver Analytics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import (
    format_currency,
    format_percent,
    formatar_moeda,
    render_graph,
    render_kpi,
    render_table_preview,
    show_empty_data,
    titulo_secao,
)


service = DashboardService()


def _resolve_data_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if isinstance(col, str) and col.strip().lower() == "data":
            return col
    return None


def _prepare_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    data_col = _resolve_data_column(df)
    safe_df = df.copy()
    if data_col and not safe_df.empty:
        safe_df[data_col] = pd.to_datetime(safe_df[data_col], errors="coerce")
        safe_df = safe_df.dropna(subset=[data_col])
    return safe_df, data_col


def _safe_to_timestamp(value) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _apply_period(df: pd.DataFrame, data_col: str | None, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if df.empty or not data_col:
        return df
    return df[(df[data_col] >= start) & (df[data_col] <= end)]


def _apply_period_interval(df: pd.DataFrame, start_col: str, end_col: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if df.empty or start_col not in df.columns or end_col not in df.columns:
        return pd.DataFrame(columns=df.columns if isinstance(df, pd.DataFrame) else [])
    work = df.copy()
    work[start_col] = pd.to_datetime(work[start_col], errors="coerce")
    work[end_col] = pd.to_datetime(work[end_col], errors="coerce")
    work = work.dropna(subset=[start_col, end_col])
    return work[(work[start_col] <= end) & (work[end_col] >= start)]


def _render_kpi_grid(kpis: list[tuple[str, str | int | float, str | None]]) -> None:
    for index in range(0, len(kpis), 2):
        cols = st.columns(2)
        bloco = kpis[index : index + 2]
        for i, item in enumerate(bloco):
            titulo, valor, subtitulo = item
            with cols[i]:
                render_kpi(titulo, valor, subtitulo)


def _weekday_metric(label: str, count: int) -> str:
    if not label or label == "-" or int(count) <= 0:
        return "-"
    return f"{label} ({int(count)}x)"


def _record_alert_once(
    state_key: str,
    current_value: int,
    should_alert: bool,
    message: str,
    level: str = "success",
) -> None:
    if not should_alert:
        return
    seen_value = int(st.session_state.get(state_key, 0))
    if int(current_value) > seen_value:
        st.session_state[state_key] = int(current_value)
        if level == "warning":
            st.warning(message)
        elif level == "error":
            st.error(message)
        elif level == "info":
            st.info(message)
        else:
            st.success(message)


def pagina_dashboard() -> None:
    """Render responsive dashboard page."""

    st.header("Dashboard Geral")

    df_receitas = service.listar_receitas()
    df_despesas = service.listar_despesas()
    df_controle_km = service.listar_controle_km()
    df_controle_litros = service.listar_controle_litros() if hasattr(service, "listar_controle_litros") else pd.DataFrame()

    df_receitas, data_col_receitas = _prepare_dates(df_receitas)
    df_despesas, data_col_despesas = _prepare_dates(df_despesas)

    with st.sidebar:
        st.subheader("Filtros")
        today = pd.Timestamp.today().normalize()
        default_start = today.replace(day=1)
        start_date = st.date_input("Data inicial", value=default_start.date(), key="dash_start")
        end_date = st.date_input("Data final", value=today.date(), key="dash_end")
        show_chart = st.checkbox("Exibir gráfico", value=True, key="dash_show_chart")

    start_ts = _safe_to_timestamp(start_date)
    end_base = _safe_to_timestamp(end_date)

    if start_ts is None or end_base is None:
        st.warning("Selecione um intervalo de datas válido.")
        return

    if start_ts > end_base:
        st.warning("A data inicial não pode ser maior que a data final.")
        return

    end_ts = end_base + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    df_receitas_f = _apply_period(df_receitas, data_col_receitas, start_ts, end_ts)
    df_despesas_f = _apply_period(df_despesas, data_col_despesas, start_ts, end_ts)
    df_controle_km_f = _apply_period_interval(df_controle_km, "data_inicio", "data_fim", start_ts, end_ts)
    df_controle_litros, data_col_controle_litros = _prepare_dates(df_controle_litros)
    df_controle_litros_f = _apply_period(df_controle_litros, data_col_controle_litros, start_ts, end_ts)
    if "esfera_despesa" in df_despesas_f.columns:
        df_despesas_f = df_despesas_f.copy()
        df_despesas_f["esfera_despesa"] = (
            df_despesas_f["esfera_despesa"].fillna("NEGOCIO").astype(str).str.upper().str.strip()
        )
    else:
        df_despesas_f = df_despesas_f.copy()
        df_despesas_f["esfera_despesa"] = "NEGOCIO"

    df_despesas_negocio = df_despesas_f[df_despesas_f["esfera_despesa"] == "NEGOCIO"]
    df_despesas_pessoal = df_despesas_f[df_despesas_f["esfera_despesa"] == "PESSOAL"]
    df_investimentos = service.listar_investimentos()
    if not df_investimentos.empty:
        df_investimentos = df_investimentos.copy()
        data_inv_col = "data_fim" if "data_fim" in df_investimentos.columns else "data"
        df_investimentos[data_inv_col] = pd.to_datetime(df_investimentos[data_inv_col], errors="coerce")
        df_investimentos = df_investimentos.dropna(subset=[data_inv_col])
        df_investimentos = df_investimentos[(df_investimentos[data_inv_col] >= start_ts) & (df_investimentos[data_inv_col] <= end_ts)]
        df_investimentos["aporte"] = pd.to_numeric(df_investimentos.get("aporte"), errors="coerce").fillna(0.0)
    else:
        df_investimentos = pd.DataFrame()

    receita_total = service.metrics.receita_total(df_receitas_f)
    despesa_total = service.metrics.despesa_total(df_despesas_f)
    despesa_negocio = service.metrics.despesa_total(df_despesas_negocio)
    despesa_pessoal = service.metrics.despesa_total(df_despesas_pessoal)
    lucro_total = service.metrics.lucro_bruto(df_receitas_f, df_despesas_negocio)
    margem_lucro = service.metrics.margem_lucro(df_receitas_f, df_despesas_negocio)
    dias = service.metrics.dias_trabalhados(df_receitas_f)
    meta_pct = service.metrics.percentual_meta_batida(df_receitas_f)
    receita_km = service.metrics.receita_por_km(df_receitas_f)
    lucro_km = service.metrics.lucro_por_km(df_receitas_f, df_despesas_negocio)
    consistencia = service.metrics.analise_consistencia(df_receitas_f, start_date=start_ts, end_date=end_base, meta=300.0)

    km_remunerado = service.metrics.km_total(df_receitas_f)
    km_total_rodado = service.metrics.km_rodado_total_controle(df_controle_km_f)
    km_total_rodado = max(float(km_total_rodado), 0.0)
    km_nao_remunerado = float(max(km_total_rodado - km_remunerado, 0.0))
    km_remunerado_pct = float((km_remunerado / km_total_rodado) * 100.0) if km_total_rodado > 0 else 0.0
    km_nao_remunerado_pct = float(100.0 - km_remunerado_pct) if km_total_rodado > 0 else 0.0
    litros_combustivel = 0.0
    if not df_controle_litros_f.empty and "litros" in df_controle_litros_f.columns:
        litros_combustivel = float(pd.to_numeric(df_controle_litros_f["litros"], errors="coerce").fillna(0.0).sum())
    if litros_combustivel <= 0:
        litros_combustivel = service.metrics.litros_combustivel_total(df_despesas_negocio)
    consumo_km_l = float(km_total_rodado / litros_combustivel) if litros_combustivel > 0 else 0.0

    total_aportes_periodo = float(df_investimentos[df_investimentos["aporte"] > 0]["aporte"].sum()) if not df_investimentos.empty else 0.0
    total_retiradas_invest = float(abs(df_investimentos[df_investimentos["aporte"] < 0]["aporte"].sum())) if not df_investimentos.empty else 0.0
    remuneracao_bruta = float(lucro_total)
    remuneracao_pos_invest = float(remuneracao_bruta - total_aportes_periodo + total_retiradas_invest)
    saldo_cpf = float(remuneracao_pos_invest - despesa_pessoal)

    tab_cnpj, tab_cpf = st.tabs(["Dashboard CNPJ", "Dashboard CPF"])

    with tab_cnpj:
        titulo_secao("Resumo do Negócio")
        st.caption("CNPJ: receitas e despesas do negócio, sem considerar despesas pessoais.")
        _render_kpi_grid(
            [
                ("Receita total", format_currency(receita_total), None),
                ("Despesa negócio", format_currency(despesa_negocio), None),
                ("Lucro", format_currency(lucro_total), None),
                ("Margem", format_percent(margem_lucro), "Lucro sobre receita do negócio"),
                ("Dias trabalhados", int(dias), None),
                ("% Meta batida", format_percent(meta_pct), None),
                ("Receita/KM", format_currency(receita_km), None),
                ("Lucro/KM", format_currency(lucro_km), None),
            ]
        )

        titulo_secao("Eficiência Energética")
        st.caption(
            "KM remunerado: quilometragem com receita. KM total rodado: valor informado no cadastro Controle. "
            "Consumo médio = KM total rodado / litros abastecidos (Controle de Litros; fallback: despesas de combustível)."
        )
        _render_kpi_grid(
            [
                ("KM remunerado", f"{km_remunerado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("KM total rodado", f"{km_total_rodado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("KM não remunerado", f"{km_nao_remunerado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("% KM remunerado", format_percent(km_remunerado_pct), None),
                ("% KM não remunerado", format_percent(km_nao_remunerado_pct), None),
                ("Litros abastecidos", f"{litros_combustivel:,.2f} L".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("Consumo médio", f"{consumo_km_l:.2f} km/L", None),
                ("Despesa total", format_currency(despesa_total), "Macro: negócio + pessoal"),
            ]
        )

        titulo_secao("Consistência Operacional")
        _render_kpi_grid(
            [
                ("Maior sequência trabalhada", f"{int(consistencia['longest_work_streak'])} dias", f"Atual: {int(consistencia['current_work_streak'])} dias"),
                ("Maior sequência sem trabalhar", f"{int(consistencia['longest_absence_streak'])} dias", f"Atual: {int(consistencia['current_absence_streak'])} dias"),
                ("Maior sequência meta batida", f"{int(consistencia['longest_meta_hit_streak'])} dias", f"Atual: {int(consistencia['current_meta_hit_streak'])} dias"),
                ("Maior sequência meta não batida", f"{int(consistencia['longest_meta_miss_streak'])} dias", f"Atual: {int(consistencia['current_meta_miss_streak'])} dias"),
                ("Dia de maior ausência", _weekday_metric(str(consistencia["most_absent_weekday"]), int(consistencia["most_absent_weekday_count"])), None),
                ("Dia mais trabalhado", _weekday_metric(str(consistencia["most_worked_weekday"]), int(consistencia["most_worked_weekday_count"])), None),
            ]
        )

        _record_alert_once(
            "record_work_streak",
            int(consistencia["longest_work_streak"]),
            bool(consistencia["new_work_streak_record"]),
            "Parabéns! Esse é um novo recorde na sequência de trabalho.",
            level="success",
        )
        _record_alert_once(
            "record_absence_streak",
            int(consistencia["longest_absence_streak"]),
            bool(consistencia["new_absence_streak_record"]),
            "Atenção: novo recorde de sequência de dias sem trabalhar.",
            level="warning",
        )
        _record_alert_once(
            "record_meta_hit_streak",
            int(consistencia["longest_meta_hit_streak"]),
            bool(consistencia["new_meta_hit_streak_record"]),
            "Novo recorde na sequência de meta batida.",
            level="info",
        )
        _record_alert_once(
            "record_meta_miss_streak",
            int(consistencia["longest_meta_miss_streak"]),
            bool(consistencia["new_meta_miss_streak_record"]),
            "Atenção: novo recorde na sequência de meta não batida.",
            level="warning",
        )

        titulo_secao("Score do Mês")
        score = service.score_mensal(df_receitas.copy(), df_despesas_negocio.copy())
        render_kpi("Pontuação", score, "Baseado no desempenho do negócio")

        titulo_secao("Análise Gráfica")
        if show_chart:
            if receita_total == 0 and despesa_negocio == 0:
                show_empty_data("Sem dados para gerar o gráfico no período selecionado.")
            else:
                df_chart = pd.DataFrame(
                    [
                        {"Métrica": "Lucro (R$)", "Valor": lucro_total, "Cor": "Lucro"},
                        {"Métrica": "Margem (%)", "Valor": margem_lucro, "Cor": "Margem"},
                        {"Métrica": "Lucro/KM (R$)", "Valor": lucro_km, "Cor": "Lucro/KM"},
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
                render_graph(fig, height=370, show_legend=False)

    with tab_cpf:
        titulo_secao("Resumo Pessoal")
        st.caption(
            "CPF: remuneração do período = lucro do negócio. "
            "Aportes em investimentos reduzem a remuneração disponível e retiradas aumentam."
        )
        _render_kpi_grid(
            [
                ("Remuneração bruta", format_currency(remuneracao_bruta), "Lucro do negócio no período"),
                ("Aportes em investimentos", format_currency(total_aportes_periodo), "Desconta da remuneração"),
                ("Retiradas de investimentos", format_currency(total_retiradas_invest), "Soma à remuneração"),
                ("Remuneração pós investimentos", format_currency(remuneracao_pos_invest), None),
                ("Despesas pessoais", format_currency(despesa_pessoal), None),
                ("Saldo CPF", format_currency(saldo_cpf), "Remuneração pós investimentos - despesas pessoais"),
            ]
        )
        if show_chart:
            df_cpf = pd.DataFrame(
                [
                    {"Métrica": "Remuneração bruta", "Valor": remuneracao_bruta},
                    {"Métrica": "Aportes", "Valor": -total_aportes_periodo},
                    {"Métrica": "Retiradas", "Valor": total_retiradas_invest},
                    {"Métrica": "Despesas pessoais", "Valor": -despesa_pessoal},
                    {"Métrica": "Saldo CPF", "Valor": saldo_cpf},
                ]
            )
            fig_cpf = px.bar(df_cpf, x="Métrica", y="Valor", color="Métrica")
            fig_cpf.update_layout(height=370, margin=dict(l=20, r=20, t=20, b=20))
            render_graph(fig_cpf, height=370, show_legend=False)

    titulo_secao("Prévia de Dados")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Receitas recentes**")
        receitas_preview = df_receitas_f.sort_values(by=data_col_receitas, ascending=False) if data_col_receitas else df_receitas_f
        if data_col_receitas and not receitas_preview.empty:
            receitas_preview = receitas_preview.copy()
            receitas_preview[data_col_receitas] = receitas_preview[data_col_receitas].dt.date
        if "valor" in receitas_preview.columns:
            receitas_preview = receitas_preview.copy()
            receitas_preview["valor"] = pd.to_numeric(receitas_preview["valor"], errors="coerce").fillna(0.0).apply(formatar_moeda)
        render_table_preview(
            receitas_preview,
            columns=["data", "valor", "km", "km_rodado_total", "tempo trabalhado"],
            key_prefix="receitas_preview",
            empty_message="Sem receitas no período selecionado.",
        )

    with col2:
        st.markdown("**Despesas recentes**")
        despesas_preview = df_despesas_f.sort_values(by=data_col_despesas, ascending=False) if data_col_despesas else df_despesas_f
        if data_col_despesas and not despesas_preview.empty:
            despesas_preview = despesas_preview.copy()
            despesas_preview[data_col_despesas] = despesas_preview[data_col_despesas].dt.date
        if "valor" in despesas_preview.columns:
            despesas_preview = despesas_preview.copy()
            despesas_preview["valor"] = pd.to_numeric(despesas_preview["valor"], errors="coerce").fillna(0.0).apply(formatar_moeda)
        render_table_preview(
            despesas_preview,
            columns=["data", "categoria", "esfera_despesa", "valor", "litros"],
            key_prefix="despesas_preview",
            empty_message="Sem despesas no período selecionado.",
        )
