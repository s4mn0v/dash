import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from core.etl import get_consolidated_df, normalize_cols
from core.processor import etl_cortadas, etl_entrega, etl_pendientes


def render_section(page, DIRS):
    st.title(page)
    path = DIRS[page]
    key = f"df_cache_{page}"
    if key not in st.session_state:
        st.session_state[key] = get_consolidated_df(path)
    df_v = st.session_state[key]

    if page == "Grupo Entrega Real" and df_v is not None:
        st.subheader("Filtros")
        c1, c2, c3, c4 = st.columns(4)

        # Helper limpieza filtros
        def get_opts(series, label):
            s = (
                series.astype(str)
                .str.strip()
                .replace(["nan", "None", "", "NaN", "<NA>"], pd.NA)
            )
            # Quitar prefijos 001- 002- para vista limpia
            s = s.apply(
                lambda x: re.sub(r"^\d+\s*-\s*", "", str(x)) if pd.notna(x) else x
            )
            return s.fillna(label)

        # Preparar Series limpias para matching
        s_marca = get_opts(df_v["MARCA"], "[Sin Marca]")
        s_mes = get_opts(df_v["MES"], "[Sin Mes]") if "MES" in df_v else pd.Series()

        c_col = (
            "COLECCIÓN"
            if "COLECCIÓN" in df_v
            else ("COLECCION" if "COLECCION" in df_v else None)
        )
        s_coll = get_opts(df_v[c_col], "[Sin Coleccion]") if c_col else pd.Series()

        s_grp = (
            get_opts(df_v["GRUPO DE ENTREGA"], "[Sin Grupo Entrega]")
            if "GRUPO DE ENTREGA" in df_v
            else pd.Series()
        )

        # Render multiselects con sorted unique
        f_marca = c1.multiselect("Marca", sorted(s_marca.unique().tolist()))
        f_mes = (
            c2.multiselect("Mes", sorted(s_mes.unique().tolist()))
            if not s_mes.empty
            else []
        )
        f_coll = (
            c3.multiselect("Colección", sorted(s_coll.unique().tolist()))
            if not s_coll.empty
            else []
        )
        f_grupo = (
            c4.multiselect("Grupo Entrega", sorted(s_grp.unique().tolist()))
            if not s_grp.empty
            else []
        )

        mask = pd.Series(True, index=df_v.index)
        if f_marca:
            mask &= s_marca.isin(f_marca)
        if f_mes:
            mask &= s_mes.isin(f_mes)
        if f_coll:
            mask &= s_coll.isin(f_coll)
        if f_grupo:
            mask &= s_grp.isin(f_grupo)
        df_f = df_v[mask]

        st.divider()
        if c_col and not df_f.empty:
            st.plotly_chart(
                px.bar(
                    df_f.groupby(c_col)[["CANT. ORDENADA", "CANT. COMPLETA"]]
                    .sum()
                    .reset_index(),
                    x=c_col,
                    y=["CANT. ORDENADA", "CANT. COMPLETA"],
                    barmode="group",
                    title="Ordenado vs Completo",
                ),
                use_container_width=True,
            )

        st.subheader("⚠️ O.P. Críticas")
        if "FECHA TERMINACIÓN" in df_f.columns:
            df_crit = df_f[
                (df_f["FECHA TERMINACIÓN"] < pd.Timestamp.now().normalize())
                & (df_f["CANT. PENDIENTE"] > 0)
            ]
            st.dataframe(
                df_crit.sort_values("CANT. PENDIENTE", ascending=False).head(10),
                use_container_width=True,
            )
        st.divider()

    up, view = st.columns([1, 3])
    with up:
        st.subheader("Subir XLS")
        files = st.file_uploader(
            "Archivos",
            type=["xls", "xlsx"],
            accept_multiple_files=True,
            key=f"u_{page}",
        )
        if st.button("Procesar y Guardar"):
            for f in files:
                df = pd.read_excel(f)
                excl = [
                    "MES ADELANTO",
                    "GRUPO DE ENTREGA",
                    "LINEA",
                    "TIPO DE ABASTECIMIENTO",
                ]
                df[[c for c in df.columns if c not in excl]] = df[
                    [c for c in df.columns if c not in excl]
                ].ffill()
                if page == "Grupo Entrega Real":
                    df = etl_entrega(df, f.name)
                elif page == "Referencias Pendientes":
                    df = etl_pendientes(df)
                elif page == "Unidades cortadas":
                    df = etl_cortadas(df)
                else:
                    df = normalize_cols(df)
                df.to_csv(
                    os.path.join(path, f.name.rsplit(".", 1)[0] + ".csv"), index=False
                )
            st.session_state[key] = get_consolidated_df(path)
            st.rerun()
    with view:
        st.subheader("Vista de Datos")
        if st.session_state[key] is not None:
            st.dataframe(st.session_state[key], use_container_width=True)
        else:
            st.info("Directorio vacío.")
