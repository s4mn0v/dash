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
    for c in ["REFERENCIA", "O.P. NÚMERO", "GRUPO DE ENTREGA"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["MARCA"] = "STOP" if "STOP" in fname.upper() else "YOYO"
    for c in ["CANT. PLANEADA", "CANT. ORDENADA", "CANT. COMPLETA", "CANT. PENDIENTE"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["ESTADO_PEDIDO"] = df.apply(
        lambda r: (
            "TERMINADO"
            if r.get("CANT. PENDIENTE", 0) == 0
            else ("EN PROCESO" if r.get("CANT. COMPLETA", 0) > 0 else "SIN INICIAR")
        ),
        axis=1,
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
