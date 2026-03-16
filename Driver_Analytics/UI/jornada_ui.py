"""Jornada de trabalho UI page."""

from __future__ import annotations

from datetime import date, time

import pandas as pd
import streamlit as st

from UI.components import render_kpi, show_empty_data, titulo_secao
from services.work_day_service import WorkDayService


service = WorkDayService()
STATUS_LABELS = {
    "open": "Em andamento",
    "closed": "Fechada",
    "partial": "Incompleta",
    "adjusted": "Ajustada",
    "manual": "Manual",
}
EVENT_LABELS = {
    "check_in": "Check-in",
    "check_out": "Check-out",
    "manual_create": "Criação manual",
    "manual_edit": "Edição manual",
    "manual_complete": "Complemento manual",
}
WORK_DAY_MIGRATION_FILE = "sql/migrations/20260316130000__add_work_days_module.sql"


def _safe_dt(value):
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed


def _date_value(value):
    parsed = _safe_dt(value)
    return parsed.date() if parsed is not None else date.today()


def _time_value(value):
    parsed = _safe_dt(value)
    return parsed.time().replace(microsecond=0) if parsed is not None else time(0, 0, 0)


def _format_minutes(value) -> str:
    try:
        total = int(value)
    except Exception:
        return "-"
    horas = total // 60
    minutos = total % 60
    return f"{horas:02d}h {minutos:02d}m"


def _format_dt(value) -> str:
    parsed = _safe_dt(value)
    return parsed.strftime("%d/%m/%Y %H:%M") if parsed is not None else "-"


def _format_km(value) -> str:
    try:
        return f"{float(value):,.1f} km"
    except Exception:
        return "-"


def _status_label(value: str) -> str:
    return STATUS_LABELS.get(str(value or "").strip().lower(), str(value or "-"))


def _bool_default(row: dict, key: str) -> bool:
    return row.get(key) not in (None, "", [])


def _combine_date_time(enabled: bool, input_date: date, input_time: time) -> str | None:
    if not enabled:
        return None
    return f"{input_date.isoformat()}T{input_time.isoformat()}"


def _event_summary(value) -> str:
    if not isinstance(value, dict) or not value:
        return "-"
    keys = ["status", "start_km", "end_km", "start_time", "end_time", "worked_minutes_final"]
    parts: list[str] = []
    for key in keys:
        if key not in value:
            continue
        raw = value.get(key)
        if key in {"start_time", "end_time"}:
            formatted = _format_dt(raw)
        elif key in {"start_km", "end_km"}:
            formatted = _format_km(raw)
        elif key == "worked_minutes_final":
            formatted = _format_minutes(raw)
        elif key == "status":
            formatted = _status_label(str(raw))
        else:
            formatted = str(raw)
        parts.append(f"{key}: {formatted}")
    return " | ".join(parts) if parts else "-"


def _work_day_bootstrap_message(exc: Exception) -> str:
    message = str(exc or "")
    if "work_days" in message or "work_day_events" in message:
        return (
            "O modulo Jornada ainda nao esta disponivel neste ambiente. "
            f"Aplique a migration `{WORK_DAY_MIGRATION_FILE}` no projeto Supabase usado pelo deploy e reinicie o app."
        )
    return f"Falha ao carregar Jornada: {message}"


def _render_legacy_backfill() -> None:
    titulo_secao("Migracao Historica")
    with st.expander("Migrar jornadas legadas a partir de receitas", expanded=False):
        st.caption(
            "Backfill seguro: agrupa receitas por data, simula inicio as 16:00, "
            "encerra com base no tempo trabalhado registrado e soma o KM remunerado do dia."
        )
        with st.form("work_day_legacy_backfill_form"):
            start_hour = st.number_input("Hora inicial simulada", min_value=0, max_value=23, value=16, step=1, key="wd_backfill_start_hour")
            overwrite = st.checkbox("Sobrescrever jornadas ja existentes nas mesmas datas", key="wd_backfill_overwrite")
            confirm = st.checkbox("Confirmo que desejo migrar jornadas historicas com simulacao de horario/KM", key="wd_backfill_confirm")
            submit = st.form_submit_button("Executar migracao historica")
            if submit:
                if not confirm:
                    st.warning("Confirme a migracao para continuar.")
                else:
                    try:
                        resultado = service.migrar_receitas_legadas(
                            simulated_start_hour=int(start_hour),
                            overwrite_existing=bool(overwrite),
                        )
                        st.success("Migracao historica concluida.")
                        cols = st.columns(3)
                        with cols[0]:
                            render_kpi("Dias migrados", int(resultado["migrated_days"]))
                        with cols[1]:
                            render_kpi("KM remunerado total", _format_km(resultado["total_km_remunerado"]))
                        with cols[2]:
                            render_kpi("Media KM/dia", _format_km(resultado["media_km_remunerado"]))
                        st.caption(
                            "Periodo migrado: "
                            f"{resultado['first_date'] or '-'} ate {resultado['last_date'] or '-'} | "
                            f"Dias ignorados: {int(resultado['skipped_days'])} | "
                            f"Tempo total: {_format_minutes(resultado['total_minutes'])}"
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))


