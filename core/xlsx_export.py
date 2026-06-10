import io

import pandas as pd
import streamlit as st


def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Datos")
    return buf.getvalue()


def download_xlsx_button(
    df: pd.DataFrame, filename: str, label: str = "⬇ Descargar XLSX"
):
    if df is None or df.empty:
        return
    st.download_button(
        label=label,
        data=to_xlsx_bytes(df),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
