"""Application service orchestrating repositories and metrics."""

from __future__ import annotations

import uuid

import pandas as pd

from repositories.categorias_despesas_repository import CategoriasDespesasRepository
from repositories.controle_litros_repository import ControleLitrosRepository
from repositories.controle_km_repository import ControleKMRepository
from repositories.despesas_repository import DespesasRepository
from repositories.investimentos_repository import InvestimentosRepository
from repositories.receitas_repository import ReceitasRepository
from repositories.usuarios_repository import UsuariosRepository
from repositories.work_days_repository import WorkDaysRepository
from repositories.work_km_periods_repository import WorkKmPeriodsRepository
from services.metrics_service import MetricsService


class DashboardService:
    """Facade service consumed by Streamlit UI pages."""

    def __init__(self) -> None:
        self.receitas_repo = ReceitasRepository()
        self.despesas_repo = DespesasRepository()
        self.controle_km_repo = ControleKMRepository()
        self.controle_litros_repo = ControleLitrosRepository()
        self.investimentos_repo = InvestimentosRepository()
        self.categorias_repo = CategoriasDespesasRepository()
        self.usuarios_repo = UsuariosRepository()
        self.work_days_repo = WorkDaysRepository()
        self.work_km_periods_repo = WorkKmPeriodsRepository()
        self.metrics = MetricsService()

    @staticmethod
    def _to_date_str(value) -> str:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return ""
        return parsed.date().isoformat()

    @staticmethod
    def _to_float(value) -> float:
        try:
            if pd.isna(value):
                return 0.0
        except Exception:
            pass
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _to_bool(value) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "t", "sim", "yes", "y"}
        return bool(value)

    @staticmethod
    def _normalize_title(value: str) -> str:
        return " ".join(str(value).strip().split()).title()

    def listar_categorias_despesas(self) -> list[str]:
        """Return normalized list of expense categories."""

        df = self.categorias_repo.listar()
        if df.empty or "nome" not in df.columns:
            return []
        values = [self._normalize_title(v) for v in df["nome"].dropna().astype(str).tolist() if str(v).strip()]
        return sorted(set(values))

    def garantir_categoria_despesa(self, nome: str) -> str:
        """Ensure category exists and return normalized display value."""

        normalized = self._normalize_title(nome)
        if not normalized:
            raise ValueError("Informe uma categoria válida.")

        existentes = {v.casefold(): v for v in self.listar_categorias_despesas()}
        if normalized.casefold() not in existentes:
            self.categorias_repo.inserir(normalized)
        return normalized

    def _receita_duplicada(
        self,
        data: str,
        valor: float,
        observacao: str = "",
        km: float = 0.0,
        tempo_trabalhado: int = 0,
        km_rodado_total: float = 0.0,
        ignore_id: int | None = None,
    ) -> bool:
        df = self.listar_receitas()
        if df.empty:
            return False
        df_cmp = df.copy()
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp["data"], errors="coerce").dt.date.astype(str)
        df_cmp["valor_cmp"] = pd.to_numeric(df_cmp["valor"], errors="coerce").fillna(0.0)
        df_cmp["km_cmp"] = pd.to_numeric(df_cmp["km"], errors="coerce").fillna(0.0)
        if "km_rodado_total" not in df_cmp.columns:
            df_cmp["km_rodado_total"] = 0.0
        df_cmp["km_rodado_total_cmp"] = pd.to_numeric(df_cmp["km_rodado_total"], errors="coerce").fillna(0.0)
        df_cmp["tempo_cmp"] = pd.to_numeric(df_cmp["tempo trabalhado"], errors="coerce").fillna(0).astype(int)
        df_cmp["obs_cmp"] = df_cmp.get("observacao", pd.Series(dtype="object")).fillna("").astype(str).str.strip()
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["valor_cmp"] == self._to_float(valor))
            & (df_cmp["obs_cmp"] == str(observacao or "").strip())
            & (df_cmp["km_cmp"] == self._to_float(km))
            & (df_cmp["km_rodado_total_cmp"] == self._to_float(km_rodado_total))
            & (df_cmp["tempo_cmp"] == self._to_int(tempo_trabalhado))
        ).any()

    def _despesa_duplicada(self, data: str, categoria: str, valor: float, ignore_id: int | None = None) -> bool:
        df = self.listar_despesas()
        if df.empty:
            return False
        df_cmp = df.copy()
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp["data"], errors="coerce").dt.date.astype(str)
        df_cmp["categoria_cmp"] = df_cmp["categoria"].astype(str).str.strip().str.lower()
        df_cmp["valor_cmp"] = pd.to_numeric(df_cmp["valor"], errors="coerce").fillna(0.0)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["categoria_cmp"] == str(categoria).strip().lower())
            & (df_cmp["valor_cmp"] == self._to_float(valor))
        ).any()

    @staticmethod
    def _normalize_tipo_despesa(value: str) -> str:
        raw = str(value or "").strip().upper()
        if raw in {"RECORRENTE", "FIXA", "VARIAVEL"}:
            return raw
        return "VARIAVEL"

    @staticmethod
    def _normalize_esfera_despesa(value: str) -> str:
        raw = str(value or "").strip().upper()
        if raw in {"NEGOCIO", "PESSOAL"}:
            return raw
        return "NEGOCIO"

    @staticmethod
    def _normalize_recorrencia_tipo(value: str) -> str:
        raw = str(value or "").strip().upper()
        if raw in {"INDETERMINADO", "PERSONALIZADO"}:
            return raw
        return "INDETERMINADO"

    def _investimento_duplicado(
        self,
        data: str,
        categoria: str,
        aporte: float,
        rendimento: float,
        ignore_id: int | None = None,
    ) -> bool:
        df = self.listar_investimentos()
        if df.empty:
            return False
        df_cmp = df.copy()
        if "categoria" not in df_cmp.columns:
            df_cmp["categoria"] = "Renda Fixa"
        data_base_col = "data_fim" if "data_fim" in df_cmp.columns else "data"
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp[data_base_col], errors="coerce").dt.date.astype(str)
        df_cmp["categoria_cmp"] = df_cmp["categoria"].astype(str).str.strip().str.lower()
        df_cmp["aporte_cmp"] = pd.to_numeric(df_cmp["aporte"], errors="coerce").fillna(0.0)
        df_cmp["rendimento_cmp"] = pd.to_numeric(df_cmp["rendimento"], errors="coerce").fillna(0.0)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["categoria_cmp"] == str(categoria).strip().lower())
            & (df_cmp["aporte_cmp"] == self._to_float(aporte))
            & (df_cmp["rendimento_cmp"] == self._to_float(rendimento))
        ).any()

    def calcular_aporte_investimento(
        self,
        data: str,
        categoria: str,
        patrimonio_total: float,
        rendimento_total: float,
        ignore_id: int | None = None,
    ) -> float:
        """Infer aporte from current patrimônio/rendimento and previous snapshot in same categoria."""

        patrimonio_atual = self._to_float(patrimonio_total)
        rendimento_atual = self._to_float(rendimento_total)
        if patrimonio_atual < 0 or rendimento_atual < 0:
            raise ValueError("Patrimônio e rendimento devem ser não negativos.")

        aporte_total_atual = patrimonio_atual - rendimento_atual
        if aporte_total_atual < 0:
            raise ValueError("Rendimento não pode ser maior que o patrimônio total.")

        df = self.listar_investimentos()
        if df.empty:
            return aporte_total_atual

        work_df = df.copy()
        if "categoria" not in work_df.columns:
            work_df["categoria"] = "Renda Fixa"
        work_df["data"] = pd.to_datetime(work_df["data"], errors="coerce")
        work_df["patrimonio total"] = pd.to_numeric(work_df["patrimonio total"], errors="coerce").fillna(0.0)
        work_df["rendimento"] = pd.to_numeric(work_df["rendimento"], errors="coerce").fillna(0.0)
        work_df = work_df[work_df["categoria"].astype(str).str.strip().str.lower() == str(categoria).strip().lower()]
        if ignore_id is not None and "id" in work_df.columns:
            work_df = work_df[work_df["id"] != int(ignore_id)]

        data_atual = pd.to_datetime(data, errors="coerce")
        if pd.isna(data_atual):
            raise ValueError("Data do investimento inválida.")

        anteriores = work_df[work_df["data"] < data_atual]
        if anteriores.empty:
            aporte_total_anterior = 0.0
        else:
            ultimo = anteriores.sort_values(by=["data", "id"], ascending=[True, True]).iloc[-1]
            aporte_total_anterior = float(ultimo["patrimonio total"]) - float(ultimo["rendimento"])

        aporte_atual = aporte_total_atual - aporte_total_anterior
        if aporte_atual < 0:
            # Prevent negative aporte snapshots when user reports no rendimento/market oscillation.
            return 0.0

        return float(aporte_atual)

    def listar_receitas(self) -> pd.DataFrame:
        return self.receitas_repo.listar()

    def listar_despesas(self) -> pd.DataFrame:
        return self.despesas_repo.listar()

    def listar_controle_km(self) -> pd.DataFrame:
        return self.controle_km_repo.listar()

    def listar_controle_litros(self) -> pd.DataFrame:
        return self.controle_litros_repo.listar()

    def fuel_consumption_snapshot(self, start_date, end_date) -> dict[str, float | int]:
        start_ts = pd.to_datetime(start_date, errors="coerce")
        end_ts = pd.to_datetime(end_date, errors="coerce")
        if pd.isna(start_ts) or pd.isna(end_ts):
            return {
                "segment_count": 0,
                "litros_total_abastecidos": 0.0,
                "litros_trechos_fechados": 0.0,
                "km_trechos_fechados": 0.0,
                "consumo_km_l": 0.0,
            }

        df = self.listar_controle_litros()
        if df.empty:
            return {
                "segment_count": 0,
                "litros_total_abastecidos": 0.0,
                "litros_trechos_fechados": 0.0,
                "km_trechos_fechados": 0.0,
                "consumo_km_l": 0.0,
            }

        work = df.copy()
        work["data"] = pd.to_datetime(work.get("data"), errors="coerce")
        work = work.dropna(subset=["data"])
        work = work[work["data"] <= end_ts]
        if work.empty:
            return {
                "segment_count": 0,
                "litros_total_abastecidos": 0.0,
                "litros_trechos_fechados": 0.0,
                "km_trechos_fechados": 0.0,
                "consumo_km_l": 0.0,
            }

        work["litros"] = pd.to_numeric(work.get("litros"), errors="coerce").fillna(0.0)
        work["odometro"] = pd.to_numeric(work.get("odometro"), errors="coerce")
        work["tanque_cheio"] = work.get("tanque_cheio", False).apply(self._to_bool)
        if "id" not in work.columns:
            work["id"] = range(1, len(work) + 1)
        work = work.sort_values(by=["data", "id"], ascending=[True, True]).reset_index(drop=True)

        litros_total_abastecidos = float(
            work[(work["data"] >= start_ts) & (work["data"] <= end_ts)]["litros"].sum()
        )

        segmentos: list[dict] = []
        ancora: dict | None = None
        litros_acumulados = 0.0

        for row in work.to_dict(orient="records"):
            if not bool(row.get("tanque_cheio", False)):
                if ancora is not None:
                    litros_acumulados += self._to_float(row.get("litros"))
                continue

            odometro_atual = pd.to_numeric(row.get("odometro"), errors="coerce")
            litros_atual = self._to_float(row.get("litros"))

            if ancora is None:
                if pd.notna(odometro_atual):
                    ancora = dict(row)
                    litros_acumulados = 0.0
                continue

            litros_consumidos = float(litros_acumulados + litros_atual)
            odometro_ancora = pd.to_numeric(ancora.get("odometro"), errors="coerce")
            if pd.notna(odometro_ancora) and pd.notna(odometro_atual):
                km_rodados = float(odometro_atual - odometro_ancora)
                if km_rodados >= 0 and litros_consumidos > 0:
                    segmentos.append(
                        {
                            "start_date": ancora.get("data"),
                            "end_date": row.get("data"),
                            "km_rodados": km_rodados,
                            "litros_consumidos": litros_consumidos,
                            "km_litro": km_rodados / litros_consumidos,
                        }
                    )

            if pd.notna(odometro_atual):
                ancora = dict(row)
            else:
                ancora = None
            litros_acumulados = 0.0

        if not segmentos:
            return {
                "segment_count": 0,
                "litros_total_abastecidos": litros_total_abastecidos,
                "litros_trechos_fechados": 0.0,
                "km_trechos_fechados": 0.0,
                "consumo_km_l": 0.0,
            }

        seg_df = pd.DataFrame(segmentos)
        seg_df["end_date"] = pd.to_datetime(seg_df["end_date"], errors="coerce")
        seg_df = seg_df[(seg_df["end_date"] >= start_ts) & (seg_df["end_date"] <= end_ts)]
        if seg_df.empty:
            return {
                "segment_count": 0,
                "litros_total_abastecidos": litros_total_abastecidos,
                "litros_trechos_fechados": 0.0,
                "km_trechos_fechados": 0.0,
                "consumo_km_l": 0.0,
            }

        km_trechos = float(pd.to_numeric(seg_df["km_rodados"], errors="coerce").fillna(0.0).sum())
        litros_trechos = float(pd.to_numeric(seg_df["litros_consumidos"], errors="coerce").fillna(0.0).sum())
        return {
            "segment_count": int(len(seg_df)),
            "litros_total_abastecidos": litros_total_abastecidos,
            "litros_trechos_fechados": litros_trechos,
            "km_trechos_fechados": km_trechos,
            "consumo_km_l": float(km_trechos / litros_trechos) if litros_trechos > 0 else 0.0,
        }

    def listar_investimentos(self) -> pd.DataFrame:
        return self.investimentos_repo.listar()

    def listar_work_days(self) -> pd.DataFrame:
        return self.work_days_repo.listar()

    def listar_work_km_periods(self) -> pd.DataFrame:
        try:
            return self.work_km_periods_repo.listar()
        except Exception:
            return pd.DataFrame()

    def obter_daily_goal(self) -> float:
        return float(self.usuarios_repo.obter_daily_goal())

    def atualizar_daily_goal(self, daily_goal: float) -> None:
        goal = max(0.0, self._to_float(daily_goal))
        self.usuarios_repo.atualizar_daily_goal(goal)

    @staticmethod
    def _date_overlap_days(start_a, end_a, start_b, end_b) -> int:
        overlap_start = max(pd.to_datetime(start_a), pd.to_datetime(start_b))
        overlap_end = min(pd.to_datetime(end_a), pd.to_datetime(end_b))
        if overlap_start > overlap_end:
            return 0
        return int((overlap_end - overlap_start).days + 1)

    def km_snapshot(self, start_date, end_date) -> dict[str, float]:
        start_ts = pd.to_datetime(start_date, errors="coerce")
        end_ts = pd.to_datetime(end_date, errors="coerce")
        if pd.isna(start_ts) or pd.isna(end_ts):
            return {"km_remunerado": 0.0, "km_total": 0.0, "km_nao_remunerado": 0.0}

        start_day = pd.Timestamp(start_ts).date()
        end_day = pd.Timestamp(end_ts).date()

        jornadas = self.listar_work_days()
        if not jornadas.empty and "work_date" in jornadas.columns:
            jornadas = jornadas.copy()
            jornadas["work_date"] = pd.to_datetime(jornadas["work_date"], errors="coerce").dt.date
            jornadas = jornadas[(jornadas["work_date"] >= start_day) & (jornadas["work_date"] <= end_day)]
        remunerado_jornada = float(pd.to_numeric(jornadas.get("km_remunerado"), errors="coerce").fillna(0.0).sum()) if not jornadas.empty else 0.0

        # Fallback temporário para receitas legadas quando o período ainda não tiver jornadas.
        remunerado_fallback = 0.0
        if remunerado_jornada <= 0:
            receitas = self.listar_receitas()
            if not receitas.empty and "data" in receitas.columns:
                receitas = receitas.copy()
                receitas["data"] = pd.to_datetime(receitas["data"], errors="coerce").dt.date
                receitas = receitas[(receitas["data"] >= start_day) & (receitas["data"] <= end_day)]
                remunerado_fallback = float(pd.to_numeric(receitas.get("km"), errors="coerce").fillna(0.0).sum())
        km_remunerado = float(remunerado_jornada if remunerado_jornada > 0 else remunerado_fallback)

        total_from_periods = 0.0
        periods = self.listar_work_km_periods()
        covered_days: set[str] = set()
        if not periods.empty:
            periods = periods.copy()
            periods["start_date"] = pd.to_datetime(periods["start_date"], errors="coerce").dt.date
            periods["end_date"] = pd.to_datetime(periods["end_date"], errors="coerce").dt.date
            periods["km_total_periodo"] = pd.to_numeric(periods["km_total_periodo"], errors="coerce").fillna(0.0)
            for row in periods.to_dict(orient="records"):
                overlap_days = self._date_overlap_days(row["start_date"], row["end_date"], start_day, end_day)
                if overlap_days <= 0:
                    continue
                total_days = self._date_overlap_days(row["start_date"], row["end_date"], row["start_date"], row["end_date"])
                if total_days <= 0:
                    continue
                total_from_periods += float(row["km_total_periodo"]) * float(overlap_days / total_days)
                for day in pd.date_range(max(pd.Timestamp(row["start_date"]), pd.Timestamp(start_day)), min(pd.Timestamp(row["end_date"]), pd.Timestamp(end_day)), freq="D"):
                    covered_days.add(day.date().isoformat())

        total_from_jornada = 0.0
        if not jornadas.empty:
            for row in jornadas.to_dict(orient="records"):
                day_key = pd.Timestamp(row["work_date"]).date().isoformat() if pd.notna(row.get("work_date")) else ""
                if day_key in covered_days:
                    continue
                start_km = pd.to_numeric(row.get("start_km"), errors="coerce")
                end_km = pd.to_numeric(row.get("end_km"), errors="coerce")
                km_rem = self._to_float(row.get("km_remunerado"))
                km_gap = self._to_float(row.get("km_nao_remunerado_antes"))
                if pd.notna(start_km) and pd.notna(end_km):
                    remunerado_dia = float(max(float(end_km) - float(start_km), 0.0))
                    total_from_jornada += float(max(remunerado_dia + max(km_gap, 0.0), 0.0))
                elif not covered_days and (km_rem or km_gap):
                    total_from_jornada += float(max(km_rem + km_gap, 0.0))

        total_from_controle = 0.0
        if total_from_periods + total_from_jornada <= 0:
            controle = self.listar_controle_km()
            if not controle.empty:
                controle = controle.copy()
                controle["data_inicio"] = pd.to_datetime(controle["data_inicio"], errors="coerce").dt.date
                controle["data_fim"] = pd.to_datetime(controle["data_fim"], errors="coerce").dt.date
                controle["km_total_rodado"] = pd.to_numeric(controle.get("km_total_rodado"), errors="coerce").fillna(0.0)
                for row in controle.to_dict(orient="records"):
                    overlap_days = self._date_overlap_days(row["data_inicio"], row["data_fim"], start_day, end_day)
                    if overlap_days <= 0:
                        continue
                    total_days = self._date_overlap_days(row["data_inicio"], row["data_fim"], row["data_inicio"], row["data_fim"])
                    if total_days <= 0:
                        continue
                    total_from_controle += float(row["km_total_rodado"]) * float(overlap_days / total_days)

        km_total = float(max(total_from_periods + total_from_jornada + total_from_controle, 0.0))
        km_nao_remunerado = float(max(km_total - km_remunerado, 0.0))
        return {
            "km_remunerado": km_remunerado,
            "km_total": km_total,
            "km_nao_remunerado": km_nao_remunerado,
        }

    def criar_controle_km(self, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        self.controle_km_repo.inserir(data_inicio, data_fim, km_total_rodado)

    def atualizar_controle_km(self, item_id: int, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        self.controle_km_repo.atualizar(item_id, data_inicio, data_fim, km_total_rodado)

    def deletar_controle_km(self, item_id: int) -> None:
        self.controle_km_repo.deletar(item_id)

    def criar_controle_litros(
        self,
        data: str,
        litros: float,
        odometro: float | None = None,
        valor_total: float = 0.0,
        tanque_cheio: bool = False,
        tipo_combustivel: str = "",
        observacao: str = "",
    ) -> None:
        self.controle_litros_repo.inserir(
            data,
            litros,
            odometro=odometro,
            valor_total=valor_total,
            tanque_cheio=tanque_cheio,
            tipo_combustivel=tipo_combustivel,
            observacao=observacao,
        )

    def atualizar_controle_litros(
        self,
        item_id: int,
        data: str,
        litros: float,
        odometro: float | None = None,
        valor_total: float = 0.0,
        tanque_cheio: bool = False,
        tipo_combustivel: str = "",
        observacao: str = "",
    ) -> None:
        self.controle_litros_repo.atualizar(
            item_id,
            data,
            litros,
            odometro=odometro,
            valor_total=valor_total,
            tanque_cheio=tanque_cheio,
            tipo_combustivel=tipo_combustivel,
            observacao=observacao,
        )

    def deletar_controle_litros(self, item_id: int) -> None:
        self.controle_litros_repo.deletar(item_id)

    def criar_receita(
        self,
        data: str,
        valor: float,
        km: float = 0.0,
        tempo_trabalhado: int = 0,
        observacao: str = "",
        km_rodado_total: float = 0.0,
    ) -> None:
        if self._receita_duplicada(data, valor, observacao, km, tempo_trabalhado, km_rodado_total=km_rodado_total):
            raise ValueError("Registro já existente.")
        self.receitas_repo.inserir(data, valor, km, tempo_trabalhado, observacao, km_rodado_total=km_rodado_total)

    def atualizar_receita(
        self,
        item_id: int,
        data: str,
        valor: float,
        km: float = 0.0,
        tempo_trabalhado: int = 0,
        observacao: str = "",
        km_rodado_total: float = 0.0,
    ) -> None:
        if self._receita_duplicada(
            data,
            valor,
            observacao,
            km,
            tempo_trabalhado,
            km_rodado_total=km_rodado_total,
            ignore_id=item_id,
        ):
            raise ValueError("Registro já existente.")
        self.receitas_repo.atualizar(
            item_id,
            data,
            valor,
            km,
            tempo_trabalhado,
            observacao,
            km_rodado_total=km_rodado_total,
        )

    def deletar_receita(self, item_id: int) -> None:
        self.receitas_repo.deletar(item_id)

    def criar_despesa(
        self,
        data: str,
        categoria: str,
        valor: float,
        observacao: str = "",
        tipo_despesa: str = "VARIAVEL",
        subcategoria_fixa: str = "",
        esfera_despesa: str = "NEGOCIO",
        litros: float = 0.0,
        recorrencia_tipo: str = "",
        recorrencia_meses: int = 0,
    ) -> None:
        categoria_ok = self.garantir_categoria_despesa(categoria)
        tipo_ok = self._normalize_tipo_despesa(tipo_despesa)
        esfera_ok = self._normalize_esfera_despesa(esfera_despesa)
        subcat_ok = str(subcategoria_fixa or "").strip()
        if tipo_ok == "FIXA":
            subcat_ok = subcat_ok or str(observacao or "").strip() or "Sem subcategoria"
        else:
            subcat_ok = ""

        data_base = self._to_date_str(data)
        if not data_base:
            raise ValueError("Data inválida.")

        if tipo_ok != "RECORRENTE":
            if self._despesa_duplicada(data_base, categoria_ok, valor):
                raise ValueError("Registro já existente.")
            self.despesas_repo.inserir(
                data_base,
                categoria_ok,
                valor,
                observacao,
                tipo_despesa=tipo_ok,
                subcategoria_fixa=subcat_ok,
                esfera_despesa=esfera_ok,
                litros=litros,
            )
            return

        recorrencia_tipo_ok = self._normalize_recorrencia_tipo(recorrencia_tipo)
        meses = max(1, self._to_int(recorrencia_meses))

        if recorrencia_tipo_ok == "INDETERMINADO":
            if self._despesa_duplicada(data_base, categoria_ok, valor):
                raise ValueError("Registro já existente.")
            self.despesas_repo.inserir(
                data_base,
                categoria_ok,
                valor,
                observacao,
                tipo_despesa=tipo_ok,
                subcategoria_fixa=subcat_ok,
                esfera_despesa=esfera_ok,
                litros=litros,
                recorrencia_tipo=recorrencia_tipo_ok,
                recorrencia_meses=0,
                recorrencia_serie_id="",
            )
            return

        serie_id = uuid.uuid4().hex if meses > 1 else ""
        start_ts = pd.to_datetime(data_base, errors="coerce")
        if pd.isna(start_ts):
            raise ValueError("Data inválida.")

        for idx in range(meses):
            data_item = (start_ts + pd.DateOffset(months=idx)).date().isoformat()
            if self._despesa_duplicada(data_item, categoria_ok, valor):
                raise ValueError(f"Registro já existente para {data_item}.")
            self.despesas_repo.inserir(
                data_item,
                categoria_ok,
                valor,
                observacao,
                tipo_despesa=tipo_ok,
                subcategoria_fixa=subcat_ok,
                esfera_despesa=esfera_ok,
                litros=litros,
                recorrencia_tipo=recorrencia_tipo_ok,
                recorrencia_meses=meses,
                recorrencia_serie_id=serie_id,
            )

    def atualizar_despesa(
        self,
        item_id: int,
        data: str,
        categoria: str,
        valor: float,
        observacao: str,
        tipo_despesa: str = "VARIAVEL",
        subcategoria_fixa: str = "",
        esfera_despesa: str = "NEGOCIO",
        litros: float = 0.0,
        recorrencia_tipo: str = "",
        recorrencia_meses: int = 0,
        recorrencia_serie_id: str = "",
    ) -> None:
        categoria_ok = self.garantir_categoria_despesa(categoria)
        if self._despesa_duplicada(data, categoria_ok, valor, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        tipo_ok = self._normalize_tipo_despesa(tipo_despesa)
        esfera_ok = self._normalize_esfera_despesa(esfera_despesa)
        subcat_ok = str(subcategoria_fixa or "").strip()
        recorrencia_tipo_ok = ""
        recorrencia_meses_ok = 0
        recorrencia_serie_id_ok = ""
        if tipo_ok == "FIXA":
            subcat_ok = subcat_ok or str(observacao or "").strip() or "Sem subcategoria"
        else:
            subcat_ok = ""
        if tipo_ok == "RECORRENTE":
            recorrencia_tipo_ok = self._normalize_recorrencia_tipo(recorrencia_tipo)
            recorrencia_meses_ok = max(1, self._to_int(recorrencia_meses)) if recorrencia_tipo_ok == "PERSONALIZADO" else 0
            recorrencia_serie_id_ok = str(recorrencia_serie_id or "").strip()

        if tipo_ok == "VARIAVEL" and not subcat_ok:
            self.despesas_repo.atualizar(
                item_id,
                data,
                categoria_ok,
                valor,
                observacao,
                esfera_despesa=esfera_ok,
                litros=litros,
                recorrencia_tipo=recorrencia_tipo_ok,
                recorrencia_meses=recorrencia_meses_ok,
                recorrencia_serie_id=recorrencia_serie_id_ok,
            )
        else:
            self.despesas_repo.atualizar(
                item_id,
                data,
                categoria_ok,
                valor,
                observacao,
                tipo_despesa=tipo_ok,
                subcategoria_fixa=subcat_ok,
                esfera_despesa=esfera_ok,
                litros=litros,
                recorrencia_tipo=recorrencia_tipo_ok,
                recorrencia_meses=recorrencia_meses_ok,
                recorrencia_serie_id=recorrencia_serie_id_ok,
            )

    def deletar_despesa(self, item_id: int) -> None:
        self.despesas_repo.deletar(item_id)

    def criar_investimento(
        self,
        data: str,
        categoria: str,
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        tipo_movimentacao: str | None = None,
    ) -> None:
        categoria_ok = str(categoria).strip() or "Renda Fixa"
        if self._investimento_duplicado(data, categoria_ok, aporte, rendimento):
            raise ValueError("Registro já existente.")
        self.investimentos_repo.inserir(
            data,
            categoria_ok,
            aporte,
            total_aportado,
            rendimento,
            patrimonio_total,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_movimentacao=tipo_movimentacao,
        )
        self.investimentos_repo.recalcular_total_aportado()
        self.investimentos_repo.recalcular_patrimonio_total()

    def atualizar_investimento(
        self,
        item_id: int,
        data: str,
        categoria: str,
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        tipo_movimentacao: str | None = None,
    ) -> None:
        categoria_ok = str(categoria).strip() or "Renda Fixa"
        if self._investimento_duplicado(data, categoria_ok, aporte, rendimento, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        self.investimentos_repo.atualizar(
            item_id,
            data,
            categoria_ok,
            aporte,
            total_aportado,
            rendimento,
            patrimonio_total,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_movimentacao=tipo_movimentacao,
        )
        self.investimentos_repo.recalcular_total_aportado()
        self.investimentos_repo.recalcular_patrimonio_total()

    def deletar_investimento(self, item_id: int) -> None:
        self.investimentos_repo.deletar(item_id)
        self.investimentos_repo.recalcular_total_aportado()
        self.investimentos_repo.recalcular_patrimonio_total()

    def recalcular_total_aportado(self) -> None:
        self.investimentos_repo.recalcular_total_aportado()

    def recalcular_patrimonio_total(self) -> None:
        self.investimentos_repo.recalcular_patrimonio_total()

    def resumo_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> dict:
        return self.metrics.resumo_mensal(df_receitas, df_despesas, meta=self.obter_daily_goal())

    def score_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> int:
        return self.metrics.score_mensal(df_receitas, df_despesas, meta=self.obter_daily_goal())
