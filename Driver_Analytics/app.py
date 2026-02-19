"""Driver Analytics Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from core.auth import get_logged_username, login_required, render_logout_button
from core.config import get_settings
from core.database import init_sqlite_schema
from core.database import get_supabase_client
from UI.cadastros_ui import pagina_cadastros
from UI.components import aplicar_estilo_global, render_hero_banner
from UI.dashboard_ui import pagina_dashboard
from UI.despesas_ui import pagina_despesas
from UI.investimentos_ui import pagina_investimentos
from UI.receitas_ui import pagina_receitas


st.set_page_config(page_title="Driver Analytics", page_icon="🚗", layout="wide")
aplicar_estilo_global()

init_sqlite_schema()
login_required()

settings = get_settings()
try:
    if settings.app_db_mode == "local":
        st.warning("Rodando em modo local (sem sync com Supabase).")
    elif settings.app_db_mode == "auto" and get_supabase_client() is None:
        st.warning("Rodando em modo local (sem sync com Supabase).")
except Exception:
    # Never fail UI bootstrap because of connectivity/mode diagnostics.
    st.warning("Aviso de ambiente indisponível no momento (seguindo com fallback local quando possível).")

username = get_logged_username()
if username:
    st.sidebar.markdown(f"**Usuário logado:** `{username}`")

render_logout_button()

menu = st.sidebar.radio("Navegação", ["Dashboard", "Cadastros", "Receitas", "Despesas", "Investimentos"])
render_hero_banner(username, menu)

if menu == "Cadastros":
    st.sidebar.success("CRUD centralizado em Cadastros")

if menu == "Dashboard":
    pagina_dashboard()
elif menu == "Cadastros":
    pagina_cadastros()
elif menu == "Receitas":
    pagina_receitas()
elif menu == "Despesas":
    pagina_despesas()
elif menu == "Investimentos":
    pagina_investimentos()
