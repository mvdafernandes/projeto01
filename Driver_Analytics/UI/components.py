# UI/components.py

import streamlit as st


def titulo_secao(texto):
    st.subheader(texto)
    st.divider()


def card_kpi(titulo, valor, subtitulo=None):
    st.markdown(
        f"""
        <div style="
            background-color:#1C1F26;
            padding:20px;
            border-radius:12px;
        ">
            <div style="font-size:14px; color:gray;">
                {titulo}
            </div>
            <div style="font-size:26px; font-weight:600;">
                {valor}
            </div>
            <div style="font-size:12px; color:#888;">
                {subtitulo if subtitulo else ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