def _render_current_status(jornadas: list[dict]) -> dict | None:
    titulo_secao("Status Atual")
    aberta = next((row for row in jornadas if row.get("status") == "open"), None)
    parcial = next((row for row in jornadas if row.get("status") == "partial"), None)
    cols = st.columns(4)
    if aberta:
        with cols[0]:
            render_kpi("Status", "Em andamento")
        with cols[1]:
            render_kpi("Início", _format_dt(aberta.get("start_time")))
        with cols[2]:
            render_kpi("KM inicial", _format_km(aberta.get("start_km")))
        with cols[3]:
            render_kpi("Observação", aberta.get("notes") or "-")
        return aberta
    if parcial:
        with cols[0]:
            render_kpi("Status", "Jornada incompleta")
        with cols[1]:
            render_kpi("Data", str(parcial.get("work_date") or "-"))
        with cols[2]:
            render_kpi("Início", _format_dt(parcial.get("start_time")))
        with cols[3]:
            render_kpi("KM inicial", _format_km(parcial.get("start_km")))
        st.warning("Existe uma jornada incompleta. Use a seção de complemento/edição para concluir ou corrigir o registro.")
        return parcial
    else:
        with cols[0]:
            render_kpi("Status", "Sem jornada aberta")
        with cols[1]:
            render_kpi("Hoje", date.today().isoformat())
        with cols[2]:
            render_kpi("Jornadas incompletas", sum(1 for row in jornadas if row.get("status") == "partial"))
    return None


