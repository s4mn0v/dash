import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.etl import get_consolidated_df


def kpi_card(label, value, color="blue"):
    color_map = {
        "green": ("#EAF3DE", "#3B6D11"),
        "amber": ("#FAEEDA", "#854F0B"),
        "red": ("#FCEBEB", "#A32D2D"),
        "blue": ("#E6F1FB", "#185FA5"),
        "purple": ("#EEEDFE", "#3C3489"),
    }
    bg, fg = color_map.get(color, color_map["blue"])
    st.markdown(
        f"""<div style="background:{bg};padding:16px 18px;border-radius:10px;">
            <p style="color:{fg};margin:0 0 4px;font-size:12px;font-weight:500;
               text-transform:uppercase;letter-spacing:.05em;">{label}</p>
            <p style="margin:0;font-size:24px;font-weight:600;color:{fg};">{value}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def _pct_color(pct):
    if pct >= 80:
        return "green"
    if pct >= 60:
        return "amber"
    return "red"


def _hex_pct(pct):
    if pct >= 80:
        return "#639922"
    if pct >= 60:
        return "#BA7517"
    return "#E24B4A"


def render_dashboard(DIRS):
    st.title("Control Tower")

    # ── Carga ───────────────────────────────────────────────────────
    df_e = get_consolidated_df(DIRS["Grupo Entrega Real"])
    df_p = get_consolidated_df(DIRS["Referencias Pendientes"])
    df_c = get_consolidated_df(DIRS["Unidades cortadas"])
    df_w = get_consolidated_df(DIRS.get("WIP"))

    # ── Filtros globales ────────────────────────────────────────────
    f1, f2, f3 = st.columns(3)

    marcas_disp = sorted(
        set().union(
            df_e["MARCA"].dropna().unique().tolist()
            if df_e is not None and "MARCA" in df_e
            else [],
            df_c["MARCA"].dropna().unique().tolist()
            if df_c is not None and "MARCA" in df_c
            else [],
        )
    ) or ["STOP", "YOYO"]
    sel_marca = f1.multiselect("Marca", marcas_disp, default=marcas_disp)

    meses_disp = []
    for df in [df_e, df_p, df_c]:
        if df is not None and "MES" in df.columns:
            meses_disp = sorted(df["MES"].dropna().unique().tolist())
            break
    sel_mes = f2.multiselect("Mes de entrega", meses_disp)

    mats_disp = []
    for df in [df_c, df_p, df_w]:
        if df is not None and "TIPO DE MATERIAL" in df.columns:
            mats_disp = sorted(df["TIPO DE MATERIAL"].dropna().unique().tolist())
            break
    sel_mat = f3.multiselect("Tipo de material", mats_disp)

    def filtrar(df):
        if df is None:
            return None
        mask = pd.Series(True, index=df.index)
        if sel_marca and "MARCA" in df.columns:
            mask &= df["MARCA"].isin(sel_marca)
        if sel_mes and "MES" in df.columns:
            mask &= df["MES"].isin(sel_mes)
        if sel_mat and "TIPO DE MATERIAL" in df.columns:
            mask &= df["TIPO DE MATERIAL"].isin(sel_mat)
        return df[mask].copy()

    df_ef = filtrar(df_e)
    df_pf = filtrar(df_p)
    df_cf = filtrar(df_c)
    df_wf = filtrar(df_w)

    st.divider()

    # ── KPIs ────────────────────────────────────────────────────────
    # Pedido total: CANT. ORDENADA de df_e
    pedido = (
        int(df_ef["CANT. ORDENADA"].sum())
        if df_ef is not None and "CANT. ORDENADA" in df_ef
        else 0
    )
    # Terminado: CANT. COMPLETA de df_e
    terminado = (
        int(df_ef["CANT. COMPLETA"].sum())
        if df_ef is not None and "CANT. COMPLETA" in df_ef
        else 0
    )
    # Cortado: CANT. COMPLETA de df_c  (en ese archivo representa unidades cortadas)
    cortado = (
        int(df_cf["CANT. COMPLETA"].sum())
        if df_cf is not None and "CANT. COMPLETA" in df_cf
        else 0
    )
    # WIP: CANT. PENDIENTE de df_w
    wip = (
        int(df_wf["CANT. PENDIENTE"].sum())
        if df_wf is not None and "CANT. PENDIENTE" in df_wf
        else 0
    )

    # Backlog = pedido - cortado (unidades ordenadas que aún no entraron a corte)
    backlog = max(0, pedido - cortado)
    # Cumplimiento global
    pct_cumpl = round(terminado / pedido * 100, 1) if pedido > 0 else 0.0
    # Eficiencia de corte = cortado / pedido
    pct_ef = round(cortado / pedido * 100, 1) if pedido > 0 else 0.0
    # Ref. pendientes
    n_pend = len(df_pf) if df_pf is not None else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        kpi_card("Cumplimiento global", f"{pct_cumpl}%", _pct_color(pct_cumpl))
    with k2:
        kpi_card("WIP actual", f"{wip:,}", "blue")
    with k3:
        kpi_card(
            "Backlog de corte", f"{backlog:,}", "amber" if backlog > 0 else "green"
        )
    with k4:
        kpi_card("Eficiencia de corte", f"{pct_ef}%", _pct_color(pct_ef))
    with k5:
        kpi_card("Ref. pendientes", f"{n_pend:,}", "red" if n_pend > 100 else "amber")

    st.divider()

    # ── Embudo de flujo ─────────────────────────────────────────────
    st.subheader("Embudo de flujo")

    def _pct_label(v):
        return f"{v:,} ({round(v / pedido * 100)}%)" if pedido > 0 else str(v)

    fig_funnel = go.Figure(
        go.Bar(
            y=["Terminado", "WIP", "Cortado", "Pedido"],
            x=[terminado, wip, cortado, pedido],
            orientation="h",
            text=[
                _pct_label(terminado),
                _pct_label(wip),
                _pct_label(cortado),
                _pct_label(pedido),
            ],
            textposition="inside",
            insidetextanchor="start",
            marker_color=["#639922", "#BA7517", "#1D9E75", "#378ADD"],
            marker_line_width=0,
        )
    )
    fig_funnel.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False),
        margin=dict(t=10, b=10, l=10, r=10),
        height=220,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

    st.divider()

    # ── Salud WIP + Balance marca/material ─────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Salud del WIP")
        if (
            df_wf is not None
            and "FECHA DE ENTREGA TELAS" in df_wf.columns
            and "CANT. PENDIENTE" in df_wf.columns
        ):
            dw = df_wf.copy()
            dw["FECHA DE ENTREGA TELAS"] = pd.to_datetime(
                dw["FECHA DE ENTREGA TELAS"], errors="coerce", dayfirst=True
            )
            dw["DIAS"] = (pd.Timestamp.now() - dw["FECHA DE ENTREGA TELAS"]).dt.days
            dw["Antigüedad"] = dw["DIAS"].apply(
                lambda d: (
                    "+15 días"
                    if pd.notna(d) and d > 15
                    else ("8–15 días" if pd.notna(d) and d > 7 else "0–7 días")
                )
            )
            resumen = (
                dw.groupby("Antigüedad")["CANT. PENDIENTE"]
                .sum()
                .reindex(["0–7 días", "8–15 días", "+15 días"], fill_value=0)
                .reset_index()
            )
            fig_wip = px.pie(
                resumen,
                names="Antigüedad",
                values="CANT. PENDIENTE",
                hole=0.55,
                color="Antigüedad",
                color_discrete_map={
                    "0–7 días": "#639922",
                    "8–15 días": "#BA7517",
                    "+15 días": "#E24B4A",
                },
            )
            fig_wip.update_layout(margin=dict(t=10, b=10), height=260)
            st.plotly_chart(fig_wip, use_container_width=True)
        else:
            st.info("Sin datos de WIP con fecha de entrega de telas.")

    with col_r:
        st.subheader("Balance marca × material")
        # Preferir df_c; si no tiene material usar df_p
        src = None
        if (
            df_cf is not None
            and "TIPO DE MATERIAL" in df_cf.columns
            and "MARCA" in df_cf.columns
        ):
            src = df_cf
            val_col = "CANT. COMPLETA"
        elif (
            df_pf is not None
            and "TIPO DE MATERIAL" in df_pf.columns
            and "MARCA" in df_pf.columns
        ):
            src = df_pf
            val_col = None  # conteo

        if src is not None:
            if val_col and val_col in src.columns:
                df_mat = (
                    src.groupby(["TIPO DE MATERIAL", "MARCA"])[val_col]
                    .sum()
                    .reset_index()
                )
                y_axis = val_col
            else:
                df_mat = (
                    src.groupby(["TIPO DE MATERIAL", "MARCA"])
                    .size()
                    .reset_index(name="CANTIDAD")
                )
                y_axis = "CANTIDAD"

            fig_mat = px.bar(
                df_mat,
                x="TIPO DE MATERIAL",
                y=y_axis,
                color="MARCA",
                barmode="group",
                color_discrete_map={
                    "STOP": "#378ADD",
                    "YOYO": "#D4537E",
                    "001 - STOP": "#378ADD",
                    "003 - YOYO": "#D4537E",
                },
            )
            fig_mat.update_layout(
                margin=dict(t=10, b=10),
                height=260,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_mat, use_container_width=True)
        else:
            st.info("Sin datos de material disponibles.")

    st.divider()

    # ── Cumplimiento por grupo de entrega ───────────────────────────
    st.subheader("Cumplimiento por grupo de entrega")
    if (
        df_ef is not None
        and "GRUPO DE ENTREGA" in df_ef.columns
        and "CANT. ORDENADA" in df_ef.columns
        and "CANT. COMPLETA" in df_ef.columns
    ):
        grp = (
            df_ef.groupby("GRUPO DE ENTREGA")
            .agg(
                ORDENADO=("CANT. ORDENADA", "sum"),
                COMPLETO=("CANT. COMPLETA", "sum"),
            )
            .reset_index()
        )
        grp["PCT"] = (
            (grp["COMPLETO"] / grp["ORDENADO"].replace(0, pd.NA) * 100)
            .fillna(0)
            .round(1)
        )
        grp = grp.sort_values("PCT")
        grp["COLOR"] = grp["PCT"].apply(_hex_pct)

        fig_grp = px.bar(
            grp,
            x="GRUPO DE ENTREGA",
            y="PCT",
            color="COLOR",
            color_discrete_map="identity",
            text="PCT",
        )
        fig_grp.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_grp.update_layout(
            yaxis=dict(range=[0, 115], title="Cumplimiento %"),
            xaxis=dict(tickangle=-35),
            showlegend=False,
            margin=dict(t=10, b=80),
            height=340,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_grp, use_container_width=True)
    else:
        st.info("Sin datos de grupo de entrega.")

    st.divider()

    # ── O.P. Críticas ───────────────────────────────────────────────
    st.subheader("O.P. críticas — vencidas sin avance")

    df_crit_src = df_ef  # Grupo Entrega Real tiene FECHA TERMINACIÓN y CANT. PENDIENTE
    if df_crit_src is not None:
        dc = df_crit_src.copy()
        fecha_col = next(
            (
                c
                for c in ["FECHA TERMINACIÓN", "FECHA TERMINACION", "FECHA DE ENTREGA"]
                if c in dc.columns
            ),
            None,
        )
        if fecha_col:
            dc[fecha_col] = pd.to_datetime(
                dc[fecha_col], errors="coerce", dayfirst=True
            )
            pend_col = "CANT. PENDIENTE" if "CANT. PENDIENTE" in dc.columns else None
            if pend_col:
                dc_crit = dc[
                    (dc[fecha_col] < pd.Timestamp.now().normalize())
                    & (dc[pend_col] > 0)
                ]
                col_op = next(
                    (c for c in ["O.P. NÚMERO", "O.P. NUMERO"] if c in dc_crit.columns),
                    None,
                )
                cols_show = [
                    "MARCA",
                    "REFERENCIA",
                    "GRUPO DE ENTREGA",
                    pend_col,
                    fecha_col,
                ]
                if col_op:
                    cols_show.insert(0, col_op)
                cols_show = [c for c in cols_show if c in dc_crit.columns]
                st.dataframe(
                    dc_crit[cols_show].sort_values(pend_col, ascending=False).head(10),
                    use_container_width=True,
                )
            else:
                st.info("Columna CANT. PENDIENTE no encontrada en Grupo Entrega Real.")
        else:
            st.info("Columna de fecha de terminación no encontrada.")
    else:
        st.info("Sin datos de entregas para calcular O.P. críticas.")

    st.divider()
