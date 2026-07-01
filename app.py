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
        # Sanitasi Data
        cols = ['KDSATKER', 'KDAKUN']
        for col in cols:
            if col in df.columns: df[col] = df[col].astype(str).str.strip()
        if 'KDSATKER' in df.columns: df['KDSATKER'] = df['KDSATKER'].str.zfill(6)
        if 'MONTH' not in df.columns: df['MONTH'] = 'JAN' # Inject fallback
        return df
    return pd.DataFrame(columns=['KDSATKER', 'YEAR', 'PAGU_DIPA', 'BLOKIR', 'MONTH', 'REAL'])

df = get_global_dataframe()

# Inisialisasi State
if "agent_state" not in st.session_state:
    st.session_state.agent_state = {"satker": None, "mutasi": 0, "override_blokir_52": 0}
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Contoh: Buatkan RPD Satker 006817"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Memproses...", expanded=True) as status:
            final_answer = ""
            # Mengirimkan State eksplisit
            for update in process_agentic_workflow(prompt, df, st.session_state.agent_state):
                if "trace" in update: st.write(update["trace"])
                if "final_answer" in update: final_answer = update["final_answer"]
                if "new_state" in update: st.session_state.agent_state.update(update["new_state"])
            status.update(label="Selesai", state="complete", expanded=False)
        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})
