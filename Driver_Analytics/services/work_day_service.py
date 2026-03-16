"""Business rules for work day check-in/check-out and manual adjustments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from domain.models import WorkDay, WorkDayEvent
from repositories.receitas_repository import ReceitasRepository
from repositories.work_day_events_repository import WorkDayEventsRepository
from repositories.work_days_repository import WorkDaysRepository


class WorkDayService:
    """Service layer for jornada de trabalho."""

    VALID_STATUSES = {"open", "closed", "partial", "adjusted", "manual"}

    def __init__(self) -> None:
        self.work_days_repo = WorkDaysRepository()
        self.events_repo = WorkDayEventsRepository()
        self.receitas_repo = ReceitasRepository()

    @staticmethod
    def _app_tz() -> ZoneInfo:
        return ZoneInfo("America/Sao_Paulo")

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()

    @staticmethod
    def _to_date_str(value: Any) -> str:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return ""
        return parsed.date().isoformat()

    @staticmethod
    def _to_iso_timestamp(value: Any) -> str:
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed):
            return ""
        return parsed.to_pydatetime().isoformat()

    def _build_legacy_day_timestamps(self, work_date: str, worked_seconds: int, start_hour: int = 16) -> tuple[str, str]:
        start_local = datetime.fromisoformat(f"{work_date}T{int(start_hour):02d}:00:00").replace(tzinfo=self._app_tz())
        end_local = start_local + pd.Timedelta(seconds=int(max(0, worked_seconds)))
        return start_local.astimezone(timezone.utc).isoformat(), end_local.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _clean_text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _to_int_or_none(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        try:
            return int(value)
        except Exception:
            return None

    def _serialize_day(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            "id": int(row.get("id", 0)),
            "work_date": self._to_date_str(row.get("work_date")),
            "start_time": self._to_iso_timestamp(row.get("start_time")),
            "end_time": self._to_iso_timestamp(row.get("end_time")),
            "start_time_source": self._clean_text(row.get("start_time_source", "auto")).lower() or "auto",
            "end_time_source": self._clean_text(row.get("end_time_source", "auto")).lower() or "auto",
            "start_km": self._to_float_or_none(row.get("start_km")),
            "end_km": self._to_float_or_none(row.get("end_km")),
            "km_remunerado": self._to_float_or_none(row.get("km_remunerado")),
            "km_nao_remunerado_antes": self._to_float_or_none(row.get("km_nao_remunerado_antes")),
            "worked_minutes_calculated": self._to_int_or_none(row.get("worked_minutes_calculated")),
            "worked_minutes_manual": self._to_int_or_none(row.get("worked_minutes_manual")),
            "worked_minutes_final": self._to_int_or_none(row.get("worked_minutes_final")),
            "status": self._clean_text(row.get("status", "partial")).lower() or "partial",
            "is_manually_adjusted": bool(row.get("is_manually_adjusted", False)),
            "notes": self._clean_text(row.get("notes", "")),
            "created_at": self._to_iso_timestamp(row.get("created_at")),
            "updated_at": self._to_iso_timestamp(row.get("updated_at")),
        }

    def _serialize_events(self, df: pd.DataFrame) -> list[dict]:
        if df.empty:
            return []
        work = df.copy()
        if "event_timestamp" in work.columns:
            work["event_timestamp"] = pd.to_datetime(work["event_timestamp"], errors="coerce", utc=True)
            work["event_timestamp"] = work["event_timestamp"].apply(lambda v: v.isoformat() if pd.notna(v) else "")
        if "created_at" in work.columns:
            work["created_at"] = pd.to_datetime(work["created_at"], errors="coerce", utc=True)
            work["created_at"] = work["created_at"].apply(lambda v: v.isoformat() if pd.notna(v) else "")
        for col in ("km_value",):
            if col in work.columns:
                work[col] = pd.to_numeric(work[col], errors="coerce")
        return work.to_dict(orient="records")

    def _validate_time_order(self, start_time: str | None, end_time: str | None, allow_override: bool = False) -> None:
        start_dt = self._to_datetime(start_time)
        end_dt = self._to_datetime(end_time)
        if start_dt and end_dt and end_dt < start_dt and not allow_override:
            raise ValueError("Horário final não pode ser anterior ao inicial.")

    def _validate_km_order(self, start_km: float | None, end_km: float | None, allow_override: bool = False) -> None:
        if start_km is not None and end_km is not None and end_km < start_km and not allow_override:
            raise ValueError("KM final não pode ser menor que o KM inicial.")

    def _validate_start_km_against_previous(
        self,
        work_date: str,
        start_km: float | None,
        current_id: int | None = None,
        allow_override: bool = False,
    ) -> None:
        if start_km is None:
            return
        previous = self.work_days_repo.buscar_ultima_fechada_antes(work_date, current_id=current_id)
        previous_end_km = self._to_float_or_none((previous or {}).get("end_km"))
        if previous_end_km is not None and start_km < previous_end_km and not allow_override:
            raise ValueError("KM inicial não pode ser menor que o KM final da jornada anterior fechada.")

    def _status_for_row(self, row: dict[str, Any]) -> str:
        has_start_time = bool(self._clean_text(row.get("start_time")))
        has_end_time = bool(self._clean_text(row.get("end_time")))
        has_start_km = self._to_float_or_none(row.get("start_km")) is not None
        has_end_km = self._to_float_or_none(row.get("end_km")) is not None
        complete = has_start_time and has_end_time and has_start_km and has_end_km
        if complete:
            if bool(row.get("is_manually_adjusted", False)):
                return "adjusted"
            if (
                self._clean_text(row.get("start_time_source", "auto")).lower() == "manual"
                and self._clean_text(row.get("end_time_source", "auto")).lower() == "manual"
            ):
                return "manual"
            return "closed"
        if has_start_time and not has_end_time:
            return "open"
        return "partial"

    def _write_event(
        self,
        work_day_id: int,
        event_type: str,
        km_value: float | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        notes: str = "",
    ) -> None:
        event = WorkDayEvent.from_raw(
            {
                "work_day_id": int(work_day_id),
                "event_type": event_type,
                "event_timestamp": self._utc_now().isoformat(),
                "km_value": km_value,
                "old_value": old_value or None,
                "new_value": new_value or None,
                "notes": notes,
            }
        )
        self.events_repo.inserir(event.to_record())

    def _recalculate_all(self) -> None:
        rows = [self._serialize_day(row) for row in self.work_days_repo.listar_raw()]
        rows = [row for row in rows if row]
        if not rows:
            return
        rows.sort(key=lambda row: (row["work_date"], row.get("start_time") or "", row.get("created_at") or "", row["id"]))
        previous_closed_end_km: float | None = None
        for row in rows:
            start_time = row.get("start_time")
            end_time = row.get("end_time")
            start_km = self._to_float_or_none(row.get("start_km"))
            end_km = self._to_float_or_none(row.get("end_km"))

            worked_calculated = None
            start_dt = self._to_datetime(start_time)
            end_dt = self._to_datetime(end_time)
            if start_dt and end_dt and end_dt >= start_dt:
                worked_calculated = int((end_dt - start_dt).total_seconds() // 60)

            worked_manual = self._to_int_or_none(row.get("worked_minutes_manual"))
            worked_final = worked_manual if worked_manual is not None else worked_calculated
            km_remunerado = (end_km - start_km) if start_km is not None and end_km is not None else None
            km_gap = (start_km - previous_closed_end_km) if start_km is not None and previous_closed_end_km is not None else None

            current = dict(row)
            current["worked_minutes_calculated"] = worked_calculated
            current["worked_minutes_final"] = worked_final
            current["km_remunerado"] = km_remunerado
            current["km_nao_remunerado_antes"] = km_gap
            current["status"] = self._status_for_row(current)

            payload = {
                "worked_minutes_calculated": worked_calculated,
                "worked_minutes_final": worked_final,
                "km_remunerado": km_remunerado,
                "km_nao_remunerado_antes": km_gap,
                "status": current["status"],
            }
            self.work_days_repo.atualizar(int(row["id"]), payload)

            if current["status"] in {"closed", "adjusted", "manual"} and end_km is not None:
                previous_closed_end_km = end_km

    def listar_jornadas(self) -> list[dict]:
        rows = [self._serialize_day(row) for row in self.work_days_repo.listar_raw()]
        rows = [row for row in rows if row]
        rows.sort(key=lambda row: (row["work_date"], row.get("start_time") or "", row["id"]), reverse=True)
        return rows

    def detalhar_jornada(self, work_day_id: int) -> dict:
        row = self._serialize_day(self.work_days_repo.buscar_por_id(int(work_day_id)))
        if not row:
            raise ValueError("Jornada não encontrada.")
        events = self._serialize_events(self.events_repo.listar_por_work_day(int(work_day_id)))
        return {"work_day": row, "events": events}

    def migrar_receitas_legadas(
        self,
        *,
        simulated_start_hour: int = 16,
        include_until_today: bool = True,
        overwrite_existing: bool = False,
    ) -> dict[str, Any]:
        """Backfill work_days from legacy receitas grouped by day."""

        receitas = self.receitas_repo.listar()
        if receitas.empty or "data" not in receitas.columns:
            return {
                "migrated_days": 0,
                "skipped_days": 0,
                "first_date": "",
                "last_date": "",
                "total_km_remunerado": 0.0,
                "media_km_remunerado": 0.0,
                "total_minutes": 0,
            }

        work = receitas.copy()
        work["data"] = pd.to_datetime(work["data"], errors="coerce")
        work = work.dropna(subset=["data"])
        if work.empty:
            return {
                "migrated_days": 0,
                "skipped_days": 0,
                "first_date": "",
                "last_date": "",
                "total_km_remunerado": 0.0,
                "media_km_remunerado": 0.0,
                "total_minutes": 0,
            }

        if "km" not in work.columns:
            work["km"] = 0.0
        if "tempo trabalhado" not in work.columns:
            work["tempo trabalhado"] = 0
        work["km"] = pd.to_numeric(work["km"], errors="coerce").fillna(0.0)
        work["tempo trabalhado"] = pd.to_numeric(work["tempo trabalhado"], errors="coerce").fillna(0).astype(int)
        work["work_date"] = work["data"].dt.date.astype(str)

        if include_until_today:
            today = pd.Timestamp.now(tz=self._app_tz()).date().isoformat()
            work = work[work["work_date"] <= today]

        aggregated = (
            work.groupby("work_date", as_index=False)
            .agg(
                km_remunerado=("km", "sum"),
                worked_seconds=("tempo trabalhado", "sum"),
                total_valor=("valor", "sum") if "valor" in work.columns else ("km", "sum"),
                receitas_count=("work_date", "count"),
            )
            .sort_values("work_date")
        )
        if aggregated.empty:
            return {
                "migrated_days": 0,
                "skipped_days": 0,
                "first_date": "",
                "last_date": "",
                "total_km_remunerado": 0.0,
                "media_km_remunerado": 0.0,
                "total_minutes": 0,
            }

        existing_rows = [self._serialize_day(row) for row in self.work_days_repo.listar_raw()]
        existing_rows = [row for row in existing_rows if row]
        existing_by_date = {str(row["work_date"]): row for row in existing_rows}
        simulated_km_cursor = 0.0
        if existing_rows:
            end_values = [self._to_float_or_none(row.get("end_km")) for row in existing_rows]
            end_values = [value for value in end_values if value is not None]
            if end_values:
                simulated_km_cursor = float(max(end_values))

        migrated_days = 0
        skipped_days = 0
        total_km = 0.0
        total_minutes = 0
        first_date = str(aggregated.iloc[0]["work_date"])
        last_date = str(aggregated.iloc[-1]["work_date"])

        for row in aggregated.to_dict(orient="records"):
            work_date = str(row["work_date"])
            km_remunerado = float(row.get("km_remunerado") or 0.0)
            worked_seconds = int(row.get("worked_seconds") or 0)
            worked_minutes = int(max(0, worked_seconds) // 60)
            start_time, end_time = self._build_legacy_day_timestamps(work_date, worked_seconds, start_hour=simulated_start_hour)
            start_km = float(simulated_km_cursor)
            end_km = float(start_km + km_remunerado)

            payload = WorkDay.from_raw(
                {
                    "work_date": work_date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "start_time_source": "manual",
                    "end_time_source": "manual",
                    "start_km": start_km,
                    "end_km": end_km,
                    "notes": (
                        "Backfill legado de receitas: inicio simulado as "
                        f"{int(simulated_start_hour):02d}:00, KM remunerado agregado do dia e "
                        "hodometro cumulativo sintetico."
                    ),
                }
            ).to_record()

            existing = existing_by_date.get(work_date)
            if existing and not overwrite_existing:
                skipped_days += 1
                simulated_km_cursor = max(simulated_km_cursor, self._to_float_or_none(existing.get("end_km")) or end_km)
                continue

            old_value = existing if existing else None
            if existing and overwrite_existing:
                payload["is_manually_adjusted"] = True
                self.work_days_repo.atualizar(int(existing["id"]), payload)
                work_day_id = int(existing["id"])
            else:
                created = self.work_days_repo.inserir(payload)
                work_day_id = int(created.get("id", 0))

            self._recalculate_all()
            refreshed = self._serialize_day(self.work_days_repo.buscar_por_id(work_day_id))
            self._write_event(
                work_day_id,
                "manual_create" if old_value is None else "manual_edit",
                km_value=km_remunerado,
                old_value=old_value,
                new_value=refreshed,
                notes=(
                    "Migracao historica automatica baseada em receitas agregadas do dia; "
                    f"tempo_total={worked_minutes}min, km_remunerado={km_remunerado:.1f}."
                ),
            )
            migrated_days += 1
            total_km += km_remunerado
            total_minutes += worked_minutes
            simulated_km_cursor = end_km

        media_km = float(total_km / migrated_days) if migrated_days > 0 else 0.0
        return {
            "migrated_days": int(migrated_days),
            "skipped_days": int(skipped_days),
            "first_date": first_date,
            "last_date": last_date,
            "total_km_remunerado": float(total_km),
            "media_km_remunerado": media_km,
            "total_minutes": int(total_minutes),
        }

    def iniciar_jornada(self, start_km: float, notes: str = "") -> dict:
        open_day = self.work_days_repo.buscar_aberta()
        if open_day:
            raise ValueError("Já existe uma jornada aberta para este usuário.")

        now = self._utc_now()
        work_date = now.date().isoformat()
        start_km_value = self._to_float_or_none(start_km)
        if start_km_value is None:
            raise ValueError("Informe um KM inicial válido.")
        self._validate_start_km_against_previous(work_date, start_km_value)

        candidate = self.work_days_repo.buscar_incompleta_por_data(work_date)
        payload = {
            "work_date": work_date,
            "start_time": now.isoformat(),
            "start_time_source": "auto",
            "start_km": start_km_value,
            "notes": self._clean_text(notes),
            "status": "open",
        }
        event_type = "check_in"
        if candidate and not self._clean_text(candidate.get("start_time")):
            work_day = self.work_days_repo.atualizar(int(candidate["id"]), payload)
            work_day_id = int(candidate["id"])
        else:
            work_day = self.work_days_repo.inserir(payload)
            work_day_id = int(work_day.get("id", 0))
        self._recalculate_all()
        refreshed = self._serialize_day(self.work_days_repo.buscar_por_id(work_day_id))
        self._write_event(work_day_id, event_type, km_value=start_km_value, new_value=refreshed, notes=notes)
        return self.detalhar_jornada(work_day_id)

    def encerrar_jornada(self, end_km: float, notes: str = "") -> dict:
        work_day = self.work_days_repo.buscar_aberta()
        if not work_day:
            raise ValueError("Nenhuma jornada aberta para encerrar.")
        current = self._serialize_day(work_day)
        end_km_value = self._to_float_or_none(end_km)
        if end_km_value is None:
            raise ValueError("Informe um KM final válido.")
        self._validate_km_order(self._to_float_or_none(current.get("start_km")), end_km_value)
        end_time = self._utc_now().isoformat()
        self._validate_time_order(current.get("start_time"), end_time)
        old_value = dict(current)
        updated = self.work_days_repo.atualizar(
            int(current["id"]),
            {
                "end_time": end_time,
                "end_time_source": "auto",
                "end_km": end_km_value,
                "notes": self._clean_text(notes) or current.get("notes", ""),
            },
        )
        self._recalculate_all()
        refreshed = self._serialize_day(self.work_days_repo.buscar_por_id(int(current["id"])))
        self._write_event(
            int(current["id"]),
            "check_out",
            km_value=end_km_value,
            old_value=old_value,
            new_value=refreshed,
            notes=notes,
        )
        return self.detalhar_jornada(int(current["id"]))

    def criar_jornada_manual(
        self,
        work_date: str,
        start_time: str | None = None,
        end_time: str | None = None,
        start_km: float | None = None,
        end_km: float | None = None,
        worked_minutes_manual: int | None = None,
        notes: str = "",
        allow_manual_override: bool = False,
    ) -> dict:
        work_date_str = self._to_date_str(work_date)
        if not work_date_str:
            raise ValueError("Data da jornada inválida.")
        self._validate_time_order(start_time, end_time, allow_override=allow_manual_override)
        self._validate_km_order(self._to_float_or_none(start_km), self._to_float_or_none(end_km), allow_override=allow_manual_override)
        self._validate_start_km_against_previous(
            work_date_str,
            self._to_float_or_none(start_km),
            allow_override=allow_manual_override,
        )
        candidate = self.work_days_repo.buscar_incompleta_por_data(work_date_str)
        payload = WorkDay.from_raw(
            {
                "work_date": work_date_str,
                "start_time": self._to_iso_timestamp(start_time) if start_time else None,
                "end_time": self._to_iso_timestamp(end_time) if end_time else None,
                "start_time_source": "manual" if start_time else "auto",
                "end_time_source": "manual" if end_time else "auto",
                "start_km": self._to_float_or_none(start_km),
                "end_km": self._to_float_or_none(end_km),
                "worked_minutes_manual": self._to_int_or_none(worked_minutes_manual),
                "notes": notes,
            }
        ).to_record()
        work_day_id: int
        event_type = "manual_create"
        if candidate and candidate.get("status") in {"partial", "open"}:
            old_value = self._serialize_day(candidate)
            self.work_days_repo.atualizar(int(candidate["id"]), payload)
            work_day_id = int(candidate["id"])
            event_type = "manual_complete"
        else:
            created = self.work_days_repo.inserir(payload)
            work_day_id = int(created.get("id", 0))
            old_value = None
        if not work_day_id:
            raise RuntimeError("Falha ao criar jornada manual.")
        self._recalculate_all()
        refreshed = self._serialize_day(self.work_days_repo.buscar_por_id(work_day_id))
        self._write_event(work_day_id, event_type, old_value=old_value, new_value=refreshed, notes=notes)
        return self.detalhar_jornada(work_day_id)

    def completar_jornada(
        self,
        work_day_id: int,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        start_km: float | None = None,
        end_km: float | None = None,
        worked_minutes_manual: int | None = None,
        notes: str = "",
        allow_manual_override: bool = False,
    ) -> dict:
        existing = self._serialize_day(self.work_days_repo.buscar_por_id(int(work_day_id)))
        if not existing:
            raise ValueError("Jornada não encontrada.")
        merged = dict(existing)
        if start_time:
            merged["start_time"] = self._to_iso_timestamp(start_time)
            merged["start_time_source"] = "manual"
        if end_time:
            merged["end_time"] = self._to_iso_timestamp(end_time)
            merged["end_time_source"] = "manual"
        if start_km is not None:
            merged["start_km"] = self._to_float_or_none(start_km)
        if end_km is not None:
            merged["end_km"] = self._to_float_or_none(end_km)
        if worked_minutes_manual is not None:
            merged["worked_minutes_manual"] = self._to_int_or_none(worked_minutes_manual)
        if notes:
            merged["notes"] = self._clean_text(notes)
        self._validate_time_order(merged.get("start_time"), merged.get("end_time"), allow_override=allow_manual_override)
        self._validate_km_order(merged.get("start_km"), merged.get("end_km"), allow_override=allow_manual_override)
        self._validate_start_km_against_previous(
            merged.get("work_date", ""),
            self._to_float_or_none(merged.get("start_km")),
            current_id=int(work_day_id),
            allow_override=allow_manual_override,
        )
        self.work_days_repo.atualizar(int(work_day_id), merged)
        self._recalculate_all()
        refreshed = self._serialize_day(self.work_days_repo.buscar_por_id(int(work_day_id)))
        self._write_event(
            int(work_day_id),
            "manual_complete",
            old_value=existing,
            new_value=refreshed,
            notes=notes,
        )
        return self.detalhar_jornada(int(work_day_id))

    def editar_jornada(
        self,
        work_day_id: int,
        payload: dict[str, Any],
        *,
        allow_manual_override: bool = False,
        notes: str = "",
    ) -> dict:
        existing = self._serialize_day(self.work_days_repo.buscar_por_id(int(work_day_id)))
        if not existing:
            raise ValueError("Jornada não encontrada.")

        merged = dict(existing)
        for key in ("work_date", "start_time", "end_time", "start_km", "end_km", "worked_minutes_manual", "notes"):
            if key not in payload:
                continue
            value = payload.get(key)
            if key == "work_date":
                merged[key] = self._to_date_str(value)
            elif key in {"start_time", "end_time"}:
                merged[key] = self._to_iso_timestamp(value) if value else ""
                merged[f"{key}_source"] = "manual"
            elif key in {"start_km", "end_km"}:
                merged[key] = self._to_float_or_none(value)
            elif key == "worked_minutes_manual":
                merged[key] = self._to_int_or_none(value)
            else:
                merged[key] = self._clean_text(value)

        merged["is_manually_adjusted"] = True
        self._validate_time_order(merged.get("start_time"), merged.get("end_time"), allow_override=allow_manual_override)
        self._validate_km_order(merged.get("start_km"), merged.get("end_km"), allow_override=allow_manual_override)
        self._validate_start_km_against_previous(
            merged.get("work_date", ""),
            self._to_float_or_none(merged.get("start_km")),
            current_id=int(work_day_id),
            allow_override=allow_manual_override,
        )

        self.work_days_repo.atualizar(int(work_day_id), merged)
        self._recalculate_all()
        refreshed = self._serialize_day(self.work_days_repo.buscar_por_id(int(work_day_id)))
        self._write_event(
            int(work_day_id),
            "manual_edit",
            old_value=existing,
            new_value=refreshed,
            notes=notes or payload.get("notes", ""),
        )
        return self.detalhar_jornada(int(work_day_id))
