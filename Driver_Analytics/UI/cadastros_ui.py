"""Cadastros UI page with full CRUD and form state management."""

from __future__ import annotations

from datetime import time

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import formatar_moeda, titulo_secao


service = DashboardService()
INVEST_CATEGORIAS = ["Renda Fixa", "Renda Variável"]
DESPESAS_CATEGORIAS_NEGOCIO = sorted(
    [
        "Combustível",
        "Estacionamento",
        "Financiamento",
        "Impostos CNPJ",
        "IPVA",
        "Lava-Jato",
        "Manutenção",
        "Multas",
        "Pedágio",
        "Seguro",
        "Telefonia",
    ]
)
DESPESAS_CATEGORIAS_PESSOAL = sorted(
    [
        "Alimentação",
        "Contas da Casa",
        "Educação",
        "Faturas de Cartão",
        "Impostos CPF",
        "Lazer",
        "Outros",
        "Plano de Saúde",
        "Serviços Domésticos",
    ]
)
TIPOS_DESPESA_LABELS = {
    "VARIAVEL": "Variável",
    "RECORRENTE": "Recorrente",
    "FIXA": "Fixa",
}
TIPOS_DESPESA_OPTIONS = list(TIPOS_DESPESA_LABELS.values())
ESFERAS_DESPESA_LABELS = {
    "NEGOCIO": "Negócio",
    "PESSOAL": "Pessoal",
}
ESFERAS_DESPESA_OPTIONS = list(ESFERAS_DESPESA_LABELS.values())


def _categorias_por_esfera(esfera_label: str) -> list[str]:
    if str(esfera_label).strip().lower() == "pessoal":
        return DESPESAS_CATEGORIAS_PESSOAL
    return DESPESAS_CATEGORIAS_NEGOCIO


def _sync_categoria_despesa_por_esfera() -> None:
    esfera_label = str(st.session_state.get("cad_despesa_esfera", "Negócio"))
    categorias = _categorias_por_esfera(esfera_label)
    categoria_default = "Outros" if "Outros" in categorias else (categorias[0] if categorias else "")
    ultima_esfera = str(st.session_state.get("cad_despesa_last_esfera", ""))
    categoria_atual = str(st.session_state.get("cad_despesa_categoria_select", ""))

    if esfera_label != ultima_esfera:
        st.session_state["cad_despesa_categoria_select"] = categoria_default
    elif categoria_atual not in categorias:
        st.session_state["cad_despesa_categoria_select"] = categoria_default

    st.session_state["cad_despesa_last_esfera"] = esfera_label


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
    st.session_state["cad_receita_confirmar_exclusao"] = False


def _set_despesa_fields(row: pd.Series | None) -> None:
    st.session_state["cad_despesa_data"] = _date_or_today(row["data"] if row is not None else None)
    tipo_raw = str(row.get("tipo_despesa", "VARIAVEL")) if row is not None else "VARIAVEL"
    tipo_key = tipo_raw.strip().upper() if tipo_raw.strip().upper() in TIPOS_DESPESA_LABELS else "VARIAVEL"
    st.session_state["cad_despesa_tipo"] = TIPOS_DESPESA_LABELS[tipo_key]
    esfera_raw = str(row.get("esfera_despesa", "NEGOCIO")) if row is not None else "NEGOCIO"
    esfera_key = esfera_raw.strip().upper() if esfera_raw.strip().upper() in ESFERAS_DESPESA_LABELS else "NEGOCIO"
    esfera_label = ESFERAS_DESPESA_LABELS[esfera_key]
    st.session_state["cad_despesa_esfera"] = esfera_label
    st.session_state["cad_despesa_last_esfera"] = esfera_label
    categorias_validas = _categorias_por_esfera(esfera_label)
    categoria = str(row["categoria"]) if row is not None else "Outros"
    st.session_state["cad_despesa_categoria_select"] = (
        categoria if categoria in categorias_validas else "Outros"
    )
    st.session_state["cad_despesa_valor"] = float(row["valor"]) if row is not None else 0.0
    st.session_state["cad_despesa_litros"] = float(row.get("litros", 0.0)) if row is not None else 0.0
    st.session_state["cad_despesa_obs"] = str(row.get("observacao", "")) if row is not None else ""
    st.session_state["cad_despesa_subcategoria_fixa"] = str(row.get("subcategoria_fixa", "")) if row is not None else ""
    st.session_state["cad_despesa_confirmar_exclusao"] = False


