import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.etl import get_consolidated_df


def render_dashboard(DIRS):
    st.title("📊 Dashboard de Control")
    df = get_consolidated_df(DIRS["Grupo Entrega Real"])
    if df is None:
        st.warning("No hay datos.")
        return
    marcas = df["MARCA"].unique()
    meses = df["MES"].unique() if "MES" in df.columns else []
    sel_marca = st.sidebar.multiselect("Marca", marcas, default=marcas)
    sel_mes = st.sidebar.multiselect("Mes", meses, default=meses)
    df_f = df[df["MARCA"].isin(sel_marca)]
    if meses:
        df_f = df_f[df_f["MES"].isin(sel_mes)]

    total_ord, total_com = df_f["CANT. ORDENADA"].sum(), df_f["CANT. COMPLETA"].sum()
    pct = (total_com / total_ord * 100) if total_ord > 0 else 0
    st.plotly_chart(
        go.Figure(
            go.Indicator(
                mode="gauge+number", value=pct, title={"text": "Cumplimiento Total %"}
            )
        ),
        use_container_width=True,
    )

    c1, c2 = st.columns(2)
    if "COLECCIÓN" in df_f.columns:
        fig = px.bar(
            df_f.groupby("COLECCIÓN")[["CANT. ORDENADA", "CANT. COMPLETA"]]
            .sum()
            .reset_index(),
            x="COLECCIÓN",
            y=["CANT. ORDENADA", "CANT. COMPLETA"],
            barmode="group",
        )
        c1.plotly_chart(fig)

    st.subheader("Críticos (Vencidos) - 10 más recientes")
    if "FECHA TERMINACIÓN" in df_f.columns:
        df_crit = df_f[
            (df_f["FECHA TERMINACIÓN"] < pd.Timestamp.now())
            & (df_f["CANT. PENDIENTE"] > 0)
        ]
        st.dataframe(df_crit.sort_values("CANT. PENDIENTE", ascending=False).head(10))
