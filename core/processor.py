import pandas as pd

from core.etl import base_clean, clean_txt


# core/processor.py
def etl_entrega(df, fname):
    df = base_clean(df)
    # Homologar + Limpiar (TRIM)
    df.columns = [c.replace("COLECCION", "COLECCIÓN") for c in df.columns]
    for c in ["REFERENCIA", "O.P. NÚMERO", "GRUPO DE ENTREGA"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # Marca col
    df["MARCA"] = "STOP" if "STOP" in fname.upper() else "YOYO"

    # Num conversion
    for c in ["CANT. ORDENADA", "CANT. COMPLETA", "CANT. PENDIENTE"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # New Cols
    df["CUMPLIMIENTO_%"] = (df["CANT. COMPLETA"] / df["CANT. ORDENADA"]).fillna(0)
    df["ESTATUS_OP"] = df["CANT. PENDIENTE"].apply(
        lambda x: "INCOMPLETO" if x > 0 else "CERRADO"
    )

    return df


def etl_pendientes(df):
    df = base_clean(df)
    if "MES" in df.columns:
        df["MES"] = df["MES"].apply(clean_txt)
    if "MARCA" in df.columns:
        df["MARCA"] = df["MARCA"].apply(clean_txt)
    return df.dropna(subset=["REFERENCIA"])


def etl_cortadas(df):
    df = base_clean(df)
    if "FECHA CREACIÓN" in df.columns:
        df["FECHA CREACIÓN"] = pd.to_datetime(
            df["FECHA CREACIÓN"], errors="coerce", dayfirst=True
        )
    if "DESC. DETALLE EXT. 2" in df.columns:
        df["DESC. DETALLE EXT. 2"] = df["DESC. DETALLE EXT. 2"].astype(str).str.strip()
    return df
