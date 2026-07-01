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
        cols = ['KDSATKER', 'KDAKUN']
        for col in cols:
            if col in df.columns: df[col] = df[col].astype(str).str.strip()
        if 'KDSATKER' in df.columns: df['KDSATKER'] = df['KDSATKER'].str.zfill(6)
        if 'MONTH' not in df.columns: df['MONTH'] = 'JAN'
        return df
    
    # Menambahkan data simulasi tambahan untuk Satker 635329 saat file parquet tidak ada
    return pd.DataFrame({
        'KDSATKER': ['403812', '403812', '635329', '635329', '635329'],
        'YEAR': [2026, 2026, 2026, 2026, 2026],
        'KDAKUN': ['511111', '521111', '511111', '521111', '531111'],
        'PAGU_DIPA': [100000000, 50000000, 500000000, 150000000, 350000000],
        'BLOKIR': [0, 0, 0, 0, 0],
        'MONTH': ['JAN', 'JAN', 'JAN', 'JAN', 'JAN'],
        'REAL': [0, 0, 0, 0, 0]
    })

df = get_global_dataframe()

# Inisialisasi State Lengkap Version 1
if "agent_state" not in st.session_state:
    st.session_state.agent_state = {
        "satker": None, "mutasi": 0, "override_blokir_52": 0.0, "n_curr": 50, "plan_53_months": None
    }
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render Riwayat Obrolan
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Contoh: Atur belanja 53 Satker 635329 di bulan Maret dan Juni"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.markdown(prompt)

    with st.chat_message("assistant"):
        ui_payload = None  # Variabel untuk menampung data rendering UI
        
        with st.status("Memproses RPD...", expanded=True) as status:
            final_answer = ""
            past_history = st.session_state.messages[:-1]
            
            for update in process_agentic_workflow(prompt, df, st.session_state.agent_state, past_history):
                if "trace" in update: st.write(update["trace"])
                if "new_state" in update: st.session_state.agent_state = update["new_state"]
                if "ui_data" in update: ui_payload = update["ui_data"]
                if "final_answer" in update: final_answer = update["final_answer"]
            
            status.update(label="Selesai!", state="complete", expanded=False)
            
        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})
        
        # --- PEMULIHAN VISUAL BASE CODE (Rule: No Code Goes Missing) ---
        if ui_payload:
            st.divider()
            st.subheader(f"📊 Dashboard Visual RPD - Satker {ui_payload.get('satker_code')}")
            
            # 1. Metrik Pagu & Defisit (Dipisah per jenis belanja 51, 52, 53)
            st.write("### 💰 Ringkasan Pagu & Rencana")
            cols = st.columns(3)
            accs = ['51', '52', '53']
            p_ef_det = ui_payload.get('pagu_efektif_detail', {})
            plan_det = ui_payload.get('monthly_plan', {})
            
            for i, p in enumerate(accs):
                with cols[i]:
                    ef = p_ef_det.get(p, 0)
                    tot_plan = sum(month_data.get(p, 0) for month_data in plan_det.values())
                    selisih = ef - tot_plan
                    status_text = "Aman" if selisih >= 0 else "Defisit"
                    st.metric(label=f"Belanja {p} (Efektif)", value=f"Rp {ef:,.0f}")
                    st.caption(f"Total Rencana: Rp {tot_plan:,.0f} | {status_text} (Rp {selisih:,.0f})")

            # 2. Tabel RPD Dataframe Interaktif
            st.write("### 📅 Matriks Proyeksi Bulanan")
            df_plan = pd.DataFrame.from_dict(plan_det, orient='index')
            st.dataframe(df_plan.style.format("Rp {:,.0f}"), use_container_width=True)
            
            # 3. Analisis Capaian Target dengan HTML Box Berwarna
            st.write("### 🔍 Analisis Capaian Target Triwulan 1")
            res_cols = st.columns(3)
            targets = ui_payload.get('target_status', {})
            for i, p in enumerate(accs):
                with res_cols[i]:
                    st.markdown(f"**Progress {p}**")
                    t_info = targets.get(p, {})
                    actual = t_info.get('actual_pct', 0)
                    target = t_info.get('target_pct', 0)
                    status_txt = t_info.get('status', 'N/A')
                    st.write(f"Realisasi/Plan T1: {actual:.1%} (Target: {target:.1%})")
                    
                    if "GAGAL" in status_txt:
                        st.error(f"❌ **{status_txt}**")
                        st.markdown(f'<div style="background-color:#ff4b4b; padding:10px; border-radius:5px; color:white;">Membutuhkan akselerasi penyerapan!</div>', unsafe_allow_html=True)
                    else:
                        st.success(f"✅ **{status_txt}**")
                        st.markdown(f'<div style="background-color:#21c354; padding:10px; border-radius:5px; color:white;">Sesuai Trajektori</div>', unsafe_allow_html=True)
