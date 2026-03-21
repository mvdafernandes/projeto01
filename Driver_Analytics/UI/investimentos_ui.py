"""Investimentos UI page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from Metrics.analytics_investimentos import (
    calcular_cagr,
    lucro_acumulado,
    patrimonio_atual as analytics_patrimonio_atual,
    patrimonio_inicial,
    projecao_com_aporte,
    rentabilidade_percentual,
    total_aportado,
)
from UI.cadastros_ui import (
    INVEST_CATEGORIAS,
    _ensure_selected_option,
    _get_row_by_id,
    _investimento_aporte_label,
    _investimento_retirada_label,
    _investimento_rendimento_label,
    _patrimonio_atual,
    _reset_fields,
    _safe_date_or_none,
    _set_invest_aporte_fields,
    _set_invest_retirada_fields,
    _set_invest_rendimento_fields,
    _sort_desc_by_id,
    _sync_edit_state,
    _with_display_order,
)
from UI.components import format_currency, format_percent, formatar_moeda, render_kpi_grid, show_empty_data, titulo_secao
from services.dashboard_service import DashboardService


service = DashboardService()
TIPO_MOVIMENTACAO_LABELS = {
    "APORTE": "Aporte",
    "RENDIMENTO": "Rendimento",
    "RETIRADA": "Retirada",
}


def _prepare_investimentos(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    for col in [
        "id",
        "data",
        "data_inicio",
        "data_fim",
        "tipo_movimentacao",
        "categoria",
        "aporte",
        "total aportado",
        "rendimento",
        "patrimonio total",
    ]:
        if col not in work.columns:
            work[col] = pd.Series(dtype="object")

    for col in ["data", "data_inicio", "data_fim"]:
        work[col] = pd.to_datetime(work[col], errors="coerce")
    for col in ["aporte", "total aportado", "rendimento", "patrimonio total"]:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)

    work["categoria"] = work["categoria"].fillna("Renda Fixa").astype(str).str.strip()
    work.loc[work["categoria"] == "", "categoria"] = "Renda Fixa"
    work["tipo_movimentacao"] = work["tipo_movimentacao"].fillna("").astype(str).str.upper().str.strip()
    work.loc[~work["tipo_movimentacao"].isin(TIPO_MOVIMENTACAO_LABELS.keys()), "tipo_movimentacao"] = (
        work["aporte"].map(lambda v: "APORTE" if float(v) > 0 else ("RETIRADA" if float(v) < 0 else "RENDIMENTO"))
    )
    return work


def _analytics_frame(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "patrimonio total" in work.columns and "patrimonio_total" not in work.columns:
        work["patrimonio_total"] = work["patrimonio total"]
    if "total aportado" in work.columns and "total_aportado" not in work.columns:
        work["total_aportado"] = work["total aportado"]
    return work


def _filter_period(df: pd.DataFrame, modo_periodo: str) -> tuple[pd.DataFrame, str]:
    if df.empty:
        return df.copy(), "Resumo do Período"

    data_col = "data_fim" if "data_fim" in df.columns else "data"
    work = df.copy()
    work = work.dropna(subset=[data_col])
    if work.empty:
        return work, "Resumo do Período"

    titulo = "Resumo do Mês"
    if modo_periodo == "Mensal":
        col1, col2 = st.columns(2)
        with col1:
            ano = st.number_input("Ano", min_value=2020, max_value=2100, value=pd.Timestamp.today().year, key="inv_ano")
        with col2:
            mes = st.number_input("Mês", min_value=1, max_value=12, value=pd.Timestamp.today().month, key="inv_mes")
        work = work[(work[data_col].dt.year == int(ano)) & (work[data_col].dt.month == int(mes))]
        return work, titulo

    min_data = work[data_col].min().date()
    max_data = work[data_col].max().date()
    col1, col2 = st.columns(2)
    with col1:
        data_inicial = st.date_input(
            "Data inicial",
            value=min_data,
            min_value=min_data,
            max_value=max_data,
            key="inv_data_inicio",
        )
    with col2:
        data_final = st.date_input(
            "Data final",
            value=max_data,
            min_value=min_data,
            max_value=max_data,
            key="inv_data_fim",
        )
    if pd.to_datetime(data_inicial) > pd.to_datetime(data_final):
        st.warning("A data inicial não pode ser maior que a data final.")
        return pd.DataFrame(columns=work.columns), "Resumo do Período"
    inicio = pd.to_datetime(data_inicial)
    fim = pd.to_datetime(data_final) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return work[(work[data_col] >= inicio) & (work[data_col] <= fim)], "Resumo do Período"


def _render_summary(df: pd.DataFrame) -> None:
    titulo_secao("Resumo da Carteira")
    if df.empty:
        show_empty_data("Sem investimentos no período selecionado.")
        return

    analytics_df = _analytics_frame(df)
    patrimonio = float(analytics_patrimonio_atual(analytics_df))
    aportado = float(total_aportado(analytics_df))
    lucro = float(lucro_acumulado(analytics_df))
    rent_pct = float(rentabilidade_percentual(analytics_df))
    cagr = float(calcular_cagr(analytics_df))
    patrimonio_base = float(patrimonio_inicial(analytics_df))

    render_kpi_grid(
        [
            ("Patrimônio atual", format_currency(patrimonio), None),
            ("Total aportado", format_currency(aportado), None),
            ("Lucro acumulado", format_currency(lucro), None),
            ("Rentabilidade", format_percent(rent_pct), None),
            ("CAGR", format_percent(cagr), "Baseado no patrimônio inicial/final"),
            ("Patrimônio inicial", format_currency(patrimonio_base), None),
        ]
    )


def _render_charts(df: pd.DataFrame) -> None:
    titulo_secao("Evolução e Composição")
    if df.empty:
        show_empty_data("Sem dados para gerar gráficos de investimentos.")
        return

    data_col = "data_fim" if "data_fim" in df.columns else "data"
    work = df.copy().dropna(subset=[data_col])
    if work.empty:
        show_empty_data("Sem datas válidas para gráficos.")
        return

    work = work.sort_values(by=[data_col, "id"] if "id" in work.columns else [data_col], ascending=True)
    work["tipo_label"] = work["tipo_movimentacao"].map(TIPO_MOVIMENTACAO_LABELS).fillna("Movimentação")
    work["patrimonio total"] = pd.to_numeric(work["patrimonio total"], errors="coerce").fillna(0.0)
    work["rendimento"] = pd.to_numeric(work["rendimento"], errors="coerce").fillna(0.0)
    work["aporte_abs"] = work["aporte"].abs()

    col1, col2 = st.columns(2)
    with col1:
        serie = work[[data_col, "patrimonio total"]].dropna().groupby(data_col, as_index=False).last()
        fig_pat = px.line(serie, x=data_col, y="patrimonio total", markers=True, labels={data_col: "Data", "patrimonio total": "Patrimônio"})
        st.plotly_chart(fig_pat, use_container_width=True)
    with col2:
        composicao = (
            work.groupby(["categoria", "tipo_label"], as_index=False)["aporte_abs"]
            .sum()
            .rename(columns={"aporte_abs": "valor"})
        )
        if composicao["valor"].sum() <= 0:
            composicao = work.groupby("categoria", as_index=False)["rendimento"].sum().rename(columns={"rendimento": "valor"})
            fig_comp = px.bar(
                composicao,
                x="categoria",
                y="valor",
                labels={"categoria": "Categoria", "valor": "Valor"},
            )
        else:
            fig_comp = px.bar(
                composicao,
                x="categoria",
                y="valor",
                color="tipo_label",
                labels={"categoria": "Categoria", "valor": "Valor"},
            )
        st.plotly_chart(fig_comp, use_container_width=True)


def _render_projection(df: pd.DataFrame) -> None:
    titulo_secao("Projeções")
    if df.empty:
        show_empty_data("Cadastre investimentos para gerar projeções.")
        return

    analytics_df = _analytics_frame(df)
    patrimonio_base = float(analytics_patrimonio_atual(analytics_df))
    aportes = analytics_df.copy()
    aportes["data_ref"] = pd.to_datetime(aportes.get("data_fim", aportes.get("data")), errors="coerce")
    aportes = aportes.dropna(subset=["data_ref"])
    aportes["aporte"] = pd.to_numeric(aportes["aporte"], errors="coerce").fillna(0.0)
    aportes = aportes[aportes["aporte"] > 0].copy()

    media_aportes = 0.0
    if not aportes.empty:
        mensal = (
            aportes.assign(mes=aportes["data_ref"].dt.to_period("M").astype(str))
            .groupby("mes", as_index=False)["aporte"]
            .sum()
        )
        media_aportes = float(mensal["aporte"].mean()) if not mensal.empty else 0.0

    sim_auto, sim_custom = st.tabs(["Simulador da Carteira", "Simulador Personalizado"])

    with sim_auto:
        st.caption("Projeção automática com base no patrimônio atual e na média histórica mensal de aportes da carteira.")
        col1, col2 = st.columns(2)
        with col1:
            taxa_anual_pct = st.number_input("Taxa anual projetada (%)", min_value=0.0, value=12.0, step=0.5, key="inv_proj_auto_taxa_anual_pct")
        with col2:
            anos = st.number_input("Prazo (anos)", min_value=1, max_value=100, value=10, step=1, key="inv_proj_auto_anos")
        meses_extra = st.number_input("Meses adicionais", min_value=0, max_value=11, value=0, step=1, key="inv_proj_auto_meses_extra")

        meses = int(anos) * 12 + int(meses_extra)
        taxa_anual = float(taxa_anual_pct) / 100.0
        taxa_mensal = (1.0 + taxa_anual) ** (1.0 / 12.0) - 1.0 if taxa_anual > 0 else 0.0
        valor_projetado = float(projecao_com_aporte(analytics_df, taxa_mensal, int(meses), float(media_aportes)))
        ganho_proj = float(valor_projetado - patrimonio_base)

        render_kpi_grid(
            [
                ("Patrimônio projetado", format_currency(valor_projetado), None),
                ("Ganho projetado", format_currency(ganho_proj), None),
                ("Média mensal de aportes", format_currency(float(media_aportes)), None),
            ]
        )

        valores = []
        for mes in range(0, int(meses) + 1):
            patrimonio_mes = float(projecao_com_aporte(analytics_df, taxa_mensal, mes, float(media_aportes)))
            aportes_mes = float(media_aportes) * int(mes)
            juros_mes = float(max(0.0, patrimonio_mes - patrimonio_base - aportes_mes))
            valores.append(
                {
                    "mes": mes,
                    "patrimonio": patrimonio_mes,
                    "aportes_acumulados": float(aportes_mes),
                    "juros_acumulados": float(juros_mes),
                }
            )
        proj_df = pd.DataFrame(valores)
        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(x=proj_df["mes"], y=proj_df["patrimonio"], mode="lines+markers", name="Patrimônio total"))
        fig_proj.add_trace(go.Scatter(x=proj_df["mes"], y=proj_df["aportes_acumulados"], mode="lines", name="Aportes acumulados"))
        fig_proj.add_trace(go.Scatter(x=proj_df["mes"], y=proj_df["juros_acumulados"], mode="lines", name="Juros acumulados"))
        fig_proj.update_layout(xaxis_title="Mês", yaxis_title="Valor")
        st.plotly_chart(fig_proj, use_container_width=True, key="inv_proj_auto_chart")
        cruzamento_auto = proj_df[proj_df["juros_acumulados"] >= proj_df["aportes_acumulados"]]
        if not cruzamento_auto.empty:
            st.caption(f"No simulador da carteira, a curva de juros alcança ou supera a de aportes no mês {int(cruzamento_auto.iloc[0]['mes'])}.")
        else:
            st.caption("No horizonte informado, a curva de juros ainda não supera a curva de aportes.")

    with sim_custom:
        st.caption("Projeção personalizada com controle do aporte mensal, mantendo a mesma base de patrimônio atual.")
        col1, col2 = st.columns(2)
        with col1:
            taxa_custom_pct = st.number_input("Taxa anual personalizada (%)", min_value=0.0, value=12.0, step=0.5, key="inv_proj_custom_taxa_anual_pct")
        with col2:
            anos_custom = st.number_input("Prazo (anos)", min_value=1, max_value=100, value=10, step=1, key="inv_proj_custom_anos")
        meses_custom_extra = st.number_input("Meses adicionais", min_value=0, max_value=11, value=0, step=1, key="inv_proj_custom_meses_extra")

        aporte_custom = st.number_input(
            "Aporte mensal personalizado",
            min_value=0.0,
            value=float(media_aportes),
            step=100.0,
            key="inv_proj_custom_aporte",
        )

        meses_custom = int(anos_custom) * 12 + int(meses_custom_extra)
        taxa_custom_anual = float(taxa_custom_pct) / 100.0
        taxa_custom_mensal = (1.0 + taxa_custom_anual) ** (1.0 / 12.0) - 1.0 if taxa_custom_anual > 0 else 0.0
        valor_custom = float(projecao_com_aporte(analytics_df, taxa_custom_mensal, int(meses_custom), float(aporte_custom)))
        ganho_custom = float(valor_custom - patrimonio_base)

        render_kpi_grid(
            [
                ("Patrimônio projetado", format_currency(valor_custom), None),
                ("Ganho projetado", format_currency(ganho_custom), None),
                ("Aportes futuros", format_currency(float(aporte_custom) * int(meses_custom)), None),
            ]
        )

        valores_custom = []
        for mes in range(0, int(meses_custom) + 1):
            patrimonio_mes = float(projecao_com_aporte(analytics_df, taxa_custom_mensal, mes, float(aporte_custom)))
            aportes_mes = float(aporte_custom) * int(mes)
            juros_mes = float(max(0.0, patrimonio_mes - patrimonio_base - aportes_mes))
            valores_custom.append(
                {
                    "mes": mes,
                    "patrimonio": patrimonio_mes,
                    "aportes_acumulados": float(aportes_mes),
                    "juros_acumulados": float(juros_mes),
                }
            )
        proj_custom_df = pd.DataFrame(valores_custom)
        fig_custom = go.Figure()
        fig_custom.add_trace(go.Scatter(x=proj_custom_df["mes"], y=proj_custom_df["patrimonio"], mode="lines+markers", name="Patrimônio total"))
        fig_custom.add_trace(go.Scatter(x=proj_custom_df["mes"], y=proj_custom_df["aportes_acumulados"], mode="lines", name="Aportes acumulados"))
        fig_custom.add_trace(go.Scatter(x=proj_custom_df["mes"], y=proj_custom_df["juros_acumulados"], mode="lines", name="Juros acumulados"))
        fig_custom.update_layout(xaxis_title="Mês", yaxis_title="Valor")
        st.plotly_chart(fig_custom, use_container_width=True, key="inv_proj_custom_chart")
        cruzamento_custom = proj_custom_df[proj_custom_df["juros_acumulados"] >= proj_custom_df["aportes_acumulados"]]
        if not cruzamento_custom.empty:
            st.caption(f"No simulador personalizado, a curva de juros alcança ou supera a de aportes no mês {int(cruzamento_custom.iloc[0]['mes'])}.")
        else:
            st.caption("No horizonte informado, a curva de juros ainda não supera a curva de aportes.")

    st.caption("Ambos os simuladores usam juros compostos sobre o patrimônio atual; o primeiro usa a média histórica de aportes e o segundo permite sobrescrever esse valor.")


def _render_forms(df_investimentos: pd.DataFrame) -> None:
    titulo_secao("Gestão de Investimentos")

    categorias_invest = INVEST_CATEGORIAS.copy()
    for key in ["cad_inv_aporte_categoria", "cad_inv_rend_categoria", "cad_inv_ret_categoria"]:
        cat = str(st.session_state.get(key, "")).strip()
        if cat and cat not in categorias_invest:
            categorias_invest.append(cat)
    for cat in sorted(df_investimentos["categoria"].dropna().astype(str).unique().tolist()) if not df_investimentos.empty else []:
        if cat and cat not in categorias_invest:
            categorias_invest.append(cat)

    df_investimentos = _sort_desc_by_id(df_investimentos)
    df_aportes = _sort_desc_by_id(df_investimentos[df_investimentos["aporte"] > 0].copy()) if not df_investimentos.empty else pd.DataFrame()
    df_rendimentos = _sort_desc_by_id(df_investimentos[df_investimentos["aporte"] == 0].copy()) if not df_investimentos.empty else pd.DataFrame()
    df_retiradas = _sort_desc_by_id(df_investimentos[df_investimentos["aporte"] < 0].copy()) if not df_investimentos.empty else pd.DataFrame()
    patrimonio_atual = _patrimonio_atual(df_investimentos)

    tab_aporte, tab_rendimento, tab_retirada = st.tabs(["Aportes", "Rendimentos", "Retiradas"])

    with tab_aporte:
        st.caption("Aportes incrementam o patrimônio. O rendimento deste lançamento permanece zerado.")
        options_aporte = [None] + (df_aportes["id"].astype(int).tolist() if "id" in df_aportes.columns else [])
        _ensure_selected_option("cad_inv_aporte_selected_id", options_aporte)
        st.selectbox(
            "Registro de aporte",
            options=options_aporte,
            format_func=lambda x: _investimento_aporte_label(df_aportes, x),
            key="cad_inv_aporte_selected_id",
        )
        _sync_edit_state(df_aportes, "cad_inv_aporte_selected_id", "cad_inv_aporte_last_selected_id", _set_invest_aporte_fields)

        with st.form("investimentos_aporte_form"):
            data = st.date_input("Data", key="cad_inv_aporte_data")
            categoria = st.selectbox("Categoria", options=categorias_invest, key="cad_inv_aporte_categoria")
            aporte = st.number_input("Valor do aporte", min_value=0.0, key="cad_inv_aporte_valor")
            selected_aporte_id = st.session_state.get("cad_inv_aporte_selected_id")
            selected_aporte_row = _get_row_by_id(df_aportes, selected_aporte_id)
            aporte_antigo = float(selected_aporte_row["aporte"]) if selected_aporte_row is not None else 0.0
            patrimonio_preview = max(0.0, float(patrimonio_atual) - float(aporte_antigo) + float(aporte))
            st.number_input("Rendimento", value=0.0, disabled=True, key="inv_aporte_rendimento_zero")
            st.number_input("Patrimônio total (automático)", value=float(patrimonio_preview), disabled=True, key="inv_aporte_patrimonio_preview")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_inv_aporte_confirmar_exclusao")

            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            selected_id = st.session_state.get("cad_inv_aporte_selected_id")
            data_valida = _safe_date_or_none(data)

            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.criar_investimento(
                            data_valida.isoformat(),
                            categoria,
                            float(aporte),
                            0.0,
                            0.0,
                            float(patrimonio_preview),
                            data_inicio=data_valida.isoformat(),
                            data_fim=data_valida.isoformat(),
                            tipo_movimentacao="APORTE",
                        )
                        st.success("Aporte salvo com sucesso.")
                        _reset_fields([
                            "cad_inv_aporte_selected_id",
                            "cad_inv_aporte_last_selected_id",
                            "cad_inv_aporte_data",
                            "cad_inv_aporte_categoria",
                            "cad_inv_aporte_valor",
                            "cad_inv_aporte_confirmar_exclusao",
                            "inv_aporte_rendimento_zero",
                            "inv_aporte_patrimonio_preview",
                        ])
                        st.rerun()

                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.atualizar_investimento(
                            int(selected_id),
                            data_valida.isoformat(),
                            categoria,
                            float(aporte),
                            0.0,
                            0.0,
                            float(patrimonio_preview),
                            data_inicio=data_valida.isoformat(),
                            data_fim=data_valida.isoformat(),
                            tipo_movimentacao="APORTE",
                        )
                        st.success("Aporte atualizado com sucesso.")
                        st.rerun()

                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_investimento(int(selected_id))
                        st.success("Aporte excluído com sucesso.")
                        _reset_fields(["cad_inv_aporte_selected_id", "cad_inv_aporte_last_selected_id", "cad_inv_aporte_confirmar_exclusao"])
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar aporte: {exc}")

    with tab_rendimento:
        st.caption("Rendimentos mantêm o aporte zerado e incrementam o patrimônio pelo período informado.")
        categoria_r = str(st.session_state.get("cad_inv_rend_categoria", "Renda Fixa"))
        categorias_r = categorias_invest.copy()
        if categoria_r not in categorias_r:
            categorias_r.append(categoria_r)
        options_r = [None] + (df_rendimentos["id"].astype(int).tolist() if "id" in df_rendimentos.columns else [])
        _ensure_selected_option("cad_inv_rend_selected_id", options_r)
        st.selectbox(
            "Registro de rendimento",
            options=options_r,
            format_func=lambda x: _investimento_rendimento_label(df_rendimentos, x),
            key="cad_inv_rend_selected_id",
        )
        _sync_edit_state(df_rendimentos, "cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id", _set_invest_rendimento_fields)

        with st.form("investimentos_rendimento_form"):
            st.selectbox("Categoria", options=categorias_r, key="cad_inv_rend_categoria")
            categoria_sel = str(st.session_state.get("cad_inv_rend_categoria", "Renda Fixa"))
            col_ini, col_fim = st.columns(2)
            with col_ini:
                data_inicio = st.date_input("Data inicial do recorte", key="cad_inv_rend_data_inicio")
            with col_fim:
                data_fim = st.date_input("Data final do recorte", key="cad_inv_rend_data_fim")
            rendimento = st.number_input("Rendimento (R$)", value=0.0, step=1.0, key="cad_inv_rend_rendimento")
            selected_id = st.session_state.get("cad_inv_rend_selected_id")
            selected_row = _get_row_by_id(df_rendimentos, selected_id)
            rendimento_antigo = float(selected_row["rendimento"]) if selected_row is not None else 0.0
            patrimonio_preview = max(0.0, float(patrimonio_atual) - float(rendimento_antigo) + float(rendimento))
            st.number_input("Aporte", value=0.0, disabled=True, key="inv_rend_aporte_zero")
            st.number_input("Patrimônio total (automático)", value=float(patrimonio_preview), disabled=True, key="inv_rend_patrimonio_preview")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_inv_rend_confirmar_exclusao")

            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            data_inicio_valida = _safe_date_or_none(data_inicio)
            data_fim_valida = _safe_date_or_none(data_fim)
            try:
                if salvar:
                    if data_inicio_valida is None or data_fim_valida is None:
                        st.warning("Selecione datas válidas para o recorte.")
                    elif data_fim_valida < data_inicio_valida:
                        st.warning("A data final do recorte deve ser maior ou igual à data inicial.")
                    else:
                        service.criar_investimento(
                            data_fim_valida.isoformat(),
                            categoria_sel,
                            0.0,
                            0.0,
                            float(rendimento),
                            float(patrimonio_preview),
                            data_inicio=data_inicio_valida.isoformat(),
                            data_fim=data_fim_valida.isoformat(),
                            tipo_movimentacao="RENDIMENTO",
                        )
                        st.success("Rendimento salvo com sucesso.")
                        _reset_fields([
                            "cad_inv_rend_selected_id",
                            "cad_inv_rend_last_selected_id",
                            "cad_inv_rend_data_inicio",
                            "cad_inv_rend_data_fim",
                            "cad_inv_rend_rendimento",
                            "cad_inv_rend_confirmar_exclusao",
                            "inv_rend_aporte_zero",
                            "inv_rend_patrimonio_preview",
                            "cad_inv_rend_categoria",
                        ])
                        st.rerun()

                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_inicio_valida is None or data_fim_valida is None:
                        st.warning("Selecione datas válidas para o recorte.")
                    elif data_fim_valida < data_inicio_valida:
                        st.warning("A data final do recorte deve ser maior ou igual à data inicial.")
                    else:
                        service.atualizar_investimento(
                            int(selected_id),
                            data_fim_valida.isoformat(),
                            categoria_sel,
                            0.0,
                            0.0,
                            float(rendimento),
                            float(patrimonio_preview),
                            data_inicio=data_inicio_valida.isoformat(),
                            data_fim=data_fim_valida.isoformat(),
                            tipo_movimentacao="RENDIMENTO",
                        )
                        st.success("Rendimento atualizado com sucesso.")
                        st.rerun()

                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_investimento(int(selected_id))
                        st.success("Rendimento excluído com sucesso.")
                        _reset_fields(["cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id", "cad_inv_rend_confirmar_exclusao"])
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar rendimento: {exc}")

    with tab_retirada:
        st.caption("Retiradas reduzem patrimônio. O valor é salvo como aporte negativo.")
        categoria_ret = str(st.session_state.get("cad_inv_ret_categoria", "Renda Fixa"))
        categorias_ret = categorias_invest.copy()
        if categoria_ret not in categorias_ret:
            categorias_ret.append(categoria_ret)
        options_ret = [None] + (df_retiradas["id"].astype(int).tolist() if "id" in df_retiradas.columns else [])
        _ensure_selected_option("cad_inv_ret_selected_id", options_ret)
        st.selectbox(
            "Registro de retirada",
            options=options_ret,
            format_func=lambda x: _investimento_retirada_label(df_retiradas, x),
            key="cad_inv_ret_selected_id",
        )
        _sync_edit_state(df_retiradas, "cad_inv_ret_selected_id", "cad_inv_ret_last_selected_id", _set_invest_retirada_fields)

        with st.form("investimentos_retirada_form"):
            data = st.date_input("Data da retirada", key="cad_inv_ret_data")
            categoria = st.selectbox("Categoria", options=categorias_ret, key="cad_inv_ret_categoria")
            retirada = st.number_input("Valor da retirada", min_value=0.0, key="cad_inv_ret_valor")
            selected_id = st.session_state.get("cad_inv_ret_selected_id")
            selected_row = _get_row_by_id(df_retiradas, selected_id)
            retirada_antiga = abs(float(selected_row["aporte"])) if selected_row is not None else 0.0
            patrimonio_disponivel = float(patrimonio_atual) + float(retirada_antiga)
            patrimonio_preview = max(0.0, patrimonio_disponivel - float(retirada))
            st.number_input("Rendimento", value=0.0, disabled=True, key="inv_ret_rendimento_zero")
            st.number_input("Patrimônio total (automático)", value=float(patrimonio_preview), disabled=True, key="inv_ret_patrimonio_preview")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_inv_ret_confirmar_exclusao")

            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            data_valida = _safe_date_or_none(data)
            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif float(retirada) > float(patrimonio_disponivel):
                        st.warning("Retirada maior que o patrimônio disponível.")
                    else:
                        service.criar_investimento(
                            data_valida.isoformat(),
                            categoria,
                            float(-retirada),
                            0.0,
                            0.0,
                            float(patrimonio_preview),
                            data_inicio=data_valida.isoformat(),
                            data_fim=data_valida.isoformat(),
                            tipo_movimentacao="RETIRADA",
                        )
                        st.success("Retirada salva com sucesso.")
                        _reset_fields([
                            "cad_inv_ret_selected_id",
                            "cad_inv_ret_last_selected_id",
                            "cad_inv_ret_data",
                            "cad_inv_ret_categoria",
                            "cad_inv_ret_valor",
                            "cad_inv_ret_confirmar_exclusao",
                            "inv_ret_rendimento_zero",
                            "inv_ret_patrimonio_preview",
                        ])
                        st.rerun()

                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif float(retirada) > float(patrimonio_disponivel):
                        st.warning("Retirada maior que o patrimônio disponível.")
                    else:
                        service.atualizar_investimento(
                            int(selected_id),
                            data_valida.isoformat(),
                            categoria,
                            float(-retirada),
                            0.0,
                            0.0,
                            float(patrimonio_preview),
                            data_inicio=data_valida.isoformat(),
                            data_fim=data_valida.isoformat(),
                            tipo_movimentacao="RETIRADA",
                        )
                        st.success("Retirada atualizada com sucesso.")
                        st.rerun()

                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_investimento(int(selected_id))
                        st.success("Retirada excluída com sucesso.")
                        _reset_fields(["cad_inv_ret_selected_id", "cad_inv_ret_last_selected_id", "cad_inv_ret_confirmar_exclusao"])
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar retirada: {exc}")


def _render_table(df: pd.DataFrame) -> None:
    titulo_secao("Registros")
    if df.empty:
        show_empty_data("Nenhum investimento cadastrado.")
        return

    tabela = _with_display_order(df)
    for col in ["data", "data_inicio", "data_fim"]:
        if col in tabela.columns:
            tabela[col] = pd.to_datetime(tabela[col], errors="coerce").dt.date
    for col in ["aporte", "total aportado", "rendimento", "patrimonio total"]:
        if col in tabela.columns:
            tabela[col] = pd.to_numeric(tabela[col], errors="coerce").fillna(0.0).apply(formatar_moeda)
    if "tipo_movimentacao" in tabela.columns:
        tabela["tipo_movimentacao"] = tabela["tipo_movimentacao"].map(TIPO_MOVIMENTACAO_LABELS).fillna("Movimentação")
    st.dataframe(tabela, width="stretch", hide_index=True)


def pagina_investimentos() -> None:
    st.header("Investimentos")

    df_investimentos = _prepare_investimentos(service.listar_investimentos())
    modo_periodo = st.radio("Visualização", ["Mensal", "Personalizado"], horizontal=True, key="inv_modo_periodo")
    df_filtrado, titulo = _filter_period(df_investimentos, modo_periodo)

    titulo_secao(titulo)
    _render_summary(df_filtrado)
    _render_charts(df_filtrado)
    _render_projection(df_filtrado if not df_filtrado.empty else df_investimentos)
    _render_forms(df_investimentos.sort_values(by="id", ascending=False) if not df_investimentos.empty and "id" in df_investimentos.columns else df_investimentos)
    _render_table(df_filtrado if not df_filtrado.empty else df_investimentos)

    if df_investimentos.empty:
        st.caption("Nenhum investimento encontrado ainda. Use os formulários acima para cadastrar aportes, rendimentos ou retiradas.")