def _set_investimento_fields(row: pd.Series | None) -> None:
    st.session_state["cad_invest_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_invest_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_invest_rendimento"] = float(row["rendimento"]) if row is not None else 0.0
    st.session_state["cad_invest_patrimonio"] = float(row["patrimonio total"]) if row is not None else 0.0


def _set_invest_aporte_fields(row: pd.Series | None) -> None:
    """Pre-fill aporte form state from selected investment row."""

    st.session_state["cad_inv_aporte_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_inv_aporte_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_inv_aporte_valor"] = float(row.get("aporte", 0.0)) if row is not None else 0.0
    st.session_state["cad_inv_aporte_patrimonio"] = float(row.get("patrimonio total", 0.0)) if row is not None else 0.0
    st.session_state["cad_inv_aporte_confirmar_exclusao"] = False


def _set_invest_rendimento_fields(row: pd.Series | None) -> None:
    """Pre-fill rendimento form state from selected investment row."""

    data_inicio = _date_or_today((row.get("data_inicio") if row is not None else None) or (row["data"] if row is not None else None))
    data_fim = _date_or_today((row.get("data_fim") if row is not None else None) or (row["data"] if row is not None else None))
    st.session_state["cad_inv_rend_data_inicio"] = data_inicio
    st.session_state["cad_inv_rend_data_fim"] = data_fim
    # Avoid mutating a key bound to an already-rendered widget in the same run.
    # The category selector is rendered before this setter is called.
    if "cad_inv_rend_categoria" not in st.session_state:
        st.session_state["cad_inv_rend_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_inv_rend_rendimento"] = float(row["rendimento"]) if row is not None else 0.0
    st.session_state["cad_inv_rend_patrimonio"] = float(row["patrimonio total"]) if row is not None else 0.0
    st.session_state["cad_inv_rend_confirmar_exclusao"] = False


def _set_invest_retirada_fields(row: pd.Series | None) -> None:
    """Pre-fill retirada form state from selected investment row."""

    st.session_state["cad_inv_ret_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_inv_ret_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_inv_ret_valor"] = abs(float(row.get("aporte", 0.0))) if row is not None else 0.0
    st.session_state["cad_inv_ret_patrimonio"] = float(row.get("patrimonio total", 0.0)) if row is not None else 0.0
    st.session_state["cad_inv_ret_confirmar_exclusao"] = False


def _sync_edit_state(df: pd.DataFrame, select_key: str, last_key: str, setter) -> int | None:
    selected_id = st.session_state.get(select_key)
    has_last = last_key in st.session_state
    last_selected = st.session_state.get(last_key)
    if (not has_last) or (selected_id != last_selected):
        setter(_get_row_by_id(df, selected_id))
        st.session_state[last_key] = selected_id
    return selected_id


def _ensure_selected_option(select_key: str, options: list[int | None]) -> None:
    current = st.session_state.get(select_key)
    if current not in options:
        st.session_state[select_key] = options[0] if options else None


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


def _investimento_aporte_label(df: pd.DataFrame, item_id: int | None) -> str:
    """Build friendly label for aporte-focused selection list."""

    if item_id is None:
        return "Novo lançamento"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    cat = str(row.get("categoria", "Renda Fixa"))
    aporte = formatar_moeda(float(row.get("aporte", 0.0)))
    return f"ID {item_id} | {data_txt} | {cat} | Aporte {aporte}"


def _investimento_retirada_label(df: pd.DataFrame, item_id: int | None) -> str:
    """Build friendly label for retirada-focused selection list."""

    if item_id is None:
        return "Novo lançamento"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    cat = str(row.get("categoria", "Renda Fixa"))
    retirada = formatar_moeda(abs(float(row.get("aporte", 0.0))))
    return f"ID {item_id} | {data_txt} | {cat} | Retirada {retirada}"


