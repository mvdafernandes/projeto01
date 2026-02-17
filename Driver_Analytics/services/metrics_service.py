"""Business metrics service with safe dataframe operations."""

from __future__ import annotations

import pandas as pd

from domain.models import ResumoMensal
from domain.validators import parse_datetime_column, safe_divide


class MetricsService:
    """Pure metrics calculations over input dataframes."""

    RECEITAS_COLS = ["id", "data", "valor", "km", "km_rodado_total", "tempo trabalhado", "observacao"]
    DESPESAS_COLS = ["id", "data", "categoria", "valor", "observacao", "litros"]
    WEEKDAY_LABELS = {
        0: "Segunda-feira",
        1: "Terça-feira",
        2: "Quarta-feira",
        3: "Quinta-feira",
        4: "Sexta-feira",
        5: "Sábado",
        6: "Domingo",
    }

    def _safe_df(self, df: pd.DataFrame | None, expected_cols: list[str]) -> pd.DataFrame:
        safe_df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
        for col in expected_cols:
            if col not in safe_df.columns:
                safe_df[col] = pd.Series(dtype="object")
        return safe_df.loc[:, expected_cols]

    def _numeric_sum(self, df: pd.DataFrame, column: str) -> float:
        if df.empty or column not in df.columns:
            return 0.0
        return float(pd.to_numeric(df[column], errors="coerce").fillna(0.0).sum())

    def _numeric_mean(self, df: pd.DataFrame, column: str) -> float:
        if df.empty or column not in df.columns:
            return 0.0
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            return 0.0
        return float(series.mean())

    def _daily_receita(self, df_receitas: pd.DataFrame | None) -> pd.DataFrame:
        safe_df = parse_datetime_column(self._safe_df(df_receitas, self.RECEITAS_COLS), "data")
        if safe_df.empty:
            return pd.DataFrame(columns=["data", "valor", "registros"])
        work = safe_df.copy()
        work["valor"] = pd.to_numeric(work["valor"], errors="coerce").fillna(0.0)
        work["data"] = work["data"].dt.normalize()
        return (
            work.groupby("data", as_index=False)
            .agg(valor=("valor", "sum"), registros=("id", "count"))
            .sort_values(by="data")
        )

    def _build_daily_calendar(
        self,
        df_receitas: pd.DataFrame | None,
        start_date=None,
        end_date=None,
        meta: float = 300.0,
    ) -> pd.DataFrame:
        daily = self._daily_receita(df_receitas)
        start_ts = pd.to_datetime(start_date, errors="coerce")
        end_ts = pd.to_datetime(end_date, errors="coerce")
        if pd.isna(start_ts):
            start_ts = daily["data"].min() if not daily.empty else pd.NaT
        if pd.isna(end_ts):
            end_ts = daily["data"].max() if not daily.empty else pd.NaT
        if pd.isna(start_ts) or pd.isna(end_ts):
            return pd.DataFrame(columns=["data", "valor", "worked", "meta_hit", "meta_miss", "absent", "weekday"])

        start_ts = pd.Timestamp(start_ts).normalize()
        end_ts = pd.Timestamp(end_ts).normalize()
        if start_ts > end_ts:
            return pd.DataFrame(columns=["data", "valor", "worked", "meta_hit", "meta_miss", "absent", "weekday"])

        calendar = pd.DataFrame({"data": pd.date_range(start=start_ts, end=end_ts, freq="D")})
        base_daily = daily[["data", "valor", "registros"]] if not daily.empty else pd.DataFrame(columns=["data", "valor", "registros"])
        merged = calendar.merge(base_daily, on="data", how="left")
        merged["valor"] = pd.to_numeric(merged["valor"], errors="coerce").fillna(0.0)
        merged["registros"] = pd.to_numeric(merged["registros"], errors="coerce").fillna(0).astype(int)
        merged["worked"] = merged["registros"] > 0
        merged["meta_hit"] = merged["worked"] & (merged["valor"] >= float(meta))
        merged["meta_miss"] = merged["worked"] & (~merged["meta_hit"])
        merged["absent"] = ~merged["worked"]
        merged["weekday_num"] = merged["data"].dt.weekday
        merged["weekday"] = merged["weekday_num"].map(self.WEEKDAY_LABELS)
        return merged

    def _streak_info(self, condition: pd.Series) -> dict[str, int | bool]:
        flags = condition.fillna(False).astype(bool).tolist()
        if not flags:
            return {"longest": 0, "current": 0, "previous_record": 0, "new_record": False}

        runs: list[tuple[int, int]] = []
        start_idx = None
        for idx, flag in enumerate(flags):
            if flag and start_idx is None:
                start_idx = idx
            if not flag and start_idx is not None:
                runs.append((start_idx, idx - 1))
                start_idx = None
        if start_idx is not None:
            runs.append((start_idx, len(flags) - 1))

        if not runs:
            return {"longest": 0, "current": 0, "previous_record": 0, "new_record": False}

        run_lengths = [end - start + 1 for start, end in runs]
        longest = max(run_lengths)

        current = 0
        if flags[-1]:
            current = run_lengths[-1]

        previous_record = longest
        if flags[-1]:
            previous_runs = run_lengths[:-1]
            previous_record = max(previous_runs) if previous_runs else 0
        new_record = bool(flags[-1] and current > previous_record and current > 0)
        return {
            "longest": int(longest),
            "current": int(current),
            "previous_record": int(previous_record),
            "new_record": bool(new_record),
        }

    def _top_weekday(self, calendar: pd.DataFrame, flag_col: str) -> tuple[str, int]:
        if calendar.empty or flag_col not in calendar.columns:
            return "-", 0
        counts = calendar[calendar[flag_col]].groupby("weekday_num").size()
        if counts.empty:
            return "-", 0
        counts = counts.reindex(range(7), fill_value=0)
        max_count = int(counts.max())
        if max_count <= 0:
            return "-", 0
        top_num = int(counts.idxmax())
        return self.WEEKDAY_LABELS.get(top_num, "-"), max_count

    def filtrar_mes(self, df: pd.DataFrame | None, ano: int, mes: int) -> pd.DataFrame:
        """Filter dataframe for the selected year/month."""

        safe_df = self._safe_df(df, self.RECEITAS_COLS if "km" in (df.columns if isinstance(df, pd.DataFrame) else []) else self.DESPESAS_COLS)
        safe_df = parse_datetime_column(safe_df, "data")
        if safe_df.empty:
            return safe_df
        return safe_df[(safe_df["data"].dt.year == int(ano)) & (safe_df["data"].dt.month == int(mes))]

    def filtrar_mes_atual(self, df: pd.DataFrame | None) -> pd.DataFrame:
        """Filter dataframe for current year/month."""

        today = pd.Timestamp.today()
        base = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        cols = self.RECEITAS_COLS if "km" in base.columns else self.DESPESAS_COLS
        return self.filtrar_mes(base, int(today.year), int(today.month)).reindex(columns=cols)

    def receita_total(self, df_receitas: pd.DataFrame | None) -> float:
        """Total receita value."""

        return self._numeric_sum(self._safe_df(df_receitas, self.RECEITAS_COLS), "valor")

    def receita_media_diaria(self, df_receitas: pd.DataFrame | None) -> float:
        """Average receita per row/day."""

        return self._numeric_mean(self._safe_df(df_receitas, self.RECEITAS_COLS), "valor")

    def dias_trabalhados(self, df_receitas: pd.DataFrame | None) -> int:
        """Count of worked days/rows."""

        safe_df = self._safe_df(df_receitas, self.RECEITAS_COLS)
        return int(safe_df.shape[0])

    def dias_meta_batida(self, df_receitas: pd.DataFrame | None, meta: float = 300.0) -> int:
        """Count rows with valor >= target meta."""

        safe_df = self._safe_df(df_receitas, self.RECEITAS_COLS)
        if safe_df.empty:
            return 0
        values = pd.to_numeric(safe_df["valor"], errors="coerce").fillna(0.0)
        return int((values >= float(meta)).sum())

    def percentual_meta_batida(self, df_receitas: pd.DataFrame | None, meta: float = 300.0) -> float:
        """Meta achievement percentage."""

        dias = self.dias_trabalhados(df_receitas)
        return float(safe_divide(self.dias_meta_batida(df_receitas, meta), dias, default=0.0) * 100)

    def km_total(self, df_receitas: pd.DataFrame | None) -> float:
        """Total kilometers."""

        return self._numeric_sum(self._safe_df(df_receitas, self.RECEITAS_COLS), "km")

    def km_rodado_total(self, df_receitas: pd.DataFrame | None) -> float:
        """Total kilometers driven (odometer-based)."""

        return self._numeric_sum(self._safe_df(df_receitas, self.RECEITAS_COLS), "km_rodado_total")

    def km_nao_remunerado_total(self, df_receitas: pd.DataFrame | None) -> float:
        """Total non-paid kilometers."""

        total_rodado = self.km_rodado_total(df_receitas)
        total_remunerado = self.km_total(df_receitas)
        return float(max(total_rodado - total_remunerado, 0.0))

    def km_remunerado_pct(self, df_receitas: pd.DataFrame | None) -> float:
        """Share of paid kilometers over total driven kilometers."""

        return float(safe_divide(self.km_total(df_receitas), self.km_rodado_total(df_receitas), default=0.0) * 100)

    def km_nao_remunerado_pct(self, df_receitas: pd.DataFrame | None) -> float:
        """Share of non-paid kilometers over total driven kilometers."""

        return float(100.0 - self.km_remunerado_pct(df_receitas)) if self.km_rodado_total(df_receitas) > 0 else 0.0

    def receita_por_km(self, df_receitas: pd.DataFrame | None) -> float:
        """Receita per kilometer."""

        return float(safe_divide(self.receita_total(df_receitas), self.km_total(df_receitas), default=0.0))

    def despesa_total(self, df_despesas: pd.DataFrame | None) -> float:
        """Total despesa value."""

        return self._numeric_sum(self._safe_df(df_despesas, self.DESPESAS_COLS), "valor")

    def despesa_media(self, df_despesas: pd.DataFrame | None) -> float:
        """Average despesa per row."""

        return self._numeric_mean(self._safe_df(df_despesas, self.DESPESAS_COLS), "valor")

    def despesa_por_categoria(self, df_despesas: pd.DataFrame | None) -> pd.Series:
        """Aggregated expenses by category."""

        safe_df = self._safe_df(df_despesas, self.DESPESAS_COLS)
        if safe_df.empty:
            return pd.Series(dtype="float64")
        work_df = safe_df.copy()
        work_df["valor"] = pd.to_numeric(work_df["valor"], errors="coerce").fillna(0.0)
        work_df["categoria"] = work_df["categoria"].fillna("Sem categoria").astype(str)
        return work_df.groupby("categoria")["valor"].sum().sort_values(ascending=False)

    def litros_combustivel_total(self, df_despesas: pd.DataFrame | None) -> float:
        """Total liters fueled in period."""

        safe_df = self._safe_df(df_despesas, self.DESPESAS_COLS)
        if safe_df.empty:
            return 0.0
        work_df = safe_df.copy()
        categorias = work_df["categoria"].fillna("").astype(str).str.lower().str.strip()
        mask = categorias.isin(["combustível", "combustivel"])
        if not mask.any():
            return 0.0
        return float(pd.to_numeric(work_df.loc[mask, "litros"], errors="coerce").fillna(0.0).sum())

    def consumo_medio_km_por_litro(self, df_receitas: pd.DataFrame | None, df_despesas: pd.DataFrame | None) -> float:
        """Average km/l based on total driven kilometers and fueled liters."""

        return float(safe_divide(self.km_rodado_total(df_receitas), self.litros_combustivel_total(df_despesas), default=0.0))

    def lucro_bruto(self, df_receitas: pd.DataFrame | None, df_despesas: pd.DataFrame | None) -> float:
        """Gross profit."""

        return float(self.receita_total(df_receitas) - self.despesa_total(df_despesas))

    def lucro_medio_diario(self, df_receitas: pd.DataFrame | None, df_despesas: pd.DataFrame | None) -> float:
        """Daily average profit."""

        return float(safe_divide(self.lucro_bruto(df_receitas, df_despesas), self.dias_trabalhados(df_receitas), default=0.0))

    def margem_lucro(self, df_receitas: pd.DataFrame | None, df_despesas: pd.DataFrame | None) -> float:
        """Profit margin percentage."""

        return float(safe_divide(self.lucro_bruto(df_receitas, df_despesas), self.receita_total(df_receitas), default=0.0) * 100)

    def lucro_por_km(self, df_receitas: pd.DataFrame | None, df_despesas: pd.DataFrame | None) -> float:
        """Profit per kilometer."""

        return float(safe_divide(self.lucro_bruto(df_receitas, df_despesas), self.km_total(df_receitas), default=0.0))

    def resumo_mensal(self, df_receitas: pd.DataFrame | None, df_despesas: pd.DataFrame | None) -> dict:
        """Monthly summary with guaranteed field schema."""

        try:
            df_r = self.filtrar_mes_atual(self._safe_df(df_receitas, self.RECEITAS_COLS))
            df_d = self.filtrar_mes_atual(self._safe_df(df_despesas, self.DESPESAS_COLS))

            resumo = ResumoMensal(
                receita_total=self.receita_total(df_r),
                despesa_total=self.despesa_total(df_d),
                lucro=self.lucro_bruto(df_r, df_d),
                margem_pct=self.margem_lucro(df_r, df_d),
                dias_trabalhados=self.dias_trabalhados(df_r),
                meta_batida_pct=self.percentual_meta_batida(df_r),
                receita_por_km=self.receita_por_km(df_r),
                lucro_por_km=self.lucro_por_km(df_r, df_d),
            )
            return resumo.to_dict()
        except Exception:
            return ResumoMensal().to_dict()

    def score_mensal(self, df_receitas: pd.DataFrame | None, df_despesas: pd.DataFrame | None) -> int:
        """Scoring rule for monthly performance."""

        resumo = self.resumo_mensal(df_receitas, df_despesas)
        score = 0

        if resumo["margem_%"] >= 40:
            score += 30
        elif resumo["margem_%"] >= 25:
            score += 20
        else:
            score += 10

        if resumo["%_meta_batida"] >= 80:
            score += 30
        elif resumo["%_meta_batida"] >= 50:
            score += 20
        else:
            score += 10

        if resumo["receita_por_km"] >= 3:
            score += 20
        else:
            score += 10

        if resumo["lucro"] > 0:
            score += 20

        return int(score)

    def analise_consistencia(
        self,
        df_receitas: pd.DataFrame | None,
        start_date=None,
        end_date=None,
        meta: float = 300.0,
    ) -> dict[str, str | int | bool]:
        """Consistency analytics for work/absence and meta hit/miss streaks."""

        calendar = self._build_daily_calendar(df_receitas, start_date=start_date, end_date=end_date, meta=meta)
        if calendar.empty:
            return {
                "longest_work_streak": 0,
                "current_work_streak": 0,
                "new_work_streak_record": False,
                "longest_absence_streak": 0,
                "current_absence_streak": 0,
                "new_absence_streak_record": False,
                "longest_meta_hit_streak": 0,
                "current_meta_hit_streak": 0,
                "new_meta_hit_streak_record": False,
                "longest_meta_miss_streak": 0,
                "current_meta_miss_streak": 0,
                "new_meta_miss_streak_record": False,
                "most_absent_weekday": "-",
                "most_absent_weekday_count": 0,
                "most_worked_weekday": "-",
                "most_worked_weekday_count": 0,
            }

        worked = self._streak_info(calendar["worked"])
        absent = self._streak_info(calendar["absent"])
        meta_hit = self._streak_info(calendar["meta_hit"])
        meta_miss = self._streak_info(calendar["meta_miss"])
        absent_weekday, absent_count = self._top_weekday(calendar, "absent")
        worked_weekday, worked_count = self._top_weekday(calendar, "worked")

        return {
            "longest_work_streak": int(worked["longest"]),
            "current_work_streak": int(worked["current"]),
            "new_work_streak_record": bool(worked["new_record"]),
            "longest_absence_streak": int(absent["longest"]),
            "current_absence_streak": int(absent["current"]),
            "new_absence_streak_record": bool(absent["new_record"]),
            "longest_meta_hit_streak": int(meta_hit["longest"]),
            "current_meta_hit_streak": int(meta_hit["current"]),
            "new_meta_hit_streak_record": bool(meta_hit["new_record"]),
            "longest_meta_miss_streak": int(meta_miss["longest"]),
            "current_meta_miss_streak": int(meta_miss["current"]),
            "new_meta_miss_streak_record": bool(meta_miss["new_record"]),
            "most_absent_weekday": absent_weekday,
            "most_absent_weekday_count": int(absent_count),
            "most_worked_weekday": worked_weekday,
            "most_worked_weekday_count": int(worked_count),
        }
