"""Reusable UI components for responsive Streamlit pages."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def aplicar_estilo_global() -> None:
    """Inject global CSS with better contrast and mobile readability."""

    st.markdown(
        """
        <style>
        :root {
          --card-bg-dark: #1f2937;
          --card-bg-light: #f3f4f6;
          --text-dark: #111827;
          --text-light: #f9fafb;
          --muted-light: #d1d5db;
          --muted-dark: #4b5563;
        }

        .da-card {
          border: 1px solid rgba(100, 116, 139, 0.35);
          border-radius: 14px;
          padding: 16px;
          min-height: 112px;
          background: linear-gradient(180deg, #1f2937, #111827);
          color: var(--text-light);
        }

        .da-card__title {
          font-size: 13px;
          color: var(--muted-light);
          margin-bottom: 8px;
        }

        .da-card__value {
          font-size: 26px;
          font-weight: 700;
          line-height: 1.1;
        }

        .da-card__subtitle {
          font-size: 12px;
          color: var(--muted-light);
          margin-top: 8px;
        }

        @media (max-width: 768px) {
          .da-card {
            padding: 18px;
            min-height: 124px;
          }
          .da-card__title {
            font-size: 14px;
          }
          .da-card__value {
            font-size: 28px;
          }
          .da-card__subtitle {
            font-size: 13px;
          }
        }

        @media (prefers-color-scheme: light) {
          .da-card {
            background: linear-gradient(180deg, #f9fafb, #e5e7eb);
            color: var(--text-dark);
          }
          .da-card__title,
          .da-card__subtitle {
            color: var(--muted-dark);
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def titulo_secao(texto: str) -> None:
    """Render section heading and visual separator."""

    st.subheader(texto)
    st.divider()


def formatar_moeda(valor: float) -> str:
    """Format number using Brazilian currency style: R$ 1.234,56."""

    numero = float(valor)
    raw = f"{numero:,.2f}"
    br = raw.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {br}"


def format_currency(value: float) -> str:
    """Backward-compatible alias for currency formatting."""

    return formatar_moeda(value)


def format_percent(value: float) -> str:
    """Format numeric value as percentage."""

    return f"{float(value):.1f}%"


def show_empty_data(message: str = "Sem dados para mostrar.") -> None:
    """Render empty-state info message."""

    st.info(message)


def render_kpi(titulo: str, valor: str | int | float, subtitulo: str | None = None) -> None:
    """Render standardized KPI card with improved contrast."""

    st.markdown(
        f"""
        <div class="da-card">
            <div class="da-card__title">{titulo}</div>
            <div class="da-card__value">{valor}</div>
            <div class="da-card__subtitle">{subtitulo or ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_graph(fig: go.Figure, height: int = 360, show_legend: bool = False) -> None:
    """Render Plotly graph with mobile-friendly defaults."""

    fig.update_layout(
        height=height,
        showlegend=show_legend,
        margin=dict(l=8, r=8, t=30, b=8),
        xaxis_title=None,
        yaxis_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_table_preview(
    df: pd.DataFrame,
    columns: list[str],
    key_prefix: str,
    empty_message: str = "Sem dados para mostrar.",
    rows: int = 8,
) -> None:
    """Render compact table preview and optional full table."""

    if df is None or df.empty:
        show_empty_data(empty_message)
        return

    safe_cols = [col for col in columns if col in df.columns]
    if not safe_cols:
        show_empty_data(empty_message)
        return

    preview = df.loc[:, safe_cols].head(rows).copy()
    st.dataframe(preview, width="stretch", hide_index=True)

    if st.button("Ver tabela completa", key=f"{key_prefix}_btn"):
        st.dataframe(df, width="stretch", hide_index=True)


# Backward compatibility alias
card_kpi = render_kpi
