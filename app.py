import os

import streamlit as st
from streamlit_option_menu import option_menu

from sections.dashboard import render_dashboard
from sections.management import render_section
from sections.storage import render_storage

DIRS = {
    "Grupo Entrega Real": "data/group-delivered",
    "Referencias Pendientes": "data/pending",
    "Unidades cortadas": "data/cut",
    "WIP": "data/wip",
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

st.set_page_config(layout="wide", page_title="Dash")

with st.sidebar:
    # Título fuera del componente
    st.markdown("# Dash")

    page = option_menu(
        menu_title=None,  # Elimina la caja de título interna
        options=[
            "Dashboard",
            "Grupo Entrega Real",
            "Referencias Pendientes",
            "Unidades cortadas",
            "WIP",
            "Gestión de Archivos",
        ],
        icons=["chart-bar", "truck", "list-check", "scissors", "gear", "folder2-open"],
        default_index=0,
        styles={
            "container": {
                "padding": "0!important",
                "background-color": "transparent",
                "border": "none",
            },
            "icon": {"color": "white", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "0px",
                "border-radius": "8px",
                "--hover-color": "#333",
            },
            "nav-link-selected": {"background-color": "#FF4B4B"},
        },
    )

if page == "Dashboard":
    render_dashboard(DIRS)
elif page == "Gestión de Archivos":
    render_storage(DIRS)
else:
    render_section(page, DIRS)
