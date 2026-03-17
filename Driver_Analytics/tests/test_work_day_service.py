"""Tests for jornada de trabalho service rules."""

from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

import pandas as pd

from UI.jornada_ui import _work_day_bootstrap_message
from services.work_day_service import WorkDayService


class _FakeWorkDaysRepository:
    def __init__(self):
        self.rows: list[dict] = []
        self.next_id = 1

    def listar_raw(self):
        return [copy.deepcopy(row) for row in self.rows]

    def buscar_por_id(self, item_id: int):
        for row in self.rows:
            if int(row["id"]) == int(item_id):
                return copy.deepcopy(row)
        return None

    def buscar_aberta(self):
        for row in sorted(self.rows, key=lambda item: item.get("created_at", ""), reverse=True):
            if row.get("status") == "open":
                return copy.deepcopy(row)
        return None

    def buscar_incompleta_por_data(self, work_date: str):
        candidates = [row for row in self.rows if str(row.get("work_date")) == str(work_date) and row.get("status") in {"partial", "open"}]
        if not candidates:
            return None
        return copy.deepcopy(sorted(candidates, key=lambda item: item.get("created_at", ""), reverse=True)[0])

    def buscar_ultima_fechada_antes(self, work_date: str, current_id: int | None = None):
        candidates = [
            row
            for row in self.rows
            if row.get("status") in {"closed", "adjusted", "manual"}
            and str(row.get("work_date")) < str(work_date)
            and (current_id is None or int(row["id"]) != int(current_id))
        ]
        if not candidates:
            return None
        return copy.deepcopy(sorted(candidates, key=lambda item: (item.get("work_date", ""), item["id"]), reverse=True)[0])

    def inserir(self, payload: dict):
        row = copy.deepcopy(payload)
        row["id"] = self.next_id
        self.next_id += 1
        row.setdefault("created_at", f"2026-03-{row['id']:02d}T00:00:00+00:00")
        row.setdefault("updated_at", row["created_at"])
        self.rows.append(row)
        return copy.deepcopy(row)

    def atualizar(self, item_id: int, payload: dict):
        for idx, row in enumerate(self.rows):
            if int(row["id"]) == int(item_id):
                self.rows[idx] = {**row, **copy.deepcopy(payload), "id": int(item_id)}
                if not self.rows[idx].get("updated_at"):
                    self.rows[idx]["updated_at"] = self.rows[idx].get("created_at")
                return copy.deepcopy(self.rows[idx])
        return None

    def deletar(self, item_id: int):
        self.rows = [row for row in self.rows if int(row["id"]) != int(item_id)]


class _FakeWorkDayEventsRepository:
    def __init__(self):
        self.rows: list[dict] = []
        self.next_id = 1

    def inserir(self, payload: dict):
        row = copy.deepcopy(payload)
        row["id"] = self.next_id
        self.next_id += 1
        self.rows.append(row)
        return copy.deepcopy(row)

    def listar_por_work_day(self, work_day_id: int):
        import pandas as pd

        rows = [copy.deepcopy(row) for row in self.rows if int(row["work_day_id"]) == int(work_day_id)]
        return pd.DataFrame(rows)

    def deletar_por_work_day(self, work_day_id: int):
        self.rows = [row for row in self.rows if int(row["work_day_id"]) != int(work_day_id)]


class _FakeReceitasRepository:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []

    def listar(self):
        return pd.DataFrame(copy.deepcopy(self.rows))