def _render_auto_flow(open_day: dict | None) -> None:
    titulo_secao("Check-in / Check-out")
    col_start, col_end = st.columns(2)
    with col_start:
        with st.form("work_day_check_in_form"):
            st.caption("Início automático: o sistema registra a data/hora atual e você informa só o KM inicial.")
            start_km = st.number_input("KM inicial", min_value=0.0, step=0.1, key="wd_start_km")
            notes = st.text_area("Observações", key="wd_start_notes")
            submit = st.form_submit_button("Iniciar jornada", disabled=open_day is not None)
            if submit:
                try:
                    service.iniciar_jornada(start_km=start_km, notes=notes)
                    st.success("Jornada iniciada.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    with col_end:
        with st.form("work_day_check_out_form"):
            st.caption("Encerramento automático: o sistema registra a data/hora atual e você informa só o KM final.")
            end_km = st.number_input("KM final", min_value=0.0, step=0.1, key="wd_end_km")
            notes = st.text_area("Observações finais", key="wd_end_notes")
            submit = st.form_submit_button("Encerrar jornada", disabled=open_day is None)
            if submit:
                try:
                    service.encerrar_jornada(end_km=end_km, notes=notes)
                    st.success("Jornada encerrada.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def _render_manual_create() -> None:
    titulo_secao("Criação Manual Excepcional")
    with st.expander("Criar jornada manual completa/incompleta", expanded=False):
        with st.form("work_day_manual_create_form"):
            work_date = st.date_input("Data da jornada", key="wd_manual_date")
            st.caption("Ative apenas os campos que realmente existem para este registro manual.")
            include_start = st.checkbox("Informar início manual", value=True, key="wd_manual_has_start")
            include_end = st.checkbox("Informar término manual", value=False, key="wd_manual_has_end")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Data de início",
                    value=work_date,
                    key="wd_manual_start_date",
                    disabled=not include_start,
                )
                start_clock = st.time_input("Hora de início", key="wd_manual_start_time", disabled=not include_start)
            with col2:
                end_date = st.date_input(
                    "Data de término",
                    value=work_date,
                    key="wd_manual_end_date",
                    disabled=not include_end,
                )
                end_clock = st.time_input("Hora de término", key="wd_manual_end_time", disabled=not include_end)
            include_start_km = st.checkbox("Informar KM inicial", value=True, key="wd_manual_has_start_km")
            start_km = st.number_input(
                "KM inicial manual",
                min_value=0.0,
                step=0.1,
                key="wd_manual_start_km",
                disabled=not include_start_km,
            )
            include_end_km = st.checkbox("Informar KM final", value=False, key="wd_manual_has_end_km")
            end_km = st.number_input(
                "KM final manual",
                min_value=0.0,
                step=0.1,
                key="wd_manual_end_km",
                disabled=not include_end_km,
            )
            worked_manual = st.number_input("Tempo manual (minutos)", min_value=0, step=1, key="wd_manual_minutes")
            notes = st.text_area("Observações", key="wd_manual_notes")
            allow_override = st.checkbox("Permitir ajuste manual excepcional", key="wd_manual_override")
            submit = st.form_submit_button("Salvar jornada manual")
            if submit:
                try:
                    start_time_value = _combine_date_time(include_start, start_date, start_clock)
                    end_time_value = _combine_date_time(include_end, end_date, end_clock)
                    service.criar_jornada_manual(
                        work_date=work_date.isoformat(),
                        start_time=start_time_value,
                        end_time=end_time_value,
                        start_km=start_km if include_start_km else None,
                        end_km=end_km if include_end_km else None,
                        worked_minutes_manual=worked_manual if worked_manual > 0 else None,
                        notes=notes,
                        allow_manual_override=allow_override,
                    )
                    st.success("Jornada manual registrada.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def _render_manual_edit(jornadas: list[dict]) -> None:
    titulo_secao("Complemento / Edição")
    if not jornadas:
        show_empty_data("Nenhuma jornada para editar.")
        return
    options = [row["id"] for row in jornadas]
    selected_id = st.selectbox("Selecione a jornada", options=options, key="wd_edit_selected_id")
    detail = service.detalhar_jornada(int(selected_id))
    row = detail["work_day"]

    with st.form("work_day_manual_edit_form"):
        work_date = st.date_input("Data", value=_date_value(row.get("work_date")), key="wd_edit_date")
        has_start = st.checkbox("Manter horário inicial", value=_bool_default(row, "start_time"), key="wd_edit_has_start")
        has_end = st.checkbox("Manter horário final", value=_bool_default(row, "end_time"), key="wd_edit_has_end")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Data de início",
                value=_date_value(row.get("start_time") or row.get("work_date")),
                key="wd_edit_start_date",
                disabled=not has_start,
            )
            start_clock = st.time_input(
                "Hora de início",
                value=_time_value(row.get("start_time")),
                key="wd_edit_start_time",
                disabled=not has_start,
            )
        with col2:
            end_date = st.date_input(
                "Data de término",
                value=_date_value(row.get("end_time") or row.get("work_date")),
                key="wd_edit_end_date",
                disabled=not has_end,
            )
            end_clock = st.time_input(
                "Hora de término",
                value=_time_value(row.get("end_time")),
                key="wd_edit_end_time",
                disabled=not has_end,
            )
        has_start_km = st.checkbox("Manter KM inicial", value=_bool_default(row, "start_km"), key="wd_edit_has_start_km")
        start_km = st.number_input(
            "KM inicial",
            min_value=0.0,
            step=0.1,
            value=float(row.get("start_km") or 0.0),
            key="wd_edit_start_km",
            disabled=not has_start_km,
        )
        has_end_km = st.checkbox("Manter KM final", value=_bool_default(row, "end_km"), key="wd_edit_has_end_km")
        end_km = st.number_input(
            "KM final",
            min_value=0.0,
            step=0.1,
            value=float(row.get("end_km") or 0.0),
            key="wd_edit_end_km",
            disabled=not has_end_km,
        )
        worked_manual = st.number_input(
            "Tempo manual (minutos)",
            min_value=0,
            step=1,
            value=int(row.get("worked_minutes_manual") or 0),
            key="wd_edit_minutes",
        )
        notes = st.text_area("Observações", value=str(row.get("notes") or ""), key="wd_edit_notes")
        allow_override = st.checkbox("Permitir ajuste manual excepcional", key="wd_edit_override")
        action = st.radio("Ação", ["Completar", "Editar"], horizontal=True, key="wd_edit_action")
        submit = st.form_submit_button("Salvar alteração")
        if submit:
            try:
                start_time_value = _combine_date_time(has_start, start_date, start_clock)
                end_time_value = _combine_date_time(has_end, end_date, end_clock)
                payload = {
                    "work_date": work_date.isoformat(),
                    "start_time": start_time_value,
                    "end_time": end_time_value,
                    "start_km": start_km if has_start_km else None,
                    "end_km": end_km if has_end_km else None,
                    "worked_minutes_manual": worked_manual if worked_manual > 0 else None,
                    "notes": notes,
                }
                if action == "Completar":
                    service.completar_jornada(
                        int(selected_id),
                        start_time=payload["start_time"],
                        end_time=payload["end_time"],
                        start_km=payload["start_km"],
                        end_km=payload["end_km"],
                        worked_minutes_manual=payload["worked_minutes_manual"],
                        notes=payload["notes"],
                        allow_manual_override=allow_override,
                    )
                else:
                    service.editar_jornada(int(selected_id), payload, allow_manual_override=allow_override, notes=notes)
                st.success("Jornada atualizada.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    titulo_secao("Eventos da Jornada")
    events = detail["events"]
    if not events:
        show_empty_data("Sem eventos registrados.")
    else:
        events_df = pd.DataFrame(events)
        if "event_type" in events_df.columns:
            events_df["event_type"] = events_df["event_type"].map(EVENT_LABELS).fillna(events_df["event_type"])
        if "event_timestamp" in events_df.columns:
            events_df["event_timestamp"] = events_df["event_timestamp"].apply(_format_dt)
        if "km_value" in events_df.columns:
            events_df["km_value"] = events_df["km_value"].apply(_format_km)
        if "old_value" in events_df.columns:
            events_df["old_value"] = events_df["old_value"].apply(_event_summary)
        if "new_value" in events_df.columns:
            events_df["new_value"] = events_df["new_value"].apply(_event_summary)
        columns = [col for col in ["event_type", "event_timestamp", "km_value", "old_value", "new_value", "notes"] if col in events_df.columns]
        st.dataframe(events_df[columns], width="stretch", hide_index=True)


def _render_history(jornadas: list[dict]) -> None:
    titulo_secao("Histórico")
    if not jornadas:
        show_empty_data("Nenhuma jornada registrada.")
        return
    df = pd.DataFrame(jornadas)
    if "status" in df.columns:
        df["status"] = df["status"].map(STATUS_LABELS).fillna(df["status"])
    for col in ("start_time", "end_time", "created_at", "updated_at"):
        if col in df.columns:
            df[col] = df[col].apply(_format_dt)
    if "worked_minutes_final" in df.columns:
        df["worked_minutes_final"] = df["worked_minutes_final"].apply(_format_minutes)
    for col in ("start_km", "end_km", "km_remunerado", "km_nao_remunerado_antes"):
        if col in df.columns:
            df[col] = df[col].apply(_format_km)
    preferred = [
        "work_date",
        "status",
        "start_time",
        "end_time",
        "start_km",
        "end_km",
        "km_remunerado",
        "km_nao_remunerado_antes",
        "worked_minutes_final",
        "notes",
        "updated_at",
    ]
    columns = [col for col in preferred if col in df.columns]
    st.dataframe(df[columns], width="stretch", hide_index=True)


def pagina_jornada() -> None:
    st.header("Jornada")
    try:
        jornadas = service.listar_jornadas()
    except Exception as exc:
        st.error(_work_day_bootstrap_message(exc))
        st.stop()
    aberta = _render_current_status(jornadas)

    if jornadas:
        total_km_rem = sum(float(row.get("km_remunerado") or 0.0) for row in jornadas)
        total_km_nao_rem = sum(float(row.get("km_nao_remunerado_antes") or 0.0) for row in jornadas)
        total_minutes = sum(int(row.get("worked_minutes_final") or 0) for row in jornadas)
        cols = st.columns(3)
        with cols[0]:
            render_kpi("KM remunerado", _format_km(total_km_rem))
        with cols[1]:
            render_kpi("KM não remunerado", _format_km(total_km_nao_rem))
        with cols[2]:
            render_kpi("Tempo final", _format_minutes(total_minutes))

    _render_auto_flow(aberta)
    _render_legacy_backfill()
    _render_manual_create()
    _render_manual_edit(jornadas)
    _render_history(jornadas)
