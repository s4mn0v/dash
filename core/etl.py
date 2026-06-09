import os
import re

import pandas as pd


def normalize_cols(df):
    df.columns = [re.sub(r"\s+", " ", str(c).strip().upper()) for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^UNNAMED")]
    return df.loc[:, ~df.columns.duplicated()]


def clean_data_values(df, filename):
    if "MARCA" not in df.columns:
        if "STOP" in filename.upper():
            df["MARCA"] = "STOP"
        elif "YOYO" in filename.upper():
            df["MARCA"] = "YOYO"
        else:
            df["MARCA"] = "DESCONOCIDO"

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(
                lambda x: (
                    re.sub(r"^\d+\s*-\s*", "", str(x)).strip().upper()
                    if pd.notna(x)
                    else x
                )
            )

    num_cols = [
        "CANT. PLANEADA",
        "CANT. ORDENADA",
        "CANT. COMPLETA",
        "CANT. PENDIENTE",
        "CANT.COMPLETA",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(0).astype(int)

    date_cols = ["FECHA TERMINACIÓN", "FECHA CREACIÓN", "FECHA APROBACIÓN"]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
    return df


def get_consolidated_df(path):
    files = [f for f in os.listdir(path) if f.endswith(".csv")]
    if not files:
        return None
    all_dfs = []
    for f in files:
        df = pd.read_csv(os.path.join(path, f))
        df = normalize_cols(df)
        df = clean_data_values(df, f)
        all_dfs.append(df)
    return pd.concat(all_dfs, axis=0, ignore_index=True).loc[
        :, ~pd.concat(all_dfs, axis=0, ignore_index=True).columns.duplicated()
    ]


def base_clean(df):
    df.columns = [re.sub(r"\s+", " ", str(c).strip().upper()) for c in df.columns]
    return df.loc[:, ~df.columns.duplicated()]


def clean_txt(val):
    if pd.isna(val):
        return val
    return re.sub(r"^\d+\s*-\s*", "", str(val)).strip().upper()
