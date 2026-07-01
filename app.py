import streamlit as st
import pandas as pd
import os
from agents.orchestrator import process_agentic_workflow

# UI Configuration
st.set_page_config(page_title="Perencana RPD AI - Version 1", layout="wide")
st.title("🤖 Asisten RPD Fiskal Agentic - Version 1")

@st.cache_data
def get_global_dataframe():
    path = "master_data.parquet"
    if os.path.exists(path):
        df = pd.read_parquet(path)
        
        # Restore critical data preprocessing
        if 'KDSATKER' in df.columns:
            df['KDSATKER'] = df['KDSATKER'].astype(str).str.strip().str.zfill(6)
        if 'KDDEPT' in df.columns:
            df['KDDEPT'] = df['KDDEPT'].astype(str).str.strip().str.zfill(3)
        if 'KDAKUN' in df.columns:
            df['KDAKUN'] = df['KDAKUN'].astype(str).str.strip()
        if 'YEAR' in df.columns:
            df['YEAR'] = pd.to_numeric(df['YEAR'], errors='coerce')
            
        for col in ['PAGU_DIPA', 'REAL', 'BLOKIR']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
        
    # Fallback dummy data if parquet is missing
    return pd.DataFrame({
        'KDSATKER': ['403812', '403812', '006817'],
        'YEAR': [2026, 2026, 2026],
        'PAGU_DIPA': [100000000, 50000000, 200000000],
        'BLOKIR': [0, 0, 0]
    })

df = get_global_dataframe()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Contoh: Cek RPD Satker 006817 dengan mutasi 2 pegawai"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Menganalisis permintaan...", expanded=True) as status:
            final_answer = ""
            for update in process_agentic_workflow(prompt, df):
                if "trace" in update:
                    st.write(update["trace"])
                if "final_answer" in update:
                    final_answer = update["final_answer"]
            
            status.update(label="Analisis Selesai", state="complete", expanded=False)
        
        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})
