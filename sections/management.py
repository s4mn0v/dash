import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from core.etl import get_consolidated_df, normalize_cols
from core.processor import etl_cortadas, etl_entrega, etl_pendientes, etl_wip
from core.xlsx_export import download_xlsx_button

# --- HELPER ORDEN ---
MESES_ORD = [
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
]


def sort_df(df):
    if df is None or df.empty:
        return df
    s_cols = []
    if "MES" in df.columns:
        df["MES"] = pd.Categorical(df["MES"], categories=MESES_ORD, ordered=True)
        s_cols.append("MES")
    for c in ["O.P. NUMERO", "O.P. NÚMERO", "REFERENCIA"]:
        if c in df.columns:
            s_cols.append(c)
            break
    return df.sort_values(by=s_cols).reset_index(drop=True)


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
                width="stretch",
            )

        st.subheader("O.P. Críticas")
        col_fecha = (
            "FECHA TERMINACION"
            if "FECHA TERMINACION" in df_f.columns
            else "FECHA TERMINACIÓN"
        )

        if col_fecha in df_f.columns:
            df_f = df_f.copy()
            df_f[col_fecha] = pd.to_datetime(df_f[col_fecha], errors="coerce")
            today = pd.Timestamp.now().normalize()
            df_crit = df_f[(df_f[col_fecha] < today) & (df_f["CANT. PENDIENTE"] > 0)]
            df_crit_show = df_crit.sort_values("CANT. PENDIENTE", ascending=False).head(
                10
            )
            st.dataframe(df_crit_show, width="stretch")

        st.divider()
        st.subheader("Vista de Datos")
        st.dataframe(df_f, width="stretch")

        dl1, dl2, _ = st.columns([1.5, 1.5, 5])
        with dl1:
            download_xlsx_button(
                df_f, "grupo_entrega_real.xlsx", "⬇ Exportar vista (XLSX)"
            )
        with dl2:
            if col_fecha in df_f.columns:
                download_xlsx_button(
                    df_crit_show, "op_criticas.xlsx", "⬇ O.P. Críticas (XLSX)"
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
                width="stretch",
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
                width="stretch",
            )

        st.subheader("Resumen por Grupo de Entrega")
        if "GRUPO DE ENTREGA" in df_f.columns:
            resumen = (
                df_f.groupby("GRUPO DE ENTREGA")
                .size()
                .reset_index(name="REF. PENDIENTES")
                .sort_values("REF. PENDIENTES", ascending=False)
            )
            st.table(resumen)

        st.subheader("Vista de Datos")
        st.dataframe(df_f, width="stretch")

        dl1, _ = st.columns([2, 6])
        with dl1:
            download_xlsx_button(
                df_f, "referencias_pendientes.xlsx", "⬇ Exportar vista (XLSX)"
            )
        st.divider()

    # --- LOGICA UNIDADES CORTADAS ---
    elif page == "Unidades cortadas" and df_v is not None:
        if "FECHA CREACION" in df_v.columns:
            df_v["FECHA CREACION"] = pd.to_datetime(
                df_v["FECHA CREACION"], errors="coerce", format="mixed"
            )

        st.subheader("Filtros")
        c1, c2, c3 = st.columns(3)

        s_marca = get_opts(df_v["MARCA"], "[Sin Marca]")
        s_linea = (
            get_opts(df_v["LINEA"], "[Sin Linea]") if "LINEA" in df_v else pd.Series()
        )
        s_mes = get_opts(df_v["MES"], "[Sin Mes]") if "MES" in df_v else pd.Series()

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
        val_col = None
        for c in ["CANT. ORDENADA", "CANT. PLANEADA", "CANT. COMPLETA"]:
            if c in num_cols:
                val_col = c
                break
        if not val_col and num_cols:
            val_col = num_cols[0]

        if val_col and not df_f.empty:
            st.divider()

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
                    width="stretch",
                )

            if "FECHA CREACION" in df_f.columns:
                df_temp = df_f.dropna(subset=["FECHA CREACION"])
                if not df_temp.empty:
                    df_daily = (
                        df_temp.groupby(df_temp["FECHA CREACION"].dt.date)[val_col]
                        .sum()
                        .reset_index()
                    )
                    df_daily.columns = ["FECHA", "CANTIDAD"]
                    df_daily = df_daily.sort_values("FECHA")
                    st.plotly_chart(
                        px.line(
                            df_daily,
                            x="FECHA",
                            y="CANTIDAD",
                            markers=True,
                            title=f"Productividad Diaria ({val_col})",
                        ),
                        width="stretch",
                    )
                else:
                    st.info("No hay fechas válidas para mostrar productividad.")

            if "TIPO DE MATERIAL" in df_f.columns:
                df_tree = df_f.groupby("TIPO DE MATERIAL")[val_col].sum().reset_index()
                st.plotly_chart(
                    px.treemap(
                        df_tree,
                        path=["TIPO DE MATERIAL"],
                        values=val_col,
                        title="Distribución por Material",
                    ),
                    width="stretch",
                )
        else:
            st.warning("Sin datos numéricos o filtros vacíos.")

        st.subheader("Vista de Datos")
        st.dataframe(df_f, width="stretch")

        dl1, _ = st.columns([2, 6])
        with dl1:
            download_xlsx_button(
                df_f, "unidades_cortadas.xlsx", "⬇ Exportar vista (XLSX)"
            )
        st.divider()

    # --- LOGICA WIP ---
    elif page == "WIP" and df_v is not None:
        if "FECHA DE ENTREGA TELAS" in df_v.columns:
            df_v["FECHA DE ENTREGA TELAS"] = pd.to_datetime(
                df_v["FECHA DE ENTREGA TELAS"], errors="coerce"
            )
            now = pd.Timestamp.now().normalize()
            df_v["DIAS_TALLER"] = (now - df_v["FECHA DE ENTREGA TELAS"]).dt.days.fillna(
                0
            )

            def get_crit(d):
                if d <= 7:
                    return "NORMAL"
                if d <= 14:
                    return "ATENCION"
                return "CRITICO"

            df_v["CRITICIDAD"] = df_v["DIAS_TALLER"].apply(get_crit)
        if "CANT. ORDENADA" in df_v.columns and "CANT. COMPLETA" in df_v.columns:
            df_v["AVANCE_%"] = (
                df_v["CANT. COMPLETA"] / df_v["CANT. ORDENADA"] * 100
            ).fillna(0)

        st.subheader("Filtros WIP")
        c1, c2, c3, c4 = st.columns(4)
        s_marca = get_opts(df_v["MARCA"], "[Sin Marca]")
        s_mat = get_opts(df_v["TIPO DE MATERIAL"], "[Sin Material]")
        s_mes = get_opts(df_v["MES"], "[Sin Mes]")
        s_crit = (
            get_opts(df_v["CRITICIDAD"], "NORMAL")
            if "CRITICIDAD" in df_v
            else pd.Series(["NORMAL"] * len(df_v))
        )

        f_marca = c1.multiselect("Marca", sorted(s_marca.unique().tolist()))
        f_mat = c2.multiselect("Material", sorted(s_mat.unique().tolist()))
        f_mes = c3.multiselect("Mes", sorted(s_mes.unique().tolist()))
        f_crit = c4.multiselect("Criticidad", ["NORMAL", "ATENCION", "CRITICO"])

        mask = pd.Series(True, index=df_v.index)
        if f_marca:
            mask &= s_marca.isin(f_marca)
        if f_mat:
            mask &= s_mat.isin(f_mat)
        if f_mes:
            mask &= s_mes.isin(f_mes)
        if f_crit:
            mask &= s_crit.isin(f_crit)
        df_f = df_v[mask].copy()

        if not df_f.empty:
            st.divider()
            col_a, col_b = st.columns(2)

            if "CRITICIDAD" in df_f.columns:
                df_age = (
                    df_f.groupby(["CRITICIDAD", "MARCA"])["CANT. PENDIENTE"]
                    .sum()
                    .reset_index()
                )
                col_a.plotly_chart(
                    px.bar(
                        df_age,
                        x="CRITICIDAD",
                        y="CANT. PENDIENTE",
                        color="MARCA",
                        title="Aging WIP",
                        category_orders={
                            "CRITICIDAD": ["NORMAL", "ATENCION", "CRITICO"]
                        },
                    ),
                    width="stretch",
                )

            if "TIPO DE MATERIAL" in df_f.columns:
                df_m = (
                    df_f.groupby("TIPO DE MATERIAL")["CANT. PENDIENTE"]
                    .sum()
                    .reset_index()
                )
                col_b.plotly_chart(
                    px.treemap(
                        df_m,
                        path=["TIPO DE MATERIAL"],
                        values="CANT. PENDIENTE",
                        title="WIP Material",
                    ),
                    width="stretch",
                )

            if "GRUPO DE ENTREGA" in df_f.columns:
                df_grp = (
                    df_f.groupby("GRUPO DE ENTREGA")["CANT. PENDIENTE"]
                    .sum()
                    .reset_index()
                    .sort_values("CANT. PENDIENTE")
                )
                st.plotly_chart(
                    px.bar(
                        df_grp.tail(15),
                        x="CANT. PENDIENTE",
                        y="GRUPO DE ENTREGA",
                        orientation="h",
                        title="Top Carga",
                    ),
                    width="stretch",
                )

            st.subheader("Avance 0% — 10 más recientes")
            df_zero = (
                df_f[df_f["AVANCE_%"] == 0]
                .sort_values("DIAS_TALLER", ascending=False)
                .head(10)
            )
            st.dataframe(df_zero, width="stretch")

            dl1, dl2, _ = st.columns([1.8, 1.8, 4])
            with dl1:
                download_xlsx_button(df_f, "wip.xlsx", "⬇ Exportar WIP (XLSX)")
            with dl2:
                download_xlsx_button(
                    df_zero, "wip_sin_avance.xlsx", "⬇ Sin avance (XLSX)"
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
                elif page == "WIP":
                    df = etl_wip(df, f.name)
                else:
                    df = normalize_cols(df)
                df.to_csv(
                    os.path.join(path, f.name.rsplit(".", 1)[0] + ".csv"), index=False
                )
            new_df = get_consolidated_df(path)
            st.session_state[key] = sort_df(new_df)
            st.rerun()
    with view:
        st.subheader("Vista de Datos")
        if st.session_state[key] is not None:
            st.dataframe(st.session_state[key], width="stretch")
            dl1, _ = st.columns([2, 6])
            with dl1:
                download_xlsx_button(
                    st.session_state[key],
                    f"{page.lower().replace(' ', '_')}_completo.xlsx",
                    "⬇ Exportar todo (XLSX)",
                )
        else:
            st.info("Directorio vacío.")
