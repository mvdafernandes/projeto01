"""Business metrics service with safe dataframe operations."""

from __future__ import annotations

import pandas as pd

from domain.models import ResumoMensal
from domain.validators import parse_datetime_column, safe_divide


class MetricsService:
    """Pure metrics calculations over input dataframes."""

    RECEITAS_COLS = ["id", "data", "valor", "km", "tempo trabalhado", "observacao"]
    DESPESAS_COLS = ["id", "data", "categoria", "valor", "observacao"]

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
