"""Reusable UI components for responsive Streamlit pages."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def titulo_secao(texto: str) -> None:
    """Render section heading and visual separator."""

    st.subheader(texto)
    st.divider()


def format_currency(value: float) -> str:
    """Format numeric value as BRL."""

    return f"R$ {float(value):,.2f}"


def format_percent(value: float) -> str:
    """Format numeric value as percentage."""

    return f"{float(value):.1f}%"


def show_empty_data(message: str = "Sem dados para mostrar.") -> None:
    """Render empty-state info message."""

    st.info(message)


def render_kpi(titulo: str, valor: str | int | float, subtitulo: str | None = None) -> None:
    """Render standardized KPI card."""

    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(120, 120, 120, 0.25);
            border-radius: 12px;
            padding: 14px 16px;
            background: linear-gradient(180deg, rgba(28,31,38,0.95), rgba(28,31,38,0.85));
            min-height: 108px;
        ">
            <div style="font-size:13px; color:#a5adba; margin-bottom:8px;">{titulo}</div>
            <div style="font-size:26px; font-weight:700; line-height:1.1;">{valor}</div>
            <div style="font-size:12px; color:#8f98a8; margin-top:8px;">{subtitulo or ''}</div>
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
