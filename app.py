import streamlit as st
import pandas as pd
import os
from agents.orchestrator import process_agentic_workflow

st.set_page_config(page_title="Perencana RPD AI - Version 1", layout="wide")
st.title("🤖 Asisten RPD Fiskal Agentic - Version 1")

@st.cache_resource
def get_global_dataframe():
    path = "master_data.parquet"
    if os.path.exists(path):
        df = pd.read_parquet(path)
        # Sesuai regulasi data pemerintah: pastikan padding teks aman
        cols = ['KDSATKER', 'KDAKUN', 'KDDEPT']
        for col in cols:
            if col in df.columns: 
                df[col] = df[col].astype(str).str.strip()
        if 'KDSATKER' in df.columns: 
            df['KDSATKER'] = df['KDSATKER'].str.zfill(6)
        if 'KDDEPT' in df.columns: 
            df['KDDEPT'] = df['KDDEPT'].str.zfill(3)
        if 'MONTH' not in df.columns: 
            df['MONTH'] = 'JAN'
            
        for col in ['PAGU_DIPA', 'REAL', 'BLOKIR']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
        
    # Validasi Tinjauan Arsitektur: Pastikan kolom MONTH tersedia agar fallback tidak crash
    return pd.DataFrame({
        'KDSATKER': ['006817'],
        'KDDEPT': ['004'],
        'KDAKUN': ['511111'],
        'YEAR': [2026],
        'PAGU_DIPA': [70250129000],
        'BLOKIR': [0],
        'MONTH': ['JAN'],
        'REAL': [0]
    })

df = get_global_dataframe()

# Inisialisasi State Eksplisit untuk Manajemen Memori yang Kuat
if "agent_state" not in st.session_state:
    st.session_state.agent_state = {"satker": None, "mutasi": 0, "override_blokir_52": 0.0}
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan riwayat chat di UI
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Contoh: Buatkan RPD Satker 006817"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Memproses analisis fiskal...", expanded=True) as status:
            final_answer = ""
            # Memisahkan pengiriman prompt aktif dengan histori masa lalu
            past_history = st.session_state.messages[:-1]
            
            for update in process_agentic_workflow(prompt, df, st.session_state.agent_state, past_history):
                if "trace" in update: 
                    st.write(update["trace"])
                if "final_answer" in update: 
                    final_answer = update["final_answer"]
                if "new_state" in update: 
                    st.session_state.agent_state.update(update["new_state"])
            status.update(label="Selesai", state="complete", expanded=False)
            
        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})
