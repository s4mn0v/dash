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
    # Limpiar Mes y Marca igual que Pendientes
    if "MES" in df.columns:
        df["MES"] = df["MES"].apply(clean_txt)
    if "MARCA" in df.columns:
        df["MARCA"] = df["MARCA"].apply(clean_txt)

    if "FECHA CREACION" in df.columns:
        df["FECHA CREACION"] = pd.to_datetime(
            df["FECHA CREACION"], errors="coerce", format="mixed"
        )

    # Asegurar números
    for c in ["CANT. PLANEADA", "CANT. ORDENADA", "CANT. COMPLETA"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "DESC. DETALLE EXT. 2" in df.columns:
        df["DESC. DETALLE EXT. 2"] = df["DESC. DETALLE EXT. 2"].astype(str).str.strip()
    return df


def etl_wip(df, fname):
    df = base_clean(df)

    # 1. Marca/Mes/Material (STOP/YOYO/DENIM)
    cols_clean = ["MARCA", "MES", "TIPO DE MATERIAL"]
    for c in cols_clean:
        if c in df.columns:
            df[c] = df[c].apply(clean_txt)

    # 2. Extraer Talla (T-14, T-TU)
    if "ITEM O.P. RESUMEN" in df.columns:
        df["TALLA"] = df["ITEM O.P. RESUMEN"].str.extract(r"(T-.*)$")[0].str.strip()

    # 3. Fechas y Números
    if "FECHA DE ENTREGA TELAS" in df.columns:
        df["FECHA DE ENTREGA TELAS"] = pd.to_datetime(
            df["FECHA DE ENTREGA TELAS"], errors="coerce", format="mixed"
        )

    for c in ["CANT. ORDENADA", "CANT. COMPLETA", "CANT. PENDIENTE"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # 4. Aging + Avance
    now = pd.Timestamp.now().normalize()
    df["DIAS_TALLER"] = (now - df["FECHA DE ENTREGA TELAS"]).dt.days.fillna(0)
    df["CRITICIDAD"] = df["DIAS_TALLER"].apply(
        lambda d: "NORMAL" if d <= 7 else ("ATENCION" if d <= 14 else "CRITICO")
    )
    df["AVANCE_%"] = (df["CANT. COMPLETA"] / df["CANT. ORDENADA"] * 100).fillna(0)

    return df
