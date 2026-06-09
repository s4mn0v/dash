import os
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


# --- ETL HELPERS ---
def base_clean(df):
    df.columns = [re.sub(r"\s+", " ", str(c).strip().upper()) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def clean_txt(val):
    if pd.isna(val):
        return val
    # Remove "001 - " prefix and trim
    return re.sub(r"^\d+\s*-\s*", "", str(val)).strip().upper()


# --- SPECIFIC ETL LOGIC ---
def etl_entrega(df, fname):
    df = base_clean(df)
    # Homologate Color col
    target_cols = ["DESC. EXTENSIÓN 1", "DETALLE EXT. 1"]
    for c in target_cols:
        if c in df.columns:
            df = df.rename(columns={c: "COLOR_NOMBRE"})

    # Trim key cols
    for c in ["REFERENCIA", "GRUPO DE ENTREGA"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # Inject Marca
    if "STOP" in fname.upper():
        df["MARCA"] = "STOP"
    else:
        df["MARCA"] = "YOYO"

    # Numeric conversion
    for c in ["CANT. PLANEADA", "CANT. COMPLETA", "CANT. PENDIENTE"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Estado Pedido
    def calc_estado(row):
        if row.get("CANT. PENDIENTE", 0) == 0:
            return "TERMINADO"
        if row.get("CANT. COMPLETA", 0) > 0:
            return "EN PROCESO"
        return "SIN INICIAR"

    df["ESTADO_PEDIDO"] = df.apply(calc_estado, axis=1)
    return df


def etl_pendientes(df):
    df = base_clean(df)
    # Clean MES (007 - JULIO → JULIO)
    if "MES" in df.columns:
        df["MES"] = df["MES"].apply(clean_txt)

    # Clean Marca
    if "MARCA" in df.columns:
        df["MARCA"] = df["MARCA"].apply(clean_txt)

    # Drop empty rows (require Referencia)
    df = df.dropna(subset=["REFERENCIA"])
    return df


def etl_cortadas(df):
    df = base_clean(df)
    # Date format
    if "FECHA CREACIÓN" in df.columns:
        df["FECHA CREACIÓN"] = pd.to_datetime(
            df["FECHA CREACIÓN"], errors="coerce", dayfirst=True
        )

    # Trim Tallas
    if "DESC. DETALLE EXT. 2" in df.columns:
        df["DESC. DETALLE EXT. 2"] = df["DESC. DETALLE EXT. 2"].astype(str).str.strip()

    return df


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

    if df_e is not None:
        # Slicers
        marcas = df_e["MARCA"].unique()
        meses = df_e["MES"].unique() if "MES" in df_e.columns else []

        sel_marca = st.sidebar.multiselect("Marca", marcas, default=marcas)
        sel_mes = st.sidebar.multiselect("Mes", meses, default=meses)

        df_f = df_e[df_e["MARCA"].isin(sel_marca)]
        if meses:
            df_f = df_f[df_f["MES"].isin(sel_mes)]

        # KPI Gauge
        total_ord = df_f["CANT. ORDENADA"].sum()
        total_com = df_f["CANT. COMPLETA"].sum()
        pct = (total_com / total_ord * 100) if total_ord > 0 else 0

        fig_g = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=pct,
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#00CC96"}},
                title={"text": "Cumplimiento Total %"},
            )
        )
        st.plotly_chart(fig_g, use_container_width=True)

        # Charts
        c1, c2 = st.columns(2)

        # Bars: Ord vs Com por Colección
        if "COLECCIÓN" in df_f.columns:
            fig_b = px.bar(
                df_f.groupby("COLECCIÓN")[["CANT. ORDENADA", "CANT. COMPLETA"]]
                .sum()
                .reset_index(),
                x="COLECCIÓN",
                y=["CANT. ORDENADA", "CANT. COMPLETA"],
                barmode="group",
            )
            c1.plotly_chart(fig_b)

        # Table: Alerta Críticos (Fecha vencida + Pendiente)
        st.subheader("⚠️ Top 10 Críticos (Vencidos)")
        now = pd.Timestamp.now()
        if "FECHA TERMINACIÓN" in df_f.columns:
            df_crit = df_f[
                (df_f["FECHA TERMINACIÓN"] < now) & (df_f["CANT. PENDIENTE"] > 0)
            ]
            st.dataframe(
                df_crit.sort_values("CANT. PENDIENTE", ascending=False).head(10)
            )

    else:
        st.warning("No hay datos.")

# --- SECTION PAGES ---
else:
    st.title(page)
    path = DIRS[page]

    state_key = f"df_cache_{page}"
    if state_key not in st.session_state:
        st.session_state[state_key] = get_consolidated_df(path)

    df_view = st.session_state[state_key]

    if page == "Grupo Entrega Real" and df_view is not None:
        # 1. SLICERS
        st.subheader("Filtros")
        c1, c2, c3, c4 = st.columns(4)

        f_marca = c1.multiselect("Marca", df_view["MARCA"].unique())
        f_mes = c2.multiselect(
            "Mes", df_view["MES"].unique() if "MES" in df_view else []
        )
        f_coll = c3.multiselect(
            "Colección", df_view["COLECCION"].unique() if "COLECCION" in df_view else []
        )
        f_grupo = c4.multiselect(
            "Grupo Entrega",
            df_view["GRUPO DE ENTREGA"].unique()
            if "GRUPO DE ENTREGA" in df_view
            else [],
        )

        # Filter Logic
        mask = pd.Series(True, index=df_view.index)
        if f_marca:
            mask &= df_view["MARCA"].isin(f_marca)
        if f_mes:
            mask &= df_view["MES"].isin(f_mes)
        if f_coll:
            mask &= df_view["COLECCIÓN"].isin(f_coll)
        if f_grupo:
            mask &= df_view["GRUPO DE ENTREGA"].isin(f_grupo)
        df_f = df_view[mask]
        st.divider()

        # 2. CHARTS
        if "COLECCION" in df_f.columns and not df_f.empty:
            fig_bar = px.bar(
                df_f.groupby("COLECCION")[["CANT. ORDENADA", "CANT. COMPLETA"]]
                .sum()
                .reset_index(),
                x="COLECCION",
                y=["CANT. ORDENADA", "CANT. COMPLETA"],
                barmode="group",
                title="Ordenado vs Completo por Coleccion",
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("Columna 'COLECCIÓN' no encontrada o datos vacíos.")
            st.write("Columnas detectadas:", list(df_f.columns))  # Debug

        # 3. ALERTS
        st.subheader("⚠️ O.P. Críticas (Vencidas + Pendientes)")
        if "FECHA TERMINACIÓN" in df_f.columns:
            today = pd.Timestamp.now().normalize()
            df_crit = (
                df_f[
                    (df_f["FECHA TERMINACIÓN"] < today) & (df_f["CANT. PENDIENTE"] > 0)
                ]
                .sort_values("CANT. PENDIENTE", ascending=False)
                .head(10)
            )
            st.dataframe(df_crit, use_container_width=True)
            st.divider()

    up_col, view_col = st.columns([1, 3])
    with up_col:
        st.subheader("Subir XLS")
        files = st.file_uploader(
            "Archivos",
            type=["xls", "xlsx"],
            accept_multiple_files=True,
            key=f"u_{page}",
        )

        if st.button("Procesar y Guardar"):
            for f in files:
                df_raw = pd.read_excel(f)

                # 1. Aplicar Forward Fill (Base)
                excl = [
                    "MES ADELANTO",
                    "GRUPO DE ENTREGA",
                    "LINEA",
                    "TIPO DE ABASTECIMIENTO",
                ]
                fill_cols = [c for c in df_raw.columns if c not in excl]
                df_raw[fill_cols] = df_raw[fill_cols].ffill()

                # 2. Aplicar Lógica Específica según la página
                if page == "Grupo Entrega Real":
                    df_raw = etl_entrega(df_raw, f.name)
                elif page == "Referencias Pendientes":
                    df_raw = etl_pendientes(df_raw)
                elif page == "Unidades cortadas":
                    df_raw = etl_cortadas(df_raw)
                else:
                    df_raw = normalize_cols(df_raw)

                # 3. Guardar
                name = f.name.rsplit(".", 1)[0] + ".csv"
                df_raw.to_csv(os.path.join(path, name), index=False)

            st.session_state[state_key] = get_consolidated_df(path)
            st.rerun()

    with view_col:
        st.subheader("Vista de Datos")
        if st.session_state[state_key] is not None:
            st.dataframe(st.session_state[state_key], use_container_width=True)
        else:
            st.info("Directorio vacío.")
