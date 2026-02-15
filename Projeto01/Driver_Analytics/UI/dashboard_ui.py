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


def _record_alert_once(state_key: str, current_value: int, should_alert: bool, message: str) -> None:
    if not should_alert:
        return
    seen_value = int(st.session_state.get(state_key, 0))
    if int(current_value) > seen_value:
        st.session_state[state_key] = int(current_value)
        st.success(message)


def pagina_dashboard() -> None:
    """Render responsive dashboard page."""

    st.header("Dashboard Geral")

    df_receitas = service.listar_receitas()
    df_despesas = service.listar_despesas()

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

    titulo_secao("Resumo do Período")
    st.caption(
        "Receita total: soma das receitas do período. Despesa total: soma das despesas do período. "
        "Lucro: receita menos despesa. Margem: percentual do lucro sobre a receita total. "
        "Receita/KM e Lucro/KM: quanto você gera (receita e lucro) por quilômetro rodado no período."
    )

    receita_total = service.metrics.receita_total(df_receitas_f)
    despesa_total = service.metrics.despesa_total(df_despesas_f)
    lucro_total = service.metrics.lucro_bruto(df_receitas_f, df_despesas_f)
    margem_lucro = service.metrics.margem_lucro(df_receitas_f, df_despesas_f)
    dias = service.metrics.dias_trabalhados(df_receitas_f)
    meta_pct = service.metrics.percentual_meta_batida(df_receitas_f)
    receita_km = service.metrics.receita_por_km(df_receitas_f)
    lucro_km = service.metrics.lucro_por_km(df_receitas_f, df_despesas_f)
    consistencia = service.metrics.analise_consistencia(
        df_receitas_f,
        start_date=start_ts,
        end_date=end_base,
        meta=300.0,
    )

    kpis = [
        ("Receita total", format_currency(receita_total), None),
        ("Despesa total", format_currency(despesa_total), None),
        ("Lucro", format_currency(lucro_total), None),
        ("Margem", format_percent(margem_lucro), None),
        ("Dias trabalhados", int(dias), None),
        ("% Meta batida", format_percent(meta_pct), None),
        ("Receita/KM", format_currency(receita_km), None),
        ("Lucro/KM", format_currency(lucro_km), None),
    ]
    _render_kpi_grid(kpis)

    titulo_secao("Consistência Operacional")
    kpis_consistencia = [
        (
            "Maior sequência trabalhada",
            f"{int(consistencia['longest_work_streak'])} dias",
            f"Atual: {int(consistencia['current_work_streak'])} dias",
        ),
        (
            "Maior sequência sem trabalhar",
            f"{int(consistencia['longest_absence_streak'])} dias",
            f"Atual: {int(consistencia['current_absence_streak'])} dias",
        ),
        (
            "Maior sequência meta batida",
            f"{int(consistencia['longest_meta_hit_streak'])} dias",
            f"Atual: {int(consistencia['current_meta_hit_streak'])} dias",
        ),
        (
            "Maior sequência meta não batida",
            f"{int(consistencia['longest_meta_miss_streak'])} dias",
            f"Atual: {int(consistencia['current_meta_miss_streak'])} dias",
        ),
        (
            "Dia de maior ausência",
            _weekday_metric(
                str(consistencia["most_absent_weekday"]),
                int(consistencia["most_absent_weekday_count"]),
            ),
            None,
        ),
        (
            "Dia mais trabalhado",
            _weekday_metric(
                str(consistencia["most_worked_weekday"]),
                int(consistencia["most_worked_weekday_count"]),
            ),
            None,
        ),
    ]
    _render_kpi_grid(kpis_consistencia)

    _record_alert_once(
        "record_work_streak",
        int(consistencia["longest_work_streak"]),
        bool(consistencia["new_work_streak_record"]),
        "Parabéns! Esse é um novo Record na sequência de trabalho.",
    )
    _record_alert_once(
        "record_absence_streak",
        int(consistencia["longest_absence_streak"]),
        bool(consistencia["new_absence_streak_record"]),
        "Parabéns! Esse é um novo Record na sequência de dias sem trabalhar.",
    )
    _record_alert_once(
        "record_meta_hit_streak",
        int(consistencia["longest_meta_hit_streak"]),
        bool(consistencia["new_meta_hit_streak_record"]),
        "Parabéns! Esse é um novo Record na sequência de meta batida.",
    )
    _record_alert_once(
        "record_meta_miss_streak",
        int(consistencia["longest_meta_miss_streak"]),
        bool(consistencia["new_meta_miss_streak_record"]),
        "Parabéns! Esse é um novo Record na sequência de meta não batida.",
    )

    titulo_secao("Score do Mês")
    score = service.score_mensal(df_receitas.copy(), df_despesas.copy())
    render_kpi("Pontuação", score, "Baseado em margem, meta e lucro")

    titulo_secao("Análise Gráfica")
    if show_chart:
        if receita_total == 0 and despesa_total == 0:
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
    else:
        st.caption("Ative 'Exibir gráfico' no menu lateral para visualizar o gráfico.")

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
            columns=["data", "valor", "km", "tempo trabalhado"],
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
            columns=["data", "categoria", "valor"],
            key_prefix="despesas_preview",
            empty_message="Sem despesas no período selecionado.",
        )
