import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.etl import get_consolidated_df


def kpi_card(label, value, color="#00CC96"):
    st.markdown(
        f"""
        <div style="background:#1E1E1E; padding:20px; border-radius:10px; border-left:5px solid {color};">
            <p style="color:#888; margin:0; font-size:14px;">{label}</p>
            <h2 style="margin:0; color:white;">{value}</h2>
        </div>
    """,
        unsafe_allow_html=True,
    )


def render_dashboard(DIRS):
    st.title("🚀 Control Tower Dashboard")

    # Data Load
    df_e = get_consolidated_df(DIRS["Grupo Entrega Real"])
    df_p = get_consolidated_df(DIRS["Referencias Pendientes"])
    df_c = get_consolidated_df(DIRS["Unidades cortadas"])
    df_w = get_consolidated_df(DIRS["WIP"])

    # Sidebar Filter
    sel = st.sidebar.multiselect("Marcas", ["STOP", "YOYO"], default=["STOP", "YOYO"])

    # --- KPI ROW ---
    c1, c2, c3, c4 = st.columns(4)

    if df_e is not None:
        df_f = df_e[df_e["MARCA"].isin(sel)]
        col_o = next(
            (c for c in ["CANT. ORDENADA", "CANT. PLANEADA"] if c in df_f.columns), None
        )
        pct = (
            (df_f["CANT. COMPLETA"].sum() / df_f[col_o].sum() * 100)
            if col_o and df_f[col_o].sum() > 0
            else 0
        )
        with c1:
            kpi_card("Cumplimiento", f"{pct:.1f}%", "#00CC96")

    if df_p is not None:
        count = len(df_p[df_p["MARCA"].isin(sel)])
        with c2:
            kpi_card("Ref. Pendientes", f"{count:,}", "#F2994A")

    if df_w is not None:
        df_f = df_w[df_w["MARCA"].isin(sel)]
        val = df_f["CANT. PENDIENTE"].sum()
        with c3:
            kpi_card("WIP Taller", f"{val:,.0f}", "#2D9CDB")

    if df_c is not None:
        df_f = df_c[df_c["MARCA"].isin(sel)]
        col_c = next(
            (
                c
                for c in ["CANT. ORDENADA", "CANT. PLANEADA", "CANT. COMPLETA"]
                if c in df_f.columns
            ),
            None,
        )
        val = df_f[col_c].sum() if col_c else 0
        with c4:
            kpi_card("Corte Total", f"{val:,.0f}", "#BB6BD9")

    st.divider()

    # --- ANALYSIS ---
    col_l, col_r = st.columns([2, 1])

    # Gráfico 1: Comparativa Marcas (Balance)
    with col_l:
        st.subheader("📊 Balance por Marca")
        data_m = []
        for m in sel:
            if df_c is not None:
                df_f = df_c[df_c["MARCA"] == m]
                col = next(
                    (
                        c
                        for c in ["CANT. ORDENADA", "CANT. PLANEADA"]
                        if c in df_f.columns
                    ),
                    None,
                )
                data_m.append(
                    {
                        "Marca": m,
                        "Tipo": "Cortado",
                        "Unidades": df_f[col].sum() if col else 0,
                    }
                )
            if df_e is not None:
                df_f = df_e[df_e["MARCA"] == m]
                data_m.append(
                    {
                        "Marca": m,
                        "Tipo": "Entregado",
                        "Unidades": df_f["CANT. COMPLETA"].sum(),
                    }
                )

        if data_m:
            fig = px.bar(
                pd.DataFrame(data_m),
                x="Marca",
                y="Unidades",
                color="Tipo",
                barmode="group",
                color_discrete_sequence=["#BB6BD9", "#00CC96"],
            )
            st.plotly_chart(fig, use_container_width=True)

    # Gráfico 2: Salud del WIP (Aging)
    with col_r:
        st.subheader("🕒 Salud del WIP")
        if df_w is not None:
            # Re-calcular criticidad al vuelo
            df_w_f = df_w[df_w["MARCA"].isin(sel)].copy()
            if "FECHA DE ENTREGA TELAS" in df_w_f.columns:
                df_w_f["FECHA"] = pd.to_datetime(
                    df_w_f["FECHA DE ENTREGA TELAS"], errors="coerce"
                )
                dias = (pd.Timestamp.now() - df_w_f["FECHA"]).dt.days
                df_w_f["Riesgo"] = dias.apply(
                    lambda d: (
                        "Crítico (>14d)"
                        if d > 14
                        else ("Alerta (>7d)" if d > 7 else "Normal")
                    )
                )
                fig_p = px.pie(
                    df_w_f,
                    names="Riesgo",
                    values="CANT. PENDIENTE",
                    color="Riesgo",
                    color_discrete_map={
                        "Crítico (>14d)": "#EB5757",
                        "Alerta (>7d)": "#F2994A",
                        "Normal": "#00CC96",
                    },
                )
                st.plotly_chart(fig_p, use_container_width=True)

    # Tabla: Críticos inmediatos
    st.subheader("⚠️ Top 5 O.P. Críticas (Sin Avance)")
    if df_w is not None:
        df_f = df_w[df_w["MARCA"].isin(sel)].copy()
        if "CANT. COMPLETA" in df_f.columns:
            # Buscar columna OP (con o sin tilde)
            col_op = next(
                (c for c in ["O.P. NÚMERO", "O.P. NUMERO", "OP"] if c in df_f.columns),
                None,
            )

            crit = (
                df_f[df_f["CANT. COMPLETA"] == 0]
                .sort_values("CANT. PENDIENTE", ascending=False)
                .head(5)
            )

            # Columnas seguras
            cols_show = ["MARCA", "GRUPO DE ENTREGA", "CANT. PENDIENTE"]
            if col_op:
                cols_show.insert(1, col_op)

            st.table(crit[cols_show])
