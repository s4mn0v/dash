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

    def get_opts(series, label):
        s = (
            series.astype(str)
            .str.strip()
            .replace(["nan", "None", "", "NaN", "<NA>"], pd.NA)
        )
        s = s.apply(lambda x: re.sub(r"^\d+\s*-\s*", "", str(x)) if pd.notna(x) else x)
        return s.fillna(label)

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

    # --- LOGICA REFERENCIAS PENDIENTES ---
    elif page == "Referencias Pendientes" and df_v is not None:
        st.subheader("Filtros")
        c1, c2, c3, c4 = st.columns(4)

        s_marca = get_opts(df_v["MARCA"], "[Sin Marca]")
        s_mat = (
            get_opts(df_v["TIPO DE MATERIAL"], "[Sin Material]")
            if "TIPO DE MATERIAL" in df_v
            else pd.Series()
        )
        # Cambio a Mes_Limpio
        s_mes = get_opts(df_v["MES"], "[Sin Mes]") if "MES" in df_v else pd.Series()
        s_prio = (
            get_opts(df_v["PRIORIDAD"], "Normal")
            if "PRIORIDAD" in df_v
            else pd.Series()
        )

        f_marca = c1.multiselect("Marca", sorted(s_marca.unique().tolist()))
        f_mat = c2.multiselect("Tipo de Material", sorted(s_mat.unique().tolist()))
        f_mes = c3.multiselect("Mes Limpio", sorted(s_mes.unique().tolist()))
        f_prio = c4.multiselect("Prioridad", sorted(s_prio.unique().tolist()))

        mask = pd.Series(True, index=df_v.index)
        if f_marca:
            mask &= s_marca.isin(f_marca)
        if f_mat:
            mask &= s_mat.isin(f_mat)
        if f_mes:
            mask &= s_mes.isin(f_mes)
        if f_prio:
            mask &= s_prio.isin(f_prio)
        df_f = df_v[mask]

        st.divider()
        chart_col1, chart_col2 = st.columns(2)

        if "TIPO DE MATERIAL" in df_f.columns:
            df_mat = (
                df_f.groupby(["TIPO DE MATERIAL", "MARCA"])
                .size()
                .reset_index(name="CANTIDAD")
            )
            chart_col1.plotly_chart(
                px.bar(
                    df_mat,
                    x="TIPO DE MATERIAL",
                    y="CANTIDAD",
                    color="MARCA",
                    title="Pendientes por Material",
                ),
                use_container_width=True,
            )

        if "TIPO DE LINEA" in df_f.columns:
            df_linea = df_f["TIPO DE LINEA"].value_counts().reset_index()
            chart_col2.plotly_chart(
                px.pie(
                    df_linea,
                    values="count",
                    names="TIPO DE LINEA",
                    hole=0.5,
                    title="Distribución por Línea",
                ),
                use_container_width=True,
            )

        st.subheader("Resumen por Grupo de Entrega")
        if "GRUPO DE ENTREGA" in df_f.columns:
            resumen = (
                df_f.groupby("GRUPO DE ENTREGA")
                .size()
                .reset_index(name="REF. PENDIENTES")
            )
            st.table(resumen.sort_values("REF. PENDIENTES", ascending=False))
        st.divider()

    # --- LOGICA UNIDADES CORTADAS ---
    elif page == "Unidades cortadas" and df_v is not None:
        # Asegurar que FECHA CREACIÓN sea datetime antes de filtrar
        if "FECHA CREACIÓN" in df_v.columns:
            df_v["FECHA CREACIÓN"] = pd.to_datetime(
                df_v["FECHA CREACIÓN"], errors="coerce"
            )

        st.subheader("Filtros")
        c1, c2, c3 = st.columns(3)

        s_marca = get_opts(df_v["MARCA"], "[Sin Marca]")
        s_linea = (
            get_opts(df_v["LINEA"], "[Sin Linea]") if "LINEA" in df_v else pd.Series()
        )

        # Obtener nombres de meses válidos
        if "FECHA CREACIÓN" in df_v.columns:
            s_mes = df_v["FECHA CREACIÓN"].dt.month_name().fillna("[Sin Fecha]")
        else:
            s_mes = pd.Series()

        f_marca = c1.multiselect("Marca", sorted(s_marca.unique().tolist()))
        f_linea = c2.multiselect("Línea", sorted(s_linea.unique().tolist()))
        f_mes = c3.multiselect("Mes", sorted(s_mes.unique().tolist()))

        mask = pd.Series(True, index=df_v.index)
        if f_marca:
            mask &= s_marca.isin(f_marca)
        if f_linea:
            mask &= s_linea.isin(f_linea)
        if f_mes:
            mask &= s_mes.isin(f_mes)
        df_f = df_v[mask].copy()

        num_cols = df_f.select_dtypes(include=["number"]).columns.tolist()
        val_col = (
            "CANT. PLANEADA"
            if "CANT. PLANEADA" in num_cols
            else (num_cols[0] if num_cols else None)
        )

        if val_col and not df_f.empty:
            st.divider()

            # 1. Columnas Apiladas
            if "LINEA" in df_f.columns:
                df_wip = df_f.groupby(["LINEA", "MARCA"])[val_col].sum().reset_index()
                st.plotly_chart(
                    px.bar(
                        df_wip,
                        x="LINEA",
                        y=val_col,
                        color="MARCA",
                        barmode="stack",
                        title=f"WIP: {val_col} por Línea",
                    ),
                    use_container_width=True,
                )

            # 2. Productividad Diaria (Corregido)
            if "FECHA CREACIÓN" in df_f.columns:
                # Eliminar nulos para la línea de tiempo
                df_temp = df_f.dropna(subset=["FECHA CREACIÓN"])
                if not df_temp.empty:
                    df_daily = (
                        df_temp.groupby(df_temp["FECHA CREACIÓN"].dt.date)[val_col]
                        .sum()
                        .reset_index()
                    )
                    df_daily.columns = [
                        "FECHA",
                        "CANTIDAD",
                    ]  # Renombrar para evitar conflictos
                    st.plotly_chart(
                        px.line(
                            df_daily,
                            x="FECHA",
                            y="CANTIDAD",
                            markers=True,
                            title="Productividad Diaria (Unidades Cortadas)",
                        ),
                        use_container_width=True,
                    )
                else:
                    st.info("No hay fechas válidas para mostrar productividad.")

            # 3. Treemap
            if "TIPO DE MATERIAL" in df_f.columns:
                df_tree = df_f.groupby("TIPO DE MATERIAL")[val_col].sum().reset_index()
                st.plotly_chart(
                    px.treemap(
                        df_tree,
                        path=["TIPO DE MATERIAL"],
                        values=val_col,
                        title="Distribución por Material",
                    ),
                    use_container_width=True,
                )
        else:
            st.warning("Sin datos numéricos o filtros demasiado estrictos.")

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
