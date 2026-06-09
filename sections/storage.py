import os
from datetime import datetime

import pandas as pd
import streamlit as st

from core.etl import normalize_cols
from core.processor import etl_cortadas, etl_entrega, etl_pendientes, etl_wip

FOLDER_COLORS = [
    "#185FA5",  # blue
    "#0F6E56",  # teal
    "#854F0B",  # amber
    "#993556",  # pink
    "#534AB7",  # purple
    "#993C1D",  # coral
]


def _file_meta(path: str) -> tuple[str, str]:
    stat = os.stat(path)
    size = stat.st_size
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024**2:
        size_str = f"{size / 1024:.0f} KB"
    else:
        size_str = f"{size / 1024**2:.1f} MB"
    date_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y")
    return size_str, date_str


def render_storage(DIRS):
    st.title("Gestión de archivos")
    st.divider()

    if "upload_reset" not in st.session_state:
        st.session_state["upload_reset"] = {}

    for idx, (label, path) in enumerate(DIRS.items()):
        color = FOLDER_COLORS[idx % len(FOLDER_COLORS)]
        files = sorted(os.listdir(path)) if os.path.isdir(path) else []
        n = len(files)
        badge = f"{n} {'archivo' if n == 1 else 'archivos'}" if n > 0 else "vacío"

        # ── Cabecera con barra de color ─────────────────────────────
        st.markdown(
            f"""
            <div style="
                border-left: 4px solid {color};
                border-radius: 0;
                padding: 10px 14px;
                margin: 1.5rem 0 0.75rem;
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <h4 style="font-weight:500;color:var(--color-text-primary);flex:1">{label}</h4>
                <span style="
                    font-size:11px;
                    padding:2px 10px;
                    border-radius:20px;
                    background:{color}22;
                    color:{color};
                    font-weight:500;
                ">{badge}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Subida ──────────────────────────────────────────────────
        reset_n = st.session_state["upload_reset"].get(label, 0)
        up_col, btn_col = st.columns([5, 1])
        with up_col:
            uploaded = st.file_uploader(
                f"up_label_{label}",
                type=["xls", "xlsx"],
                accept_multiple_files=True,
                key=f"up_{label}_{reset_n}",
                label_visibility="collapsed",
            )
        with btn_col:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button(
                "Subir",
                key=f"btn_up_{label}",
                use_container_width=True,
            ):
                if uploaded:
                    for f in uploaded:
                        # 1. Leer excel temporal
                        df = pd.read_excel(f)

                        # 2. Aplicar Forward Fill base
                        excl = [
                            "MES ADELANTO",
                            "GRUPO DE ENTREGA",
                            "LINEA",
                            "TIPO DE ABASTECIMIENTO",
                        ]
                        fill_cols = [c for c in df.columns if c not in excl]
                        df[fill_cols] = df[fill_cols].ffill()

                        # 3. Aplicar lógica por sección
                        if label == "Grupo Entrega Real":
                            df = etl_entrega(df, f.name)
                        elif label == "Referencias Pendientes":
                            df = etl_pendientes(df)
                        elif label == "Unidades cortadas":
                            df = etl_cortadas(df)
                        elif label == "WIP":
                            df = etl_wip(df, f.name)
                        else:
                            df = normalize_cols(df)

                        # 4. Guardar como CSV
                        fname_csv = f.name.rsplit(".", 1)[0] + ".csv"
                        df.to_csv(os.path.join(path, fname_csv), index=False)

                    # Reset y cache
                    cache_key = f"df_cache_{label}"
                    if cache_key in st.session_state:
                        del st.session_state[cache_key]
                    st.session_state["upload_reset"][label] = reset_n + 1
                    st.rerun()
                else:
                    st.toast("Selecciona al menos un archivo primero.", icon="⚠️")

        # ── Lista de archivos ───────────────────────────────────────
        if not files:
            st.caption("No hay archivos en esta carpeta.")
            st.divider()
            continue

        # Cabecera columnas
        _, h_name, h_size, h_date, _ = st.columns([0.4, 4, 1, 1.2, 0.5])
        h_name.markdown(
            "<span style='font-size:12px;color:var(--color-text-secondary)'>Nombre</span>",
            unsafe_allow_html=True,
        )
        h_size.markdown(
            "<span style='font-size:12px;color:var(--color-text-secondary)'>Tamaño</span>",
            unsafe_allow_html=True,
        )
        h_date.markdown(
            "<span style='font-size:12px;color:var(--color-text-secondary)'>Modificado</span>",
            unsafe_allow_html=True,
        )

        selected = []
        for fname in files:
            fpath = os.path.join(path, fname)
            size_str, date_str = _file_meta(fpath)

            c_chk, c_name, c_size, c_date, c_del = st.columns([0.4, 4, 1, 1.2, 0.5])
            checked = c_chk.checkbox(
                label=fname,
                key=f"chk_{label}_{fname}",
                label_visibility="collapsed",
            )
            c_name.markdown(
                f"<span style='font-size:13px;line-height:2;"
                f"border-left:2px solid {color};padding-left:8px'>{fname}</span>",
                unsafe_allow_html=True,
            )
            c_size.markdown(
                f"<span style='font-size:12px;color:var(--color-text-secondary);line-height:2.8'>{size_str}</span>",
                unsafe_allow_html=True,
            )
            c_date.markdown(
                f"<span style='font-size:12px;color:var(--color-text-secondary);line-height:2.8'>{date_str}</span>",
                unsafe_allow_html=True,
            )
            if c_del.button("✕", key=f"del1_{label}_{fname}", help=f"Eliminar {fname}"):
                os.remove(fpath)
                cache_key = f"df_cache_{label}"
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                st.rerun()

            if checked:
                selected.append(fname)

        # ── Acciones bulk ───────────────────────────────────────────
        act1, act2, _ = st.columns([1.6, 1.4, 3])
        del_label = (
            f"Eliminar seleccionados ({len(selected)})"
            if selected
            else "Eliminar seleccionados"
        )
        if act1.button(
            del_label, key=f"del_{label}", disabled=not selected, type="secondary"
        ):
            for fname in selected:
                os.remove(os.path.join(path, fname))
            cache_key = f"df_cache_{label}"
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()

        if act2.button("Vaciar carpeta", key=f"clear_{label}", type="secondary"):
            for fname in files:
                os.remove(os.path.join(path, fname))
            cache_key = f"df_cache_{label}"
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()

        st.divider()
