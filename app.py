import streamlit as st
import pandas as pd
import os
from agents.orchestrator import process_agentic_workflow

st.set_page_config(page_title="Perencana RPD AI", layout="wide")
st.title("🤖 Asisten RPD Fiskal Agentic")

# Singleton Data Loader
@st.cache_resource
def get_global_dataframe():
    path = "master_data.parquet"
    if os.path.exists(path):
        return pd.read_parquet(path)
    # Return dummy data for testing if file doesn't exist
    return pd.DataFrame({
        'KDSATKER': ['403812', '403812'],
        'YEAR': [2026, 2026],
        'PAGU_DIPA': [100000000, 50000000],
        'BLOKIR': [0, 0]
    })

df = get_global_dataframe()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Contoh: Cek RPD Satker 403812 dengan mutasi 2 pegawai"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # The Reasoning Trace UI
        with st.status("Menganalisis permintaan...", expanded=True) as status:
            final_answer = ""
            # Iterate through the generator from the orchestrator
            for update in process_agentic_workflow(prompt, df):
                if "trace" in update:
                    st.write(update["trace"])
                if "final_answer" in update:
                    final_answer = update["final_answer"]
            
            status.update(label="Analisis Selesai", state="complete", expanded=False)
        
        # Display the final synthesized answer
        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})
