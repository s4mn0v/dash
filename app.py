import os

import streamlit as st
from streamlit_option_menu import option_menu

from sections.dashboard import render_dashboard
from sections.management import render_section

DIRS = {
    "Grupo Entrega Real": "data/group-delivered",
    "Referencias Pendientes": "data/pending",
    "Unidades cortadas": "data/cut",
    "WIP": "data/wip",
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

st.set_page_config(layout="wide", page_title="Control Tower 2026")

with st.sidebar:
    page = option_menu(
        "Control Tower",
        ["Dashboard"] + list(DIRS.keys()),
        icons=["chart-bar", "truck", "list-check", "scissors", "gear"],
        default_index=0,
    )

if page == "Dashboard":
    render_dashboard(DIRS)
else:
    render_section(page, DIRS)
