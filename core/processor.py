import pandas as pd

from core.etl import base_clean, clean_txt


def etl_entrega(df, fname):
    df = base_clean(df)
    targets = {
        "DESC. EXTENSIÓN 1": "COLOR_NOMBRE",
        "DETALLE EXT. 1": "COLOR_NOMBRE",
        "COLECCION": "COLECCIÓN",
    }
    df = df.rename(columns=targets)
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].astype(str).str.strip()
    marca = "STOP" if "STOP" in fname.upper() else "YOYO"
    if "MARCA" in df.columns:
        df = df.drop(columns=["MARCA"])
    df.insert(0, "MARCA", marca)
    for c in ["CANT. ORDENADA", "CANT. COMPLETA", "CANT. PENDIENTE"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["CUMPLIMIENTO %"] = (df["CANT. COMPLETA"] / df["CANT. ORDENADA"]).fillna(0)
    df["ESTATUS OP"] = df["CANT. PENDIENTE"].apply(
        lambda x: "INCOMPLETO" if x > 0 else "CERRADO"
    )
    return df


def etl_pendientes(df):
    df = base_clean(df)
    # 1. Mes_Limpio
    if "MES" in df.columns:
        df["MES"] = df["MES"].apply(clean_txt)
    # 2. Marcas (STOP/YOYO)
    if "MARCA" in df.columns:
        df["MARCA"] = df["MARCA"].apply(clean_txt)
    # 3. Prioridad
    if "MES ADELANTO" in df.columns:
        df["PRIORIDAD"] = df["MES ADELANTO"].apply(
            lambda x: (
                "Prioridad Alta" if pd.notna(x) and str(x).strip() != "" else "Normal"
            )
        )
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
