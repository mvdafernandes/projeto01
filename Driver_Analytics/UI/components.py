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
          --card-bg-dark: #172554;
          --card-bg-light: #eff6ff;
          --text-dark: #0f172a;
          --text-light: #f9fafb;
          --muted-light: #cbd5e1;
          --muted-dark: #475569;
          --brand-1: #0ea5e9;
          --brand-2: #2563eb;
          --brand-3: #22c55e;
        }

        .da-hero {
          border: 1px solid rgba(56, 189, 248, 0.25);
          border-radius: 18px;
          padding: 18px 20px;
          margin: 6px 0 18px 0;
          background:
            radial-gradient(circle at 10% 10%, rgba(34, 197, 94, 0.18), transparent 45%),
            radial-gradient(circle at 85% 30%, rgba(14, 165, 233, 0.22), transparent 40%),
            linear-gradient(135deg, #0f172a 0%, #1e3a8a 52%, #0f172a 100%);
          color: #f8fafc;
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 16px;
          align-items: center;
        }

        .da-hero__title {
          font-size: 24px;
          font-weight: 800;
          line-height: 1.2;
          margin-bottom: 4px;
        }

        .da-hero__meta {
          font-size: 13px;
          color: #cbd5e1;
        }

        .da-hero__badge {
          display: inline-block;
          margin-top: 10px;
          padding: 4px 10px;
          border-radius: 999px;
          background: rgba(14, 165, 233, 0.2);
          border: 1px solid rgba(125, 211, 252, 0.45);
          font-size: 12px;
          color: #e0f2fe;
        }

        .da-hero svg {
          width: 140px;
          height: 72px;
          opacity: 0.95;
        }

        .da-card {
          border: 1px solid rgba(100, 116, 139, 0.35);
          border-radius: 14px;
          padding: 14px 16px;
          min-height: 112px;
          background: linear-gradient(170deg, #1e3a8a, #0f172a);
          color: var(--text-light);
          box-shadow: 0 10px 24px rgba(2, 6, 23, 0.22);
          transition: transform .16s ease, box-shadow .16s ease;
        }

        .da-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 14px 28px rgba(2, 6, 23, 0.3);
        }

        .da-card__head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }

        .da-card__title {
          font-size: 13px;
          color: var(--muted-light);
          margin-bottom: 6px;
        }

        .da-card__icon {
          width: 24px;
          height: 24px;
          border-radius: 999px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          background: rgba(148, 163, 184, 0.24);
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
          .da-hero {
            grid-template-columns: 1fr;
          }
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
          .da-hero {
            background:
              radial-gradient(circle at 10% 10%, rgba(34, 197, 94, 0.16), transparent 45%),
              radial-gradient(circle at 85% 30%, rgba(14, 165, 233, 0.18), transparent 40%),
              linear-gradient(140deg, #e0f2fe 0%, #dbeafe 55%, #ecfeff 100%);
            color: #0f172a;
            border: 1px solid rgba(14, 116, 144, 0.2);
          }
          .da-hero__meta {
            color: #334155;
          }
          .da-hero__badge {
            background: rgba(2, 132, 199, 0.12);
            border: 1px solid rgba(2, 132, 199, 0.25);
            color: #075985;
          }
          .da-card {
            background: linear-gradient(180deg, #f8fafc, #e2e8f0);
            color: var(--text-dark);
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
          }
          .da-card__title,
          .da-card__subtitle {
            color: var(--muted-dark);
          }
          .da-card__icon {
            background: rgba(14, 116, 144, 0.12);
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


def render_hero_banner(usuario: str, secao: str) -> None:
    user = str(usuario or "").strip() or "Convidado"
    section = str(secao or "Dashboard").strip()
    st.markdown(
        f"""
        <div class="da-hero">
            <div>
                <div class="da-hero__title">Driver Analytics</div>
                <div class="da-hero__meta">Acompanhe desempenho, custos e investimentos em um único painel.</div>
                <div class="da-hero__badge">Usuário: {user} | Seção: {section}</div>
            </div>
            <svg viewBox="0 0 240 120" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stop-color="#22d3ee"/>
                  <stop offset="100%" stop-color="#3b82f6"/>
                </linearGradient>
              </defs>
              <path d="M20 84c10-26 26-40 53-40h69c21 0 34 9 44 26l9 14h-20c-3-9-10-14-20-14H76c-10 0-18 5-21 14H20z" fill="url(#g1)" opacity="0.95"/>
              <circle cx="74" cy="86" r="13" fill="#0f172a"/><circle cx="74" cy="86" r="6" fill="#e2e8f0"/>
              <circle cx="157" cy="86" r="13" fill="#0f172a"/><circle cx="157" cy="86" r="6" fill="#e2e8f0"/>
              <path d="M90 54h42l18 16H76l14-16z" fill="#e0f2fe" opacity="0.9"/>
            </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kpi_icon_for_title(titulo: str) -> str:
    t = str(titulo or "").lower()
    if "receita" in t:
        return "💵"
    if "despesa" in t:
        return "🧾"
    if "lucro" in t:
        return "📈"
    if "meta" in t:
        return "🎯"
    if "dia" in t:
        return "📅"
    if "km" in t:
        return "🛣️"
    if "patrim" in t or "aporte" in t or "invest" in t:
        return "🏦"
    if "margem" in t:
        return "📊"
    return "•"


def render_kpi(titulo: str, valor: str | int | float, subtitulo: str | None = None) -> None:
    """Render standardized KPI card with improved contrast."""

    st.markdown(
        f"""
        <div class="da-card">
            <div class="da-card__head">
              <div class="da-card__title">{titulo}</div>
              <span class="da-card__icon">{_kpi_icon_for_title(titulo)}</span>
            </div>
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