def _patrimonio_atual(df: pd.DataFrame) -> float:
    """Return latest patrimonio total snapshot from dataframe."""

    if df is None or df.empty:
        return 0.0
    work = df.copy()
    work["data"] = pd.to_datetime(work["data"], errors="coerce")
    work["patrimonio total"] = pd.to_numeric(work.get("patrimonio total"), errors="coerce").fillna(0.0)
    work = work.sort_values(by=["data", "id"], ascending=[True, True])
    return float(work.iloc[-1]["patrimonio total"]) if not work.empty else 0.0


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

        st.selectbox(
            "Registro",
            options=options,
            format_func=lambda x: _receita_label(df_receitas, x),
            key="cad_receita_selected_id",
        )
        _sync_edit_state(df_receitas, "cad_receita_selected_id", "cad_receita_last_selected_id", _set_receita_fields)

        with st.form("cad_receita_form"):
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
                        service.criar_receita(
                            data_valida.isoformat(),
                            float(valor),
                            float(km),
                            int(tempo_total),
                            observacao,
                        )
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
                        service.atualizar_receita(
                            int(selected_id),
                            data_valida.isoformat(),
                            float(valor),
                            float(km),
                            int(tempo_total),
                            observacao,
                        )
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

        st.selectbox(
            "Registro",
            options=options,
            format_func=lambda x: _despesa_label(df_despesas, x),
            key="cad_despesa_selected_id",
        )
        _sync_edit_state(df_despesas, "cad_despesa_selected_id", "cad_despesa_last_selected_id", _set_despesa_fields)
        st.selectbox(
            "Escopo da despesa",
            options=ESFERAS_DESPESA_OPTIONS,
            key="cad_despesa_esfera",
        )
        _sync_categoria_despesa_por_esfera()
        categorias_despesa = _categorias_por_esfera(str(st.session_state.get("cad_despesa_esfera", "Negócio")))

        with st.form("cad_despesa_form"):
            data = st.date_input("Data", key="cad_despesa_data")
            categoria_escolhida = st.selectbox(
                "Categoria",
                options=categorias_despesa,
                key="cad_despesa_categoria_select",
            )
            tipo_despesa_label = st.selectbox(
                "Tipo de despesa",
                options=TIPOS_DESPESA_OPTIONS,
                key="cad_despesa_tipo",
            )
            subcategoria_fixa = ""
            if str(tipo_despesa_label).strip().lower() == "fixa":
                subcategoria_fixa = st.text_input(
                    "Subcategoria da conta fixa",
                    key="cad_despesa_subcategoria_fixa",
                    placeholder="Ex.: Aluguel, Internet, Energia",
                )
            valor = st.number_input("Valor", min_value=0.0, key="cad_despesa_valor")
            categoria_normalizada = str(categoria_escolhida).strip().lower()
            if categoria_normalizada == "combustível" or categoria_normalizada == "combustivel":
                litros = st.number_input("Litros abastecidos", min_value=0.0, step=0.1, key="cad_despesa_litros")
            else:
                litros = 0.0
                st.number_input("Litros abastecidos", value=0.0, disabled=True, key="cad_despesa_litros_disabled")
            observacao = st.text_input("Observação", key="cad_despesa_obs")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_despesa_confirmar_exclusao")

            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            selected_id = st.session_state.get("cad_despesa_selected_id")
            data_valida = _safe_date_or_none(data)
            categoria_escolhida = str(categoria_escolhida).strip()
            tipo_despesa = {
                "Variável": "VARIAVEL",
                "Recorrente": "RECORRENTE",
                "Fixa": "FIXA",
            }.get(str(tipo_despesa_label), "VARIAVEL")
            esfera_despesa_label = str(st.session_state.get("cad_despesa_esfera", "Negócio"))
            esfera_despesa = {
                "Negócio": "NEGOCIO",
                "Pessoal": "PESSOAL",
            }.get(str(esfera_despesa_label), "NEGOCIO")
            subcategoria_fixa = str(subcategoria_fixa or "").strip()

            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif not categoria_escolhida:
                        st.warning("Informe uma nova categoria ou selecione uma existente.")
                    elif tipo_despesa == "FIXA" and not subcategoria_fixa and not str(observacao).strip():
                        st.warning("Para despesa fixa, informe subcategoria fixa ou observação.")
                    else:
                        service.criar_despesa(
                            data_valida.isoformat(),
                            categoria_escolhida,
                            float(valor),
                            observacao,
                            tipo_despesa=tipo_despesa,
                            subcategoria_fixa=subcategoria_fixa,
                            esfera_despesa=esfera_despesa,
                            litros=float(litros),
                        )
                        st.success("Despesa salva com sucesso.")
                        _reset_fields([
                            "cad_despesa_selected_id", "cad_despesa_last_selected_id", "cad_despesa_data",
                            "cad_despesa_categoria_select", "cad_despesa_valor",
                            "cad_despesa_obs", "cad_despesa_confirmar_exclusao",
                            "cad_despesa_tipo", "cad_despesa_esfera", "cad_despesa_last_esfera", "cad_despesa_subcategoria_fixa", "cad_despesa_litros",
                            "cad_despesa_litros_disabled",
                        ])
                        st.rerun()

                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif not categoria_escolhida:
                        st.warning("Informe uma nova categoria ou selecione uma existente.")
                    elif tipo_despesa == "FIXA" and not subcategoria_fixa and not str(observacao).strip():
                        st.warning("Para despesa fixa, informe subcategoria fixa ou observação.")
                    else:
                        service.atualizar_despesa(
                            int(selected_id),
                            data_valida.isoformat(),
                            categoria_escolhida,
                            float(valor),
                            observacao,
                            tipo_despesa=tipo_despesa,
                            subcategoria_fixa=subcategoria_fixa,
                            esfera_despesa=esfera_despesa,
                            litros=float(litros),
                        )
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
        titulo_secao("Gestão de Investimentos")
        df_investimentos = service.listar_investimentos()
        if "categoria" not in df_investimentos.columns and not df_investimentos.empty:
            df_investimentos["categoria"] = "Renda Fixa"
        if not df_investimentos.empty:
            df_investimentos["aporte"] = pd.to_numeric(df_investimentos.get("aporte"), errors="coerce").fillna(0.0)
            df_investimentos["rendimento"] = pd.to_numeric(df_investimentos.get("rendimento"), errors="coerce").fillna(0.0)
        if not df_investimentos.empty and "id" in df_investimentos.columns:
            df_investimentos = df_investimentos.sort_values(by="id", ascending=False)

        categorias_invest = INVEST_CATEGORIAS.copy()
        for key in ["cad_inv_aporte_categoria", "cad_inv_rend_categoria"]:
            cat = str(st.session_state.get(key, "")).strip()
            if cat and cat not in categorias_invest:
                categorias_invest.append(cat)

        df_aportes = df_investimentos[df_investimentos["aporte"] > 0] if not df_investimentos.empty else pd.DataFrame()
        df_rendimentos = df_investimentos[df_investimentos["aporte"] == 0] if not df_investimentos.empty else pd.DataFrame()
        df_retiradas = df_investimentos[df_investimentos["aporte"] < 0] if not df_investimentos.empty else pd.DataFrame()
        patrimonio_atual = _patrimonio_atual(df_investimentos)

        sub_aportes, sub_rendimentos, sub_retiradas = st.tabs(
            ["Novo Aporte", "Patrimônio e Rendimentos", "Retiradas"]
        )

        with sub_aportes:
            st.caption("Aportes só incrementam patrimônio. Neste formulário o rendimento é sempre zero.")
            options_aporte = [None] + (df_aportes["id"].astype(int).tolist() if "id" in df_aportes.columns else [])
            _ensure_selected_option("cad_inv_aporte_selected_id", options_aporte)
            st.selectbox(
                "Registro de aporte",
                options=options_aporte,
                format_func=lambda x: _investimento_aporte_label(df_aportes, x),
                key="cad_inv_aporte_selected_id",
            )
            _sync_edit_state(df_aportes, "cad_inv_aporte_selected_id", "cad_inv_aporte_last_selected_id", _set_invest_aporte_fields)

            with st.form("cad_invest_aporte_form"):
                data = st.date_input("Data", key="cad_inv_aporte_data")
                categoria = st.selectbox("Categoria", options=categorias_invest, key="cad_inv_aporte_categoria")
                aporte = st.number_input("Valor do aporte", min_value=0.0, key="cad_inv_aporte_valor")
                st.number_input("Rendimento", value=0.0, disabled=True, key="cad_inv_aporte_rendimento_zero")
                selected_aporte_id = st.session_state.get("cad_inv_aporte_selected_id")
                selected_aporte_row = _get_row_by_id(df_aportes, selected_aporte_id)
                aporte_antigo = float(selected_aporte_row["aporte"]) if selected_aporte_row is not None else 0.0
                patrimonio_preview = max(0.0, float(patrimonio_atual) - float(aporte_antigo) + float(aporte))
                st.number_input(
                    "Patrimônio total (automático)",
                    value=float(patrimonio_preview),
                    disabled=True,
                    key="cad_inv_aporte_patrimonio_preview",
                )
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
                                "cad_inv_aporte_selected_id", "cad_inv_aporte_last_selected_id", "cad_inv_aporte_data",
                                "cad_inv_aporte_categoria", "cad_inv_aporte_valor", "cad_inv_aporte_confirmar_exclusao",
                                "cad_inv_aporte_rendimento_zero", "cad_inv_aporte_patrimonio_preview", "cad_inv_aporte_patrimonio",
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
                            st.success("Registro de aporte excluído com sucesso.")
                            _reset_fields(["cad_inv_aporte_selected_id", "cad_inv_aporte_last_selected_id", "cad_inv_aporte_confirmar_exclusao"])
                            st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Erro ao processar aporte: {exc}")

        with sub_rendimentos:
            st.caption("Atualize apenas o rendimento em reais por período. O patrimônio total é calculado automaticamente.")
            categoria_r = str(st.session_state.get("cad_inv_rend_categoria", "Renda Fixa"))
            categorias_r = INVEST_CATEGORIAS.copy()
            if categoria_r not in categorias_r:
                categorias_r.append(categoria_r)
            st.selectbox("Categoria", options=categorias_r, key="cad_inv_rend_categoria")
            categoria_sel = str(st.session_state.get("cad_inv_rend_categoria", "Renda Fixa"))
            df_rend = df_rendimentos[df_rendimentos["categoria"].astype(str) == categoria_sel] if not df_rendimentos.empty else pd.DataFrame()
            options_r = [None] + (df_rend["id"].astype(int).tolist() if "id" in df_rend.columns else [])
            _ensure_selected_option("cad_inv_rend_selected_id", options_r)
            st.selectbox(
                "Registro de patrimônio/rendimento",
                options=options_r,
                format_func=lambda x: _investimento_rendimento_label(df_rend, x),
                key="cad_inv_rend_selected_id",
            )
            _sync_edit_state(df_rend, "cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id", _set_invest_rendimento_fields)

            with st.form("cad_invest_rendimento_form"):
                col_data_ini, col_data_fim = st.columns(2)
                with col_data_ini:
                    data_r_inicio = st.date_input("Data inicial do recorte", key="cad_inv_rend_data_inicio")
                with col_data_fim:
                    data_r_fim = st.date_input("Data final do recorte", key="cad_inv_rend_data_fim")
                st.number_input("Aporte", value=0.0, disabled=True, key="cad_inv_rend_aporte_zero")
                rendimento_r = st.number_input("Rendimento (R$)", value=0.0, step=1.0, key="cad_inv_rend_rendimento")
                selected_rend_id = st.session_state.get("cad_inv_rend_selected_id")
                selected_rend_row = _get_row_by_id(df_rend, selected_rend_id)
                rendimento_antigo = float(selected_rend_row["rendimento"]) if selected_rend_row is not None else 0.0
                patrimonio_preview_r = max(0.0, float(patrimonio_atual) - float(rendimento_antigo) + float(rendimento_r))
                st.number_input(
                    "Patrimônio total (automático)",
                    value=float(patrimonio_preview_r),
                    disabled=True,
                    key="cad_inv_rend_patrimonio_preview",
                )
                confirmar_exclusao_r = st.checkbox("Confirmo a exclusão deste registro", key="cad_inv_rend_confirmar_exclusao")

                col1, col2, col3 = st.columns(3)
                salvar_r = col1.form_submit_button("Salvar (novo)")
                atualizar_r = col2.form_submit_button("Atualizar")
                excluir_r = col3.form_submit_button("Excluir")

                selected_id_r = st.session_state.get("cad_inv_rend_selected_id")
                data_valida_r_inicio = _safe_date_or_none(data_r_inicio)
                data_valida_r_fim = _safe_date_or_none(data_r_fim)
                try:
                    if salvar_r:
                        if data_valida_r_inicio is None or data_valida_r_fim is None:
                            st.warning("Selecione datas válidas para o recorte.")
                        elif data_valida_r_fim < data_valida_r_inicio:
                            st.warning("A data final do recorte deve ser maior ou igual à data inicial.")
                        else:
                            service.criar_investimento(
                                data_valida_r_fim.isoformat(),
                                categoria_sel,
                                0.0,
                                0.0,
                                float(rendimento_r),
                                float(patrimonio_preview_r),
                                data_inicio=data_valida_r_inicio.isoformat(),
                                data_fim=data_valida_r_fim.isoformat(),
                                tipo_movimentacao="RENDIMENTO",
                            )
                            st.success("Registro de patrimônio/rendimento salvo com sucesso.")
                            _reset_fields([
                                "cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id",
                                "cad_inv_rend_data_inicio", "cad_inv_rend_data_fim",
                                "cad_inv_rend_rendimento", "cad_inv_rend_confirmar_exclusao",
                                "cad_inv_rend_aporte_zero", "cad_inv_rend_patrimonio_preview",
                                "cad_inv_rend_categoria", "cad_inv_rend_patrimonio",
                            ])
                            st.rerun()

                    if atualizar_r:
                        if selected_id_r is None:
                            st.warning("Selecione um registro para atualizar.")
                        elif data_valida_r_inicio is None or data_valida_r_fim is None:
                            st.warning("Selecione datas válidas para o recorte.")
                        elif data_valida_r_fim < data_valida_r_inicio:
                            st.warning("A data final do recorte deve ser maior ou igual à data inicial.")
                        else:
                            service.atualizar_investimento(
                                int(selected_id_r),
                                data_valida_r_fim.isoformat(),
                                categoria_sel,
                                0.0,
                                0.0,
                                float(rendimento_r),
                                float(patrimonio_preview_r),
                                data_inicio=data_valida_r_inicio.isoformat(),
                                data_fim=data_valida_r_fim.isoformat(),
                                tipo_movimentacao="RENDIMENTO",
                            )
                            st.success("Registro de patrimônio/rendimento atualizado com sucesso.")
                            st.rerun()

                    if excluir_r:
                        if selected_id_r is None:
                            st.warning("Selecione um registro para excluir.")
                        elif not confirmar_exclusao_r:
                            st.warning("Confirme a exclusão para continuar.")
                        else:
                            service.deletar_investimento(int(selected_id_r))
                            st.success("Registro de patrimônio/rendimento excluído com sucesso.")
                            _reset_fields([
                                "cad_inv_rend_selected_id", "cad_inv_rend_last_selected_id", "cad_inv_rend_confirmar_exclusao"
                            ])
                            st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Erro ao processar patrimônio/rendimento: {exc}")

        with sub_retiradas:
            st.caption("Retiradas reduzem patrimônio. Informe apenas o valor da retirada; o patrimônio é atualizado automaticamente.")
            categoria_ret = str(st.session_state.get("cad_inv_ret_categoria", "Renda Fixa"))
            categorias_ret = INVEST_CATEGORIAS.copy()
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
            _sync_edit_state(
                df_retiradas,
                "cad_inv_ret_selected_id",
                "cad_inv_ret_last_selected_id",
                _set_invest_retirada_fields,
            )

            with st.form("cad_invest_retirada_form"):
                data_ret = st.date_input("Data da retirada", key="cad_inv_ret_data")
                categoria_ret_sel = st.selectbox("Categoria", options=categorias_ret, key="cad_inv_ret_categoria")
                retirada = st.number_input("Valor da retirada", min_value=0.0, key="cad_inv_ret_valor")
                st.number_input("Rendimento", value=0.0, disabled=True, key="cad_inv_ret_rendimento_zero")

                selected_ret_id = st.session_state.get("cad_inv_ret_selected_id")
                selected_ret_row = _get_row_by_id(df_retiradas, selected_ret_id)
                retirada_antiga = abs(float(selected_ret_row["aporte"])) if selected_ret_row is not None else 0.0
                patrimonio_disponivel = float(patrimonio_atual) + float(retirada_antiga)
                patrimonio_preview_ret = max(0.0, patrimonio_disponivel - float(retirada))
                st.number_input(
                    "Patrimônio total (automático)",
                    value=float(patrimonio_preview_ret),
                    disabled=True,
                    key="cad_inv_ret_patrimonio_preview",
                )
                confirmar_exclusao_ret = st.checkbox("Confirmo a exclusão deste registro", key="cad_inv_ret_confirmar_exclusao")

                col1, col2, col3 = st.columns(3)
                salvar_ret = col1.form_submit_button("Salvar (novo)")
                atualizar_ret = col2.form_submit_button("Atualizar")
                excluir_ret = col3.form_submit_button("Excluir")

                data_valida_ret = _safe_date_or_none(data_ret)
                try:
                    if salvar_ret:
                        if data_valida_ret is None:
                            st.warning("Selecione uma data válida.")
                        elif float(retirada) > float(patrimonio_disponivel):
                            st.warning("Retirada maior que o patrimônio disponível.")
                        else:
                            service.criar_investimento(
                                data_valida_ret.isoformat(),
                                categoria_ret_sel,
                                float(-retirada),
                                0.0,
                                0.0,
                                float(patrimonio_preview_ret),
                                data_inicio=data_valida_ret.isoformat(),
                                data_fim=data_valida_ret.isoformat(),
                                tipo_movimentacao="RETIRADA",
                            )
                            st.success("Retirada salva com sucesso.")
                            _reset_fields([
                                "cad_inv_ret_selected_id", "cad_inv_ret_last_selected_id",
                                "cad_inv_ret_data", "cad_inv_ret_valor", "cad_inv_ret_categoria",
                                "cad_inv_ret_confirmar_exclusao", "cad_inv_ret_rendimento_zero", "cad_inv_ret_patrimonio_preview",
                                "cad_inv_ret_patrimonio",
                            ])
                            st.rerun()

                    if atualizar_ret:
                        if selected_ret_id is None:
                            st.warning("Selecione um registro para atualizar.")
                        elif data_valida_ret is None:
                            st.warning("Selecione uma data válida.")
                        elif float(retirada) > float(patrimonio_disponivel):
                            st.warning("Retirada maior que o patrimônio disponível.")
                        else:
                            service.atualizar_investimento(
                                int(selected_ret_id),
                                data_valida_ret.isoformat(),
                                categoria_ret_sel,
                                float(-retirada),
                                0.0,
                                0.0,
                                float(patrimonio_preview_ret),
                                data_inicio=data_valida_ret.isoformat(),
                                data_fim=data_valida_ret.isoformat(),
                                tipo_movimentacao="RETIRADA",
                            )
                            st.success("Retirada atualizada com sucesso.")
                            st.rerun()

                    if excluir_ret:
                        if selected_ret_id is None:
                            st.warning("Selecione um registro para excluir.")
                        elif not confirmar_exclusao_ret:
                            st.warning("Confirme a exclusão para continuar.")
                        else:
                            service.deletar_investimento(int(selected_ret_id))
                            st.success("Registro de retirada excluído com sucesso.")
                            _reset_fields(["cad_inv_ret_selected_id", "cad_inv_ret_last_selected_id", "cad_inv_ret_confirmar_exclusao"])
                            st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Erro ao processar retirada: {exc}")