class _FakeWorkKmPeriodsRepository:
    def __init__(self):
        self.rows: list[dict] = []
        self.next_id = 1

    def listar_raw(self):
        return [copy.deepcopy(row) for row in self.rows]

    def listar(self):
        return pd.DataFrame(copy.deepcopy(self.rows))

    def buscar_por_id(self, item_id: int):
        for row in self.rows:
            if int(row["id"]) == int(item_id):
                return copy.deepcopy(row)
        return None

    def inserir(self, payload: dict):
        row = copy.deepcopy(payload)
        row["id"] = self.next_id
        self.next_id += 1
        row.setdefault("created_at", f"2026-03-{row['id']:02d}T00:00:00+00:00")
        row.setdefault("updated_at", row["created_at"])
        self.rows.append(row)
        return copy.deepcopy(row)

    def atualizar(self, item_id: int, payload: dict):
        for idx, row in enumerate(self.rows):
            if int(row["id"]) == int(item_id):
                self.rows[idx] = {**row, **copy.deepcopy(payload), "id": int(item_id)}
                return copy.deepcopy(self.rows[idx])
        return None

    def deletar(self, item_id: int):
        self.rows = [row for row in self.rows if int(row["id"]) != int(item_id)]


class WorkDayServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = WorkDayService()
        self.service.work_days_repo = _FakeWorkDaysRepository()
        self.service.events_repo = _FakeWorkDayEventsRepository()
        self.service.receitas_repo = _FakeReceitasRepository()
        self.service.work_km_periods_repo = _FakeWorkKmPeriodsRepository()

    def test_iniciar_jornada_cria_open_e_registra_evento(self):
        self.service._utc_now = lambda: datetime(2026, 3, 16, 8, 0, tzinfo=timezone.utc)
        self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-15",
                "start_time": "2026-03-15T08:00:00+00:00",
                "end_time": "2026-03-15T18:00:00+00:00",
                "start_time_source": "auto",
                "end_time_source": "auto",
                "start_km": 100.0,
                "end_km": 180.0,
                "status": "closed",
                "created_at": "2026-03-15T08:00:00+00:00",
                "updated_at": "2026-03-15T18:00:00+00:00",
            }
        )

        detail = self.service.iniciar_jornada(start_km=200.0, notes="Inicio")

        self.assertEqual(detail["work_day"]["status"], "open")
        self.assertEqual(detail["work_day"]["start_km"], 200.0)
        self.assertEqual(detail["work_day"]["km_nao_remunerado_antes"], 20.0)
        self.assertEqual(detail["events"][0]["event_type"], "check_in")

    def test_iniciar_jornada_bloqueia_segunda_aberta(self):
        self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-16",
                "start_time": "2026-03-16T08:00:00+00:00",
                "start_time_source": "auto",
                "start_km": 200.0,
                "status": "open",
            }
        )

        with self.assertRaises(ValueError):
            self.service.iniciar_jornada(start_km=220.0)

    def test_encerrar_jornada_calcula_km_e_tempo(self):
        self.service._utc_now = lambda: datetime(2026, 3, 16, 18, 30, tzinfo=timezone.utc)
        row = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-16",
                "start_time": "2026-03-16T08:00:00+00:00",
                "start_time_source": "auto",
                "start_km": 200.0,
                "status": "open",
                "created_at": "2026-03-16T08:00:00+00:00",
                "updated_at": "2026-03-16T08:00:00+00:00",
            }
        )

        detail = self.service.encerrar_jornada(end_km=260.0, notes="Fim")

        self.assertEqual(detail["work_day"]["id"], int(row["id"]))
        self.assertEqual(detail["work_day"]["status"], "closed")
        self.assertEqual(detail["work_day"]["km_remunerado"], 60.0)
        self.assertEqual(detail["work_day"]["worked_minutes_calculated"], 630)
        self.assertEqual(detail["events"][0]["event_type"], "check_out")

    def test_edicao_recalcula_km_nao_remunerado_da_jornada_seguinte(self):
        first = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-15",
                "start_time": "2026-03-15T08:00:00+00:00",
                "end_time": "2026-03-15T18:00:00+00:00",
                "start_time_source": "auto",
                "end_time_source": "auto",
                "start_km": 100.0,
                "end_km": 180.0,
                "status": "closed",
                "created_at": "2026-03-15T08:00:00+00:00",
                "updated_at": "2026-03-15T18:00:00+00:00",
            }
        )
        second = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-16",
                "start_time": "2026-03-16T08:00:00+00:00",
                "end_time": "2026-03-16T18:00:00+00:00",
                "start_time_source": "auto",
                "end_time_source": "auto",
                "start_km": 200.0,
                "end_km": 260.0,
                "status": "closed",
                "created_at": "2026-03-16T08:00:00+00:00",
                "updated_at": "2026-03-16T18:00:00+00:00",
            }
        )
        self.service._recalculate_all()

        detail = self.service.editar_jornada(int(first["id"]), {"end_km": 190.0}, allow_manual_override=True, notes="Ajuste")

        updated_second = self.service.detalhar_jornada(int(second["id"]))
        self.assertEqual(detail["work_day"]["status"], "adjusted")
        self.assertEqual(updated_second["work_day"]["km_nao_remunerado_antes"], 10.0)

    def test_bootstrap_message_indica_migration_pendente(self):
        message = _work_day_bootstrap_message(RuntimeError("Falha ao consultar work_days no Supabase: relation \"public.work_days\" does not exist"))
        self.assertIn("20260316130000__add_work_days_module.sql", message)
        self.assertIn("20260317090000__add_daily_goal_and_work_km_periods.sql", message)
        self.assertIn("Jornada", message)

    def test_manual_timestamp_is_converted_from_local_timezone_to_utc(self):
        detail = self.service.criar_jornada_manual(
            work_date="2026-03-16",
            start_time="2026-03-16T16:00:00",
            end_time="2026-03-16T18:30:00",
            start_km=100.0,
            end_km=140.0,
        )

        self.assertEqual(detail["work_day"]["start_time"], "2026-03-16T19:00:00+00:00")
        self.assertEqual(detail["work_day"]["end_time"], "2026-03-16T21:30:00+00:00")
        self.assertEqual(detail["work_day"]["worked_minutes_calculated"], 150)

    def test_work_date_uses_local_timezone_on_check_in(self):
        self.service._utc_now = lambda: datetime(2026, 3, 17, 2, 0, tzinfo=timezone.utc)

        detail = self.service.iniciar_jornada(start_km=10.0)

        self.assertEqual(detail["work_day"]["work_date"], "2026-03-16")
        self.assertEqual(detail["work_day"]["start_time"], "2026-03-17T02:00:00+00:00")

    def test_deletar_jornada_recalcula_jornada_seguinte(self):
        first = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-15",
                "start_time": "2026-03-15T08:00:00+00:00",
                "end_time": "2026-03-15T18:00:00+00:00",
                "start_km": 100.0,
                "end_km": 150.0,
                "status": "closed",
            }
        )
        second = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-16",
                "start_time": "2026-03-16T08:00:00+00:00",
                "end_time": "2026-03-16T18:00:00+00:00",
                "start_km": 170.0,
                "end_km": 230.0,
                "status": "closed",
            }
        )
        self.service._recalculate_all()

        self.service.deletar_jornada(int(first["id"]))

        updated_second = self.service.detalhar_jornada(int(second["id"]))
        self.assertEqual(updated_second["work_day"]["km_nao_remunerado_antes"], None)

    def test_km_periodo_calcula_nao_remunerado(self):
        self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-16",
                "start_time": "2026-03-16T08:00:00+00:00",
                "end_time": "2026-03-16T18:00:00+00:00",
                "start_km": 100.0,
                "end_km": 180.0,
                "km_remunerado": 80.0,
                "status": "closed",
            }
        )

        period = self.service.criar_km_periodo("2026-03-16", "2026-03-16", 100.0, notes="Histórico")

        self.assertEqual(period["km_remunerado_periodo"], 80.0)
        self.assertEqual(period["km_nao_remunerado_periodo"], 20.0)

    def test_periodo_historico_reseta_gap_do_hodometro(self):
        self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-01",
                "start_time": "2026-03-01T08:00:00+00:00",
                "end_time": "2026-03-01T18:00:00+00:00",
                "start_km": 1000.0,
                "end_km": 1010.0,
                "status": "closed",
            }
        )
        self.service.work_km_periods_repo.inserir(
            {
                "start_date": "2026-03-02",
                "end_date": "2026-03-10",
                "km_total_periodo": 400.0,
                "notes": "Historico",
            }
        )
        current = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-11",
                "start_time": "2026-03-11T08:00:00+00:00",
                "end_time": "2026-03-11T18:00:00+00:00",
                "start_km": 1200.0,
                "end_km": 1210.0,
                "status": "closed",
            }
        )

        self.service._recalculate_all()

        updated = self.service.detalhar_jornada(int(current["id"]))
        self.assertIsNone(updated["work_day"]["km_nao_remunerado_antes"])

    def test_migrar_receitas_legadas_agrega_por_dia_e_simula_jornada(self):
        self.service.receitas_repo = _FakeReceitasRepository(
            [
                {"data": "2026-03-10", "km": 40.0, "tempo trabalhado": 3600, "valor": 100.0},
                {"data": "2026-03-10", "km": 20.0, "tempo trabalhado": 1800, "valor": 50.0},
                {"data": "2026-03-11", "km": 30.0, "tempo trabalhado": 5400, "valor": 80.0},
            ]
        )

        result = self.service.migrar_receitas_legadas(simulated_start_hour=16)

        self.assertEqual(result["migrated_days"], 2)
        self.assertEqual(result["skipped_days"], 0)
        self.assertAlmostEqual(result["total_km_remunerado"], 90.0)
        self.assertAlmostEqual(result["media_km_remunerado"], 45.0)
        jornadas = self.service.listar_jornadas()
        self.assertEqual(len(jornadas), 2)
        earliest = sorted(jornadas, key=lambda row: row["work_date"])[0]
        self.assertEqual(earliest["work_date"], "2026-03-10")
        self.assertIsNone(earliest["start_km"])
        self.assertIsNone(earliest["end_km"])
        self.assertAlmostEqual(earliest["km_remunerado"], 60.0)
        self.assertEqual(earliest["status"], "manual")
        self.assertEqual(earliest["worked_minutes_final"], 90)

    def test_reparar_hodometro_historico_preenche_registros_anteriores(self):
        self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-16",
                "start_time": "2026-03-16T08:00:00+00:00",
                "end_time": "2026-03-16T18:00:00+00:00",
                "km_remunerado": 40.0,
                "status": "manual",
            }
        )
        middle = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-17",
                "start_time": "2026-03-17T08:00:00+00:00",
                "end_time": "2026-03-17T18:00:00+00:00",
                "km_remunerado": 30.0,
                "status": "manual",
            }
        )
        anchor = self.service.work_days_repo.inserir(
            {
                "work_date": "2026-03-18",
                "start_time": "2026-03-18T08:00:00+00:00",
                "end_time": "2026-03-18T18:00:00+00:00",
                "start_km": 150000.0,
                "end_km": 150020.0,
                "km_remunerado": 20.0,
                "status": "closed",
            }
        )

        result = self.service.reparar_hodometro_historico(intervalo_padrao_km=10.0)

        updated_middle = self.service.detalhar_jornada(int(middle["id"]))["work_day"]
        updated_first = self.service.detalhar_jornada(1)["work_day"]
        self.assertEqual(result["anchor_work_day_id"], int(anchor["id"]))
        self.assertEqual(result["updated_rows"], 2)
        self.assertEqual(updated_middle["end_km"], 149990.0)
        self.assertEqual(updated_middle["start_km"], 149960.0)
        self.assertEqual(updated_first["end_km"], 149950.0)
        self.assertEqual(updated_first["start_km"], 149910.0)


if __name__ == "__main__":
    unittest.main()
