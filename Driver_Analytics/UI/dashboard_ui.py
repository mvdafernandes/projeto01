"""Responsive dashboard page for Driver Analytics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from services.dashboard_service import DashboardService
from UI.cadastros_ui import _ensure_selected_option, _get_row_by_id, _reset_fields, _with_display_order
from UI.components import (
    format_currency,
    format_percent,
    formatar_moeda,
    render_graph,
    render_kpi_grid,
    render_kpi,
    render_table_preview,
    show_empty_data,
    titulo_secao,
)


service = DashboardService()
FUEL_TYPES = ["Flex", "Gasolina", "Etanol", "Diesel", "GNV", "Outro"]


def _set_dashboard_full_history(start_date, end_date) -> None:
    st.session_state["dash_start"] = start_date
    st.session_state["dash_end"] = end_date


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


def _fuel_unit_for_type(tipo_combustivel: str) -> str:
    return "m³" if str(tipo_combustivel or "").strip().upper() == "GNV" else "L"


def _fuel_summary_unit(df_controle_litros: pd.DataFrame) -> str:
    if df_controle_litros.empty or "tipo_combustivel" not in df_controle_litros.columns:
        return "L"
    tipos = {
        str(value).strip().upper()
        for value in df_controle_litros["tipo_combustivel"].fillna("").astype(str).tolist()
        if str(value).strip()
    }
    if tipos == {"GNV"}:
        return "m³"
    return "L"


def _fuel_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo abastecimento"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return "Registro ?"
    ordered = _with_display_order(df)
    selected = ordered[ordered["id"] == int(item_id)]
    registro = int(selected.iloc[0]["registro"]) if not selected.empty else 0
    status = "Tanque cheio" if bool(row.get("tanque_cheio", False)) else "Parcial"
    return f"Registro {registro} | {row.get('data', '-') } | {status}"


def _set_fuel_form_fields(df: pd.DataFrame, selected_id: int | None) -> None:
    row = _get_row_by_id(df, selected_id)
    st.session_state["fuel_data"] = pd.to_datetime(row.get("data"), errors="coerce").date() if row is not None and pd.notna(pd.to_datetime(row.get("data"), errors="coerce")) else pd.Timestamp.today().date()
    st.session_state["fuel_odometro"] = float(row.get("odometro", 0.0) or 0.0) if row is not None else 0.0
    st.session_state["fuel_litros"] = float(row.get("litros", 0.0) or 0.0) if row is not None else 0.0
    st.session_state["fuel_valor_total"] = float(row.get("valor_total", 0.0) or 0.0) if row is not None else 0.0
    st.session_state["fuel_tanque_cheio"] = bool(row.get("tanque_cheio", False)) if row is not None else False
    tipo = str(row.get("tipo_combustivel", "") if row is not None else "").strip()
    st.session_state["fuel_tipo_combustivel"] = tipo if tipo in FUEL_TYPES else FUEL_TYPES[0]
    st.session_state["fuel_observacao"] = str(row.get("observacao", "") if row is not None else "")
    st.session_state["fuel_confirm_delete"] = False


def _render_fuel_control(df_controle_litros: pd.DataFrame) -> None:
    titulo_secao("Abastecimentos")
    migrate_col, _ = st.columns([1, 3])
    if migrate_col.button("Migrar abastecimentos antigos", key="fuel_migrate_legacy"):
        try:
            resultado = service.migrar_abastecimentos_legados()
            st.success(
                f"Migração concluída: {int(resultado.get('migrados', 0))} importados, {int(resultado.get('ignorados', 0))} ignorados."
            )
            _reset_fields(["fuel_selected_id", "fuel_last_selected_id", "fuel_confirm_delete"])
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    df = df_controle_litros.copy()
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    if not df.empty and "id" in df.columns:
        df = df.sort_values(by=["data", "id"], ascending=[False, False]).reset_index(drop=True)

    options = [None] + (df["id"].astype(int).tolist() if "id" in df.columns else [])
    _ensure_selected_option("fuel_selected_id", options)
    selected_id = st.selectbox("Abastecimento", options=options, format_func=lambda x: _fuel_label(df, x), key="fuel_selected_id")
    last_selected = st.session_state.get("fuel_last_selected_id")
    if selected_id != last_selected:
        _set_fuel_form_fields(df, selected_id)
        st.session_state["fuel_last_selected_id"] = selected_id

    with st.form("fuel_control_form"):
        data = st.date_input("Data do abastecimento", key="fuel_data")
        tipo_combustivel = st.selectbox("Tipo de combustível", options=FUEL_TYPES, key="fuel_tipo_combustivel")
        unidade_volume = _fuel_unit_for_type(tipo_combustivel)
        col1, col2 = st.columns(2)
        with col1:
            odometro = st.number_input("Odômetro", min_value=0.0, step=1.0, key="fuel_odometro")
            litros = st.number_input(f"Volume abastecido ({unidade_volume})", min_value=0.0, step=0.1, key="fuel_litros")
        with col2:
            valor_total = st.number_input("Valor total", min_value=0.0, step=0.01, key="fuel_valor_total")
            tanque_cheio = st.checkbox("Tanque cheio", key="fuel_tanque_cheio")
        observacao = st.text_input("Observação", key="fuel_observacao")
        confirmar_exclusao = st.checkbox("Confirmo a exclusão deste abastecimento", key="fuel_confirm_delete")
        col_save, col_update, col_delete = st.columns(3)
        salvar = col_save.form_submit_button("Salvar (novo)")
        atualizar = col_update.form_submit_button("Atualizar")
        excluir = col_delete.form_submit_button("Excluir")

        try:
            if salvar:
                service.criar_controle_litros(
                    data.isoformat(),
                    float(litros),
                    odometro=float(odometro) if odometro > 0 else None,
                    valor_total=float(valor_total),
                    tanque_cheio=bool(tanque_cheio),
                    tipo_combustivel=tipo_combustivel,
                    observacao=observacao,
                )
                st.success("Abastecimento salvo.")
                _reset_fields(["fuel_selected_id", "fuel_last_selected_id", "fuel_confirm_delete"])
                st.rerun()
            if atualizar:
                if selected_id is None:
                    st.warning("Selecione um abastecimento para atualizar.")
                else:
                    service.atualizar_controle_litros(
                        int(selected_id),
                        data.isoformat(),
                        float(litros),
                        odometro=float(odometro) if odometro > 0 else None,
                        valor_total=float(valor_total),
                        tanque_cheio=bool(tanque_cheio),
                        tipo_combustivel=tipo_combustivel,
                        observacao=observacao,
                    )
                    st.success("Abastecimento atualizado.")
                    st.rerun()
            if excluir:
                if selected_id is None:
                    st.warning("Selecione um abastecimento para excluir.")
                elif not confirmar_exclusao:
                    st.warning("Confirme a exclusão para continuar.")
                else:
                    service.deletar_controle_litros(int(selected_id))
                    st.success("Abastecimento excluído.")
                    _reset_fields(["fuel_selected_id", "fuel_last_selected_id", "fuel_confirm_delete"])
                    st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if df.empty:
        show_empty_data("Nenhum abastecimento cadastrado.")
        return
    tabela = _with_display_order(df)
    tabela["data"] = pd.to_datetime(tabela["data"], errors="coerce").dt.date
    if "litros" in tabela.columns:
        tabela["volume"] = [
            f"{float(value or 0.0):.1f} {_fuel_unit_for_type(tipo)}"
            for value, tipo in zip(tabela["litros"], tabela.get("tipo_combustivel", pd.Series([""] * len(tabela))))
        ]
        tabela = tabela.drop(columns=["litros"])
    if "odometro" in tabela.columns:
        tabela["odometro"] = pd.to_numeric(tabela["odometro"], errors="coerce").fillna(0.0).map(lambda x: f"{x:.1f}")
    if "valor_total" in tabela.columns:
        tabela["valor_total"] = pd.to_numeric(tabela["valor_total"], errors="coerce").fillna(0.0).apply(formatar_moeda)
    if "tanque_cheio" in tabela.columns:
        tabela["tanque_cheio"] = tabela["tanque_cheio"].map(lambda x: "Sim" if bool(x) else "Não")
    st.dataframe(
        tabela[[col for col in ["registro", "data", "odometro", "volume", "valor_total", "tanque_cheio", "tipo_combustivel", "observacao"] if col in tabela.columns]],
        use_container_width=True,
        hide_index=True,
    )


def pagina_dashboard() -> None:
    """Render responsive dashboard page."""

    st.header("Dashboard Geral")

    df_receitas = service.listar_receitas()
    df_despesas = service.listar_despesas()
    df_controle_km = service.listar_controle_km()
    df_controle_litros = service.listar_controle_litros() if hasattr(service, "listar_controle_litros") else pd.DataFrame()
    df_investimentos = service.listar_investimentos()

    df_receitas, data_col_receitas = _prepare_dates(df_receitas)
    df_despesas, data_col_despesas = _prepare_dates(df_despesas)
    df_controle_litros, data_col_controle_litros = _prepare_dates(df_controle_litros)

    # Prefer full historical window when data exists to avoid "all-zero" first render.
    date_series: list[pd.Series] = []
    for frame, col in [
        (df_receitas, data_col_receitas),
        (df_despesas, data_col_despesas),
        (df_controle_litros, data_col_controle_litros),
    ]:
        if isinstance(frame, pd.DataFrame) and not frame.empty and col and col in frame.columns:
            date_series.append(frame[col].dropna())
    if isinstance(df_investimentos, pd.DataFrame) and not df_investimentos.empty:
        inv_col = "data_fim" if "data_fim" in df_investimentos.columns else "data"
        if inv_col in df_investimentos.columns:
            inv_dates = pd.to_datetime(df_investimentos[inv_col], errors="coerce").dropna()
            if not inv_dates.empty:
                date_series.append(inv_dates)

    today = pd.Timestamp.today().normalize()
    if date_series:
        min_available = min(series.min() for series in date_series).normalize()
        max_available = max(series.max() for series in date_series).normalize()
    else:
        min_available = today.replace(day=1)
        max_available = today

    st.session_state.setdefault("dash_start", min_available.date())
    st.session_state.setdefault("dash_end", max_available.date())

    with st.sidebar:
        st.subheader("Filtros")
        start_date = st.date_input("Data inicial", value=min_available.date(), key="dash_start")
        end_date = st.date_input("Data final", value=max_available.date(), key="dash_end")
        st.button(
            "Usar todo histórico",
            key="dash_use_full_history",
            on_click=_set_dashboard_full_history,
            args=(min_available.date(), max_available.date()),
        )
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
    daily_goal = float(service.obter_daily_goal())
    despesa_total = service.metrics.despesa_total(df_despesas_f)
    despesa_negocio = service.metrics.despesa_total(df_despesas_negocio)
    despesa_pessoal = service.metrics.despesa_total(df_despesas_pessoal)
    lucro_total = service.metrics.lucro_bruto(df_receitas_f, df_despesas_negocio)
    margem_lucro = service.metrics.margem_lucro(df_receitas_f, df_despesas_negocio)
    dias = service.metrics.dias_trabalhados(df_receitas_f)
    meta_pct = service.metrics.percentual_meta_batida(df_receitas_f, meta=daily_goal)
    consistencia = service.metrics.analise_consistencia(df_receitas_f, start_date=start_ts, end_date=end_base, meta=daily_goal)

    km_snapshot = service.km_snapshot(start_ts, end_base)
    km_remunerado = float(km_snapshot["km_remunerado"])
    km_total_rodado = float(km_snapshot["km_total"])
    km_nao_remunerado = float(km_snapshot["km_nao_remunerado"])
    receita_km = float(receita_total / km_remunerado) if km_remunerado > 0 else 0.0
    lucro_km = float(lucro_total / km_remunerado) if km_remunerado > 0 else 0.0
    km_remunerado_pct = float((km_remunerado / km_total_rodado) * 100.0) if km_total_rodado > 0 else 0.0
    km_nao_remunerado_pct = float(100.0 - km_remunerado_pct) if km_total_rodado > 0 else 0.0
    fuel_snapshot = service.fuel_consumption_snapshot(start_ts, end_base)
    fuel_unit = _fuel_summary_unit(df_controle_litros_f)
    litros_combustivel = float(fuel_snapshot["litros_total_abastecidos"])
    litros_trechos_fechados = float(fuel_snapshot["litros_trechos_fechados"])
    km_trechos_fechados = float(fuel_snapshot["km_trechos_fechados"])
    trechos_fechados = int(fuel_snapshot["segment_count"])
    consumo_km_l = float(fuel_snapshot["consumo_km_l"])
    if litros_combustivel <= 0:
        litros_combustivel = service.metrics.litros_combustivel_total(df_despesas_negocio)

    total_aportes_periodo = float(df_investimentos[df_investimentos["aporte"] > 0]["aporte"].sum()) if not df_investimentos.empty else 0.0
    total_retiradas_invest = float(abs(df_investimentos[df_investimentos["aporte"] < 0]["aporte"].sum())) if not df_investimentos.empty else 0.0
    remuneracao_bruta = float(lucro_total)
    remuneracao_pos_invest = float(remuneracao_bruta - total_aportes_periodo + total_retiradas_invest)
    saldo_cpf = float(remuneracao_pos_invest - despesa_pessoal)

    tab_cnpj, tab_cpf = st.tabs(["Dashboard CNPJ", "Dashboard CPF"])

    with tab_cnpj:
        titulo_secao("Resumo do Negócio")
        st.caption("CNPJ: receitas e despesas do negócio, sem considerar despesas pessoais.")
        render_kpi_grid(
            [
                ("Receita total", format_currency(receita_total), None),
                ("Despesa negócio", format_currency(despesa_negocio), None),
                ("Lucro", format_currency(lucro_total), None),
                ("Margem", format_percent(margem_lucro), "Lucro sobre receita do negócio"),
                ("Dias trabalhados", int(dias), None),
                ("% Meta batida", format_percent(meta_pct), f"Meta diária: {format_currency(daily_goal)}"),
                ("Receita/KM", format_currency(receita_km), None),
                ("Lucro/KM", format_currency(lucro_km), None),
            ]
        )

        titulo_secao("Eficiência Energética")
        st.caption(
            "KM remunerado vem prioritariamente da Jornada. KM total rodado vem do Controle histórico por período "
            "e, quando não existir, do cálculo derivado da Jornada com hodômetro; controles legados entram só como fallback. "
            f"Consumo real (km/{fuel_unit}) é calculado por trechos fechados entre dois abastecimentos com tanque cheio."
        )
        render_kpi_grid(
            [
                ("KM remunerado", f"{km_remunerado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("KM total rodado", f"{km_total_rodado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("KM não remunerado", f"{km_nao_remunerado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("% KM remunerado", format_percent(km_remunerado_pct), None),
                ("% KM não remunerado", format_percent(km_nao_remunerado_pct), None),
                ("Volume abastecido", f"{litros_combustivel:,.2f} {fuel_unit}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("Consumo real", f"{consumo_km_l:.2f} km/{fuel_unit}", f"Trechos fechados: {trechos_fechados}"),
                ("KM em trechos fechados", f"{km_trechos_fechados:,.2f} km".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("Volume em trechos fechados", f"{litros_trechos_fechados:,.2f} {fuel_unit}".replace(",", "X").replace(".", ",").replace("X", "."), None),
                ("Despesa total", format_currency(despesa_total), "Macro: negócio + pessoal"),
            ]
        )

        titulo_secao("Consistência Operacional")
        render_kpi_grid(
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
        render_kpi_grid(
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

    _render_fuel_control(df_controle_litros)
