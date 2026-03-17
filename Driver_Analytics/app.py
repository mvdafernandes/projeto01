"""Driver Analytics Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from core.auth import get_logged_user_id, get_logged_username, login_required, render_logout_button
from core.config import get_settings
from core.database import get_supabase_client
from UI.components import aplicar_estilo_global, render_hero_banner


st.set_page_config(page_title="Driver Analytics", page_icon="🚗", layout="wide")
aplicar_estilo_global()

login_required()

settings = get_settings()
try:
    if settings.app_db_mode != "remote":
        st.error("Segurança: defina APP_DB_MODE=remote para evitar fallback local de autenticação.")
        st.stop()
    if get_supabase_client() is None:
        st.error("Falha ao conectar no Supabase. Configure SUPABASE_URL/SUPABASE_KEY válidos.")
        st.stop()
except Exception:
    st.error("Não foi possível validar a conexão com Supabase remoto.")
    st.stop()

username = get_logged_username()
if username:
    user_id = get_logged_user_id()
    st.sidebar.markdown(f"**Usuário logado:** `{username}` | id `{user_id}`")
st.sidebar.caption("build 1985d35")

render_logout_button()

menu = st.sidebar.radio("Navegação", ["Dashboard", "Jornada", "Receitas", "Despesas", "Investimentos", "Backup"])
render_hero_banner(username, menu)

if menu == "Backup":
    st.sidebar.success("Exporte e restaure seus dados com segurança")

if menu == "Dashboard":
    from UI.dashboard_ui import pagina_dashboard

    pagina_dashboard()
elif menu == "Jornada":
    from UI.jornada_ui import pagina_jornada

    pagina_jornada()
elif menu == "Backup":
    from UI.cadastros_ui import pagina_backup

    pagina_backup()
elif menu == "Receitas":
    from UI.receitas_ui import pagina_receitas

    pagina_receitas()
elif menu == "Despesas":
    from UI.despesas_ui import pagina_despesas

    pagina_despesas()
elif menu == "Investimentos":
    from UI.investimentos_ui import pagina_investimentos

    pagina_investimentos()
