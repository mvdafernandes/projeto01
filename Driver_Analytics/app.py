"""Driver Analytics Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from core.auth import login_required, render_logout_button
from core.database import init_sqlite_schema
from UI.cadastros_ui import pagina_cadastros
from UI.components import aplicar_estilo_global
from UI.dashboard_ui import pagina_dashboard
from UI.despesas_ui import pagina_despesas
from UI.investimentos_ui import pagina_investimentos
from UI.receitas_ui import pagina_receitas


st.set_page_config(page_title="Driver Analytics", page_icon="🚗", layout="wide")
st.title("🚗 Driver Analytics")
aplicar_estilo_global()

login_required()
render_logout_button()
init_sqlite_schema()

menu = st.sidebar.radio("Navegação", ["Dashboard", "Cadastros", "Receitas", "Despesas", "Investimentos"])

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
