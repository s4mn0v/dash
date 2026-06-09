import streamlit as st
import pandas as pd
import os
import re

PATH = "data/pending"
os.makedirs(PATH, exist_ok=True)

def clean_cols(df):
    # Strip, Upper, and collapse all internal whitespace to single space
    df.columns = [re.sub(r'\s+', ' ', str(c).strip().upper()) for c in df.columns]
    # Remove "UNNAMED" columns often found in XLS
    df = df.loc[:, ~df.columns.str.contains('^UNNAMED')]
    # Dedupe columns
    return df.loc[:, ~df.columns.duplicated()]

st.title("XLS Dashboard")

# 1. Upload
st.sidebar.header("Upload")
files = st.sidebar.file_uploader("XLS Files", type="xls", accept_multiple_files=True)

if st.sidebar.button("Convert"):
    for f in files:
        df = pd.read_excel(f)
        df = clean_cols(df)
        
        # Strict Exclude
        excl = ["MES ADELANTO", "GRUPO DE ENTREGA", "LINEA", "TIPO DE ABASTECIMIENTO"]
        
        # Logic: ffill everything else
        fill_cols = [c for c in df.columns if c not in excl]
        df[fill_cols] = df[fill_cols].ffill()
        
        # Save CSV - no index
        name = f.name.rsplit(".", 1)[0] + ".csv"
        df.to_csv(os.path.join(PATH, name), index=False)
    st.sidebar.success("Done")

# 2. View
st.header("Data")
if st.button("Refresh"):
    csv_files = [f for f in os.listdir(PATH) if f.endswith(".csv")]
    if csv_files:
        all_dfs = []
        for f in csv_files:
            tmp = pd.read_csv(os.path.join(PATH, f))
            tmp = clean_cols(tmp) # Clean again to be 100% sure
            all_dfs.append(tmp)
            
        # Concat merges identical column names
        final = pd.concat(all_dfs, axis=0, ignore_index=True)
        # Final dedupe check for MARCA
        final = final.loc[:, ~final.columns.duplicated()]
        
        st.dataframe(final)
