"""Cadastros UI page with full CRUD and form state management."""

from __future__ import annotations

from datetime import time

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import formatar_moeda, titulo_secao


service = DashboardService()
INVEST_CATEGORIAS = ["Renda Fixa", "Renda Variável"]
DESPESAS_CATEGORIAS_PREDEFINIDAS = [
    "Combustível",
    "Lava-Jato",
    "Pedágio",
    "Manutenção",
    "Impostos em geral",
    "Multas",
    "Estacionamento",
    "Contas da Casa",
    "Faturas de Cartão",
    "Outros",
]


def _safe_date_or_none(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _safe_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _date_or_today(value):
    date_value = _safe_date_or_none(value)
    if date_value is None:
        return pd.Timestamp.today().date()
    return date_value


def _time_from_seconds(value) -> time:
    total = max(0, _safe_int(value))
    horas = (total // 3600) % 24
    minutos = (total % 3600) // 60
    segundos = total % 60
    return time(horas, minutos, segundos)


def _get_row_by_id(df: pd.DataFrame, selected_id: int | None) -> pd.Series | None:
    if selected_id is None or df.empty or "id" not in df.columns:
        return None
    row = df[df["id"] == int(selected_id)]
    if row.empty:
        return None
    return row.iloc[0]


def _reset_fields(keys: list[str]) -> None:
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def _set_receita_fields(row: pd.Series | None) -> None:
    st.session_state["cad_receita_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_receita_valor"] = float(row["valor"]) if row is not None else 0.0
    st.session_state["cad_receita_km"] = float(row["km"]) if row is not None else 0.0
    st.session_state["cad_receita_tempo"] = _time_from_seconds(row["tempo trabalhado"] if row is not None else 0)
    st.session_state["cad_receita_obs"] = str(row.get("observacao", "")) if row is not None else ""


def _set_despesa_fields(row: pd.Series | None) -> None:
    st.session_state["cad_despesa_data"] = _date_or_today(row["data"] if row is not None else None)
    categoria = str(row["categoria"]) if row is not None else "Outros"
    st.session_state["cad_despesa_categoria_select"] = (
        categoria if categoria in DESPESAS_CATEGORIAS_PREDEFINIDAS else "Outros"
    )
    st.session_state["cad_despesa_valor"] = float(row["valor"]) if row is not None else 0.0
    st.session_state["cad_despesa_obs"] = str(row.get("observacao", "")) if row is not None else ""


def _set_investimento_fields(row: pd.Series | None) -> None:
    st.session_state["cad_invest_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_invest_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_invest_rendimento"] = float(row["rendimento"]) if row is not None else 0.0
    st.session_state["cad_invest_patrimonio"] = float(row["patrimonio total"]) if row is not None else 0.0


def _set_invest_rendimento_fields(row: pd.Series | None) -> None:
    """Pre-fill rendimento form state from selected investment row."""

    st.session_state["cad_inv_rend_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_inv_rend_rendimento"] = float(row["rendimento"]) if row is not None else 0.0
    st.session_state["cad_inv_rend_patrimonio"] = float(row["patrimonio total"]) if row is not None else 0.0
    if row is not None and "categoria" in row:
        st.session_state["cad_inv_rend_categoria"] = str(row.get("categoria", "Renda Fixa"))


def _sync_edit_state(df: pd.DataFrame, select_key: str, last_key: str, setter) -> int | None:
    selected_id = st.session_state.get(select_key)
    last_selected = st.session_state.get(last_key)
    if selected_id != last_selected:
        setter(_get_row_by_id(df, selected_id))
        st.session_state[last_key] = selected_id
    return selected_id


def _receita_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    return f"ID {item_id} | {data_txt} | {formatar_moeda(float(row['valor']))}"


def _despesa_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    categoria = str(row["categoria"]).strip() or "Sem categoria"
    return f"ID {item_id} | {data_txt} | {categoria}"


def _investimento_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    cat = str(row.get("categoria", "Renda Fixa"))
    return f"ID {item_id} | {data_txt} | {cat} | Aporte {formatar_moeda(float(row['aporte']))}"


def _investimento_rendimento_label(df: pd.DataFrame, item_id: int | None) -> str:
    """Build friendly label for rendimento-focused selection list."""

    if item_id is None:
        return "Novo lançamento"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    cat = str(row.get("categoria", "Renda Fixa"))
    rendimento = formatar_moeda(float(row.get("rendimento", 0.0)))
    return f"ID {item_id} | {data_txt} | {cat} | Rend. {rendimento}"


def pagina_cadastros() -> None:
    """Render central CRUD page for receitas, despesas and investimentos."""

    st.header("Cadastros")
    tab_receitas, tab_despesas, tab_investimentos = st.tabs(["Receitas", "Despesas", "Investimentos"])

    with tab_receitas:
        titulo_secao("CRUD de Receitas")
        df_receitas = service.listar_receitas()
        if not df_receitas.empty and "id" in df_receitas.columns:
            df_receitas = df_receitas.sort_values(by="id", ascending=False)
        options = [None] + (df_receitas["id"].astype(int).tolist() if "id" in df_receitas.columns else [])

        with st.form("cad_receita_form"):
            st.selectbox("Registro", options=options, format_func=lambda x: _receita_label(df_receitas, x), key="cad_receita_selected_id")
            _sync_edit_state(df_receitas, "cad_receita_selected_id", "cad_receita_last_selected_id", _set_receita_fields)

            data = st.date_input("Data", key="cad_receita_data")
            valor = st.number_input("Valor", min_value=0.0, key="cad_receita_valor")
            km = st.number_input("KM", min_value=0.0, key="cad_receita_km")
            # time_input já permite precisão de 1 minuto no seletor padrão.
            tempo = st.time_input("Tempo trabalhado (hh:mm:ss)", value=time(0, 0, 0), key="cad_receita_tempo")
            observacao = st.text_input("Observação", key="cad_receita_obs")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_receita_confirmar_exclusao")

            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            selected_id = st.session_state.get("cad_receita_selected_id")
            data_valida = _safe_date_or_none(data)
            tempo_total = tempo.hour * 3600 + tempo.minute * 60 + tempo.second

            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.criar_receita(data_valida.isoformat(), float(valor), float(km), int(tempo_total), observacao)
                        st.success("Receita salva com sucesso.")
                        _reset_fields([
                            "cad_receita_selected_id", "cad_receita_last_selected_id", "cad_receita_data",
                            "cad_receita_valor", "cad_receita_km", "cad_receita_tempo", "cad_receita_obs",
                            "cad_receita_confirmar_exclusao",
                        ])
                        st.rerun()

                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.atualizar_receita(int(selected_id), data_valida.isoformat(), float(valor), float(km), int(tempo_total), observacao)
                        st.success("Receita atualizada com sucesso.")
                        st.rerun()

                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_receita(int(selected_id))
                        st.success("Receita excluída com sucesso.")
                        _reset_fields(["cad_receita_selected_id", "cad_receita_last_selected_id", "cad_receita_confirmar_exclusao"])
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar receita: {exc}")

    with tab_despesas:
        titulo_secao("CRUD de Despesas")
        df_despesas = service.listar_despesas()
        if not df_despesas.empty and "id" in df_despesas.columns:
            df_despesas = df_despesas.sort_values(by="id", ascending=False)
        options = [None] + (df_despesas["id"].astype(int).tolist() if "id" in df_despesas.columns else [])

        with st.form("cad_despesa_form"):
            st.selectbox("Registro", options=options, format_func=lambda x: _despesa_label(df_despesas, x), key="cad_despesa_selected_id")
            _sync_edit_state(df_despesas, "cad_despesa_selected_id", "cad_despesa_last_selected_id", _set_despesa_fields)

            data = st.date_input("Data", key="cad_despesa_data")
            categoria_escolhida = st.selectbox(
                "Categoria",
                options=DESPESAS_CATEGORIAS_PREDEFINIDAS,
                key="cad_despesa_categoria_select",
            )
            valor = st.number_input("Valor", min_value=0.0, key="cad_despesa_valor")
            observacao = st.text_input("Observação", key="cad_despesa_obs")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_despesa_confirmar_exclusao")

            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            selected_id = st.session_state.get("cad_despesa_selected_id")
            data_valida = _safe_date_or_none(data)
            categoria_escolhida = str(categoria_escolhida).strip()

            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif not categoria_escolhida:
                        st.warning("Informe uma nova categoria ou selecione uma existente.")
                    else:
                        service.criar_despesa(data_valida.isoformat(), categoria_escolhida, float(valor), observacao)
                        st.success("Despesa salva com sucesso.")
                        _reset_fields([
                            "cad_despesa_selected_id", "cad_despesa_last_selected_id", "cad_despesa_data",
                            "cad_despesa_categoria_select", "cad_despesa_valor",
                            "cad_despesa_obs", "cad_despesa_confirmar_exclusao",
                        ])
                        st.rerun()

                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif not categoria_escolhida:
                        st.warning("Informe uma nova categoria ou selecione uma existente.")
                    else:
                        service.atualizar_despesa(int(selected_id), data_valida.isoformat(), categoria_escolhida, float(valor), observacao)
                        st.success("Despesa atualizada com sucesso.")
                        st.rerun()

                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_despesa(int(selected_id))
                        st.success("Despesa excluída com sucesso.")
                        _reset_fields(["cad_despesa_selected_id", "cad_despesa_last_selected_id", "cad_despesa_confirmar_exclusao"])
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar despesa: {exc}")

    with tab_investimentos:
        titulo_secao("CRUD de Investimentos")
        df_investimentos = service.listar_investimentos()
        if "categoria" not in df_investimentos.columns and not df_investimentos.empty:
            df_investimentos["categoria"] = "Renda Fixa"
        if not df_investimentos.empty and "id" in df_investimentos.columns:
            df_investimentos = df_investimentos.sort_values(by="id", ascending=False)
        options = [None] + (df_investimentos["id"].astype(int).tolist() if "id" in df_investimentos.columns else [])
        categoria_invest = str(st.session_state.get("cad_invest_categoria", "Renda Fixa"))
        categorias_invest = INVEST_CATEGORIAS.copy()
        if categoria_invest not in categorias_invest:
            categorias_invest.append(categoria_invest)

        sub_aportes, sub_rendimentos = st.tabs(["Aportes e Patrimônio (CRUD)", "Rendimentos por Categoria"])

        with sub_aportes:
            st.caption("Informe patrimônio total e rendimento informado. Em novo aporte sem rendimento, use 0 e o sistema não criará aporte negativo.")
            with st.form("cad_investimento_form"):
                st.selectbox("Registro", options=options, format_func=lambda x: _investimento_label(df_investimentos, x), key="cad_invest_selected_id")
                _sync_edit_state(df_investimentos, "cad_invest_selected_id", "cad_invest_last_selected_id", _set_investimento_fields)

                data = st.date_input("Data", key="cad_invest_data")
                categoria = st.selectbox("Categoria", options=categorias_invest, key="cad_invest_categoria")
                st.number_input("Valor (aporte)", min_value=0.0, value=0.0, disabled=True, key="cad_invest_aporte_preview")
                st.caption("Aporte calculado automaticamente no momento do envio.")
                rendimento = st.number_input("Rendimento informado (total)", min_value=0.0, key="cad_invest_rendimento")
                patrimonio_total = st.number_input("Patrimônio total", min_value=0.0, key="cad_invest_patrimonio")
                confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_invest_confirmar_exclusao")

                col1, col2, col3 = st.columns(3)
                salvar = col1.form_submit_button("Salvar (novo)")
                atualizar = col2.form_submit_button("Atualizar")
                excluir = col3.form_submit_button("Excluir")

                selected_id = st.session_state.get("cad_invest_selected_id")
                data_valida = _safe_date_or_none(data)

                try:
                    if salvar:
                        if data_valida is None:
                            st.warning("Selecione uma data válida.")
                        else:
                            aporte_auto = service.calcular_aporte_investimento(
                                data=data_valida.isoformat(),
                                categoria=categoria,
                                patrimonio_total=float(patrimonio_total),
                                rendimento_total=float(rendimento),
                            )
                            service.criar_investimento(
                                data_valida.isoformat(),
                                categoria,
                                float(aporte_auto),
                                0.0,
                                float(rendimento),
                                float(patrimonio_total),
                            )
                            st.success("Aporte salvo com sucesso.")
                            _reset_fields([
                                "cad_invest_selected_id", "cad_invest_last_selected_id", "cad_invest_data",
                                "cad_invest_categoria", "cad_invest_rendimento", "cad_invest_patrimonio",
                                "cad_invest_confirmar_exclusao", "cad_invest_aporte_preview",
                            ])
                            st.rerun()

                    if atualizar:
                        if selected_id is None:
                            st.warning("Selecione um registro para atualizar.")
                        elif data_valida is None:
                            st.warning("Selecione uma data válida.")
                        else:
                            aporte_auto = service.calcular_aporte_investimento(
                                data=data_valida.isoformat(),
                                categoria=categoria,
                                patrimonio_total=float(patrimonio_total),
                                rendimento_total=float(rendimento),
                                ignore_id=int(selected_id),
                            )
                            service.atualizar_investimento(
                                int(selected_id),
                                data_valida.isoformat(),
                                categoria,
                                float(aporte_auto),
                                0.0,
                                float(rendimento),
                                float(patrimonio_total),
                            )
                            st.success("Aporte/patrimônio atualizado com sucesso.")
                            st.rerun()

                    if excluir:
                        if selected_id is None:
                            st.warning("Selecione um registro para excluir.")
                        elif not confirmar_exclusao:
                            st.warning("Confirme a exclusão para continuar.")
                        else:
                            service.deletar_investimento(int(selected_id))
                            st.success("Registro de aporte excluído com sucesso.")
                            _reset_fields(["cad_invest_selected_id", "cad_invest_last_selected_id", "cad_invest_confirmar_exclusao"])
                            st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Erro ao processar aporte: {exc}")

        with sub_rendimentos:
            st.caption("Atualize rendimentos de forma independente por categoria sem perder o histórico dos registros.")
            categoria_r = str(st.session_state.get("cad_inv_rend_categoria", "Renda Fixa"))
            categorias_r = INVEST_CATEGORIAS.copy()
            if categoria_r not in categorias_r:
                categorias_r.append(categoria_r)

            with st.form("cad_invest_rendimento_form"):
                categoria_sel = st.selectbox("Categoria de rendimento", options=categorias_r, key="cad_inv_rend_categoria")
                df_rend = df_investimentos[df_investimentos["categoria"].astype(str) == categoria_sel] if not df_investimentos.empty else pd.DataFrame()
                options_r = [None] + (df_rend["id"].astype(int).tolist() if "id" in df_rend.columns else [])

                st.selectbox(
                    "Registro da categoria",
                    options=options_r,
                    format_func=lambda x: _investimento_rendimento_label(df_rend, x),
                    key="cad_inv_rend_selected_id",
                )
                _sync_edit_state(df_rend, "cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id", _set_invest_rendimento_fields)

                data_r = st.date_input("Data do rendimento", key="cad_inv_rend_data")
                rendimento_r = st.number_input("Rendimento", min_value=0.0, key="cad_inv_rend_rendimento")
                patrimonio_r = st.number_input("Patrimônio total (após rendimento)", min_value=0.0, key="cad_inv_rend_patrimonio")
                confirmar_exclusao_r = st.checkbox("Confirmo a exclusão deste registro", key="cad_inv_rend_confirmar_exclusao")

                col1, col2, col3 = st.columns(3)
                salvar_r = col1.form_submit_button("Salvar rendimento (novo)")
                atualizar_r = col2.form_submit_button("Atualizar rendimento")
                excluir_r = col3.form_submit_button("Excluir")

                selected_id_r = st.session_state.get("cad_inv_rend_selected_id")
                data_valida_r = _safe_date_or_none(data_r)
                try:
                    if salvar_r:
                        if data_valida_r is None:
                            st.warning("Selecione uma data válida.")
                        else:
                            aporte_auto = service.calcular_aporte_investimento(
                                data=data_valida_r.isoformat(),
                                categoria=categoria_sel,
                                patrimonio_total=float(patrimonio_r),
                                rendimento_total=float(rendimento_r),
                            )
                            service.criar_investimento(
                                data_valida_r.isoformat(),
                                categoria_sel,
                                float(aporte_auto),
                                0.0,
                                float(rendimento_r),
                                float(patrimonio_r),
                            )
                            st.success("Rendimento lançado com sucesso.")
                            _reset_fields([
                                "cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id", "cad_inv_rend_data",
                                "cad_inv_rend_rendimento", "cad_inv_rend_patrimonio", "cad_inv_rend_confirmar_exclusao",
                            ])
                            st.rerun()

                    if atualizar_r:
                        if selected_id_r is None:
                            st.warning("Selecione um registro para atualizar.")
                        elif data_valida_r is None:
                            st.warning("Selecione uma data válida.")
                        else:
                            aporte_auto = service.calcular_aporte_investimento(
                                data=data_valida_r.isoformat(),
                                categoria=categoria_sel,
                                patrimonio_total=float(patrimonio_r),
                                rendimento_total=float(rendimento_r),
                                ignore_id=int(selected_id_r),
                            )
                            service.atualizar_investimento(
                                int(selected_id_r),
                                data_valida_r.isoformat(),
                                categoria_sel,
                                float(aporte_auto),
                                0.0,
                                float(rendimento_r),
                                float(patrimonio_r),
                            )
                            st.success("Rendimento atualizado com sucesso.")
                            st.rerun()

                    if excluir_r:
                        if selected_id_r is None:
                            st.warning("Selecione um registro para excluir.")
                        elif not confirmar_exclusao_r:
                            st.warning("Confirme a exclusão para continuar.")
                        else:
                            service.deletar_investimento(int(selected_id_r))
                            st.success("Registro de rendimento excluído com sucesso.")
                            _reset_fields([
                                "cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id", "cad_inv_rend_confirmar_exclusao"
                            ])
                            st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Erro ao processar rendimento: {exc}")
