import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_option_menu import option_menu

# --- SETUP ---
DIRS = {
    "Grupo Entrega Real": "data/group-delivered",
    "Referencias Pendientes": "data/pending",
    "Unidades cortadas": "data/cut",
    "WIP": "data/wip",
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

st.set_page_config(layout="wide", page_title="Control Tower 2026")


# --- ETL LOGIC ---
def normalize_cols(df):
    # Strip + Upper + Regex cleanup
    df.columns = [re.sub(r"\s+", " ", str(c).strip().upper()) for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^UNNAMED")]
    return df.loc[:, ~df.columns.duplicated()]


def clean_data_values(df, filename):
    # Inject MARCA from filename
    if "MARCA" not in df.columns:
        if "STOP" in filename.upper():
            df["MARCA"] = "STOP"
        elif "YOYO" in filename.upper():
            df["MARCA"] = "YOYO"
        else:
            df["MARCA"] = "DESCONOCIDO"

    # Normalize cell text
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(
                lambda x: (
                    re.sub(r"^\d+\s*-\s*", "", str(x)).strip().upper()
                    if pd.notna(x)
                    else x
                )
            )

    # Clean numbers (50.0000 -> 50)
    num_cols = [
        "CANT. PLANEADA",
        "CANT. ORDENADA",
        "CANT. COMPLETA",
        "CANT. PENDIENTE",
        "CANT.COMPLETA",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(0).astype(int)

    # Dates
    date_cols = ["FECHA TERMINACIÓN", "FECHA CREACIÓN", "FECHA APROBACIÓN"]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
    return df


def get_consolidated_df(path):
    files = [f for f in os.listdir(path) if f.endswith(".csv")]
    if not files:
        return None
    all_dfs = []
    for f in files:
        df = pd.read_csv(os.path.join(path, f))
        df = normalize_cols(df)
        df = clean_data_values(df, f)
        all_dfs.append(df)
    final = pd.concat(all_dfs, axis=0, ignore_index=True)
    return final.loc[:, ~final.columns.duplicated()]


# --- SIDEBAR ---
with st.sidebar:
    page = option_menu(
        "Control Tower",
        [
            "Dashboard",
            "Grupo Entrega Real",
            "Referencias Pendientes",
            "Unidades cortadas",
            "WIP",
        ],
        icons=["chart-bar", "truck", "list-check", "scissors", "gear"],
        default_index=0,
    )

# --- DASHBOARD PAGE ---
if page == "Dashboard":
    st.title("📊 Dashboard de Control")
    df_e = get_consolidated_df(DIRS["Grupo Entrega Real"])
    df_p = get_consolidated_df(DIRS["Referencias Pendientes"])

    if df_e is not None:
        # Filters
        marcas = df_e["MARCA"].unique()
        sel_marca = st.sidebar.multiselect("Filtrar Marca", marcas, default=marcas)
        df_f = df_e[df_e["MARCA"].isin(sel_marca)]

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        total_ord = df_f["CANT. ORDENADA"].sum()
        total_com = df_f["CANT. COMPLETA"].sum()
        c1.metric(
            "Cumplimiento %",
            f"{(total_com / total_ord * 100 if total_ord > 0 else 0):.1f}%",
        )
        c2.metric("Pendiente Total", f"{df_f['CANT. PENDIENTE'].sum():,}")
        c3.metric("MOPs Activos", len(df_f["O.P. NÚMERO"].unique()))
        c4.metric("Backlog Pendiente", len(df_p) if df_p is not None else 0)

        # Charts
        col_l, col_r = st.columns(2)
        fig1 = px.bar(
            df_f.groupby("MES")[["CANT. ORDENADA", "CANT. COMPLETA"]]
            .sum()
            .reset_index(),
            x="MES",
            y=["CANT. ORDENADA", "CANT. COMPLETA"],
            barmode="group",
            title="Ordenado vs Entregado",
        )
        col_l.plotly_chart(fig1, use_container_width=True)

        fig2 = px.pie(
            df_f,
            values="CANT. COMPLETA",
            names="MARCA",
            title="Distribución por Marca",
            hole=0.4,
        )
        col_r.plotly_chart(fig2, use_container_width=True)

        st.subheader("⚠️ Top 10 Críticos")
        st.dataframe(
            df_f.sort_values("CANT. PENDIENTE", ascending=False).head(10),
            use_container_width=True,
        )
    else:
        st.warning("Cargar datos en secciones para activar Dashboard.")

# --- SECTION PAGES ---
else:
    st.title(page)
    path = DIRS[page]

    # State management
    state_key = f"df_cache_{page}"
    if state_key not in st.session_state:
        st.session_state[state_key] = get_consolidated_df(path)

    up_col, view_col = st.columns([1, 3])
    with up_col:
        st.subheader("Subir XLS")
        files = st.file_uploader(
            "Arrastre archivos",
            type=["xls", "xlsx"],
            accept_multiple_files=True,
            key=f"u_{page}",
        )
        if st.button("Procesar y Guardar"):
            for f in files:
                df_raw = pd.read_excel(f)
                df_raw = normalize_cols(df_raw)
                # Forward Fill Logic
                excl = [
                    "MES ADELANTO",
                    "GRUPO DE ENTREGA",
                    "LINEA",
                    "TIPO DE ABASTECIMIENTO",
                ]
                fill_cols = [c for c in df_raw.columns if c not in excl]
                df_raw[fill_cols] = df_raw[fill_cols].ffill()
                # Save
                name = f.name.rsplit(".", 1)[0] + ".csv"
                df_raw.to_csv(os.path.join(path, name), index=False)
            st.session_state[state_key] = get_consolidated_df(path)
            st.rerun()

        if st.button("Actualizar Vista ↻"):
            st.session_state[state_key] = get_consolidated_df(path)
            st.rerun()

    with view_col:
        st.subheader("Vista de Datos")
        if st.session_state[state_key] is not None:
            st.dataframe(st.session_state[state_key], use_container_width=True)
        else:
            st.info("Directorio vacío.")
