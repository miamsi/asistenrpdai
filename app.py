import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import json
# --- TAMBAHAN IMPORT MANDIRI UNTUK FITUR KONSULTAN ---
from groq import Groq

# --- 1. KONFIGURASI (Version 1) ---
st.set_page_config(page_title="Perencana RPD - Version 1", layout="wide")
MONTH_ORDER = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']

# Daftar akun 51 yang tidak digunakan untuk THR/Gaji-13
NON_THR_51 = [
    '511129', '512211', '511628', '512212', '511179'
]

@st.cache_data
def load_data():
    PATH = "master_data.parquet"
    if not os.path.exists(PATH): return pd.DataFrame()
    df = pd.read_parquet(PATH)
    df['KDSATKER'] = df['KDSATKER'].astype(str).str.strip().str.zfill(6)
    df['KDAKUN'] = df['KDAKUN'].astype(str).str.strip()
    df['YEAR'] = pd.to_numeric(df['YEAR'], errors='coerce')
    for col in ['PAGU_DIPA', 'REAL', 'BLOKIR']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# --- 1.A INISIALISASI STATE & FUNGSI ISOLASI KONSULTAN AI ---
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

def get_ai_consultant_json(messages_history, recom_df, pagu_map, current_q):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        
        # Ekstraksi matriks data operasional untuk dikirim ke LLM
        context_data = {
            "pagu_efektif_satker": pagu_map,
            "proposal_default_sistem": recom_df.to_dict(),
            "triwulan_berjalan_saat_ini": current_q
        }
        
        system_prompt = f"""Anda adalah Konsultan Perencana Anggaran Pemerintah yang sangat ahli, presisi, dan bijaksana.
Tugas Anda adalah menganalisis kekhawatiran, kendala lapangan, atau rencana perubahan yang diketik oleh pengguna.
Gunakan data acuan profil anggaran satker berikut untuk melakukan kalkulasi dampak:
{json.dumps(context_data)}

Kombinasikan riwayat percakapan dengan pesan terbaru untuk memberikan solusi mitigasi risiko.
Anda WAJIB memberikan respons HANYA dalam bentuk valid JSON Object dengan struktur persis seperti di bawah ini tanpa teks pengantar di luar JSON:
{{
  "analisis": "Analisis terukur mengenai dampak rencana user terhadap pagu efektif bulanan atau target triwulanan.",
  "risiko": ["Poin risiko atau peringatan kritis 1", "Poin risiko atau peringatan kritis 2"],
  "saran": "Rekomendasi taktis langkah perbaikan atau alternatif pergeseran bulan anggaran agar tetap aman."
}}
Gunakan Bahasa Indonesia formal yang profesional dan solutif."""

        payload = [{"role": "system", "content": system_prompt}]
        # Membawa konteks percakapan terakhir agar percakapan bersifat kontinu
        for msg in messages_history[-6:]:
            if isinstance(msg["content"], dict):
                # Jika pesan asisten berupa dict/json, ekstrak bagian analisis & saran untuk memori konteks
                text_content = f"Analisis: {msg['content'].get('analisis')}. Saran: {msg['content'].get('saran')}"
                payload.append({"role": msg["role"], "content": text_content})
            else:
                payload.append({"role": msg["role"], "content": str(msg["content"])})
                
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=payload,
            response_format={"type": "json_object"},
            temperature=0.4
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "analisis": f"Koneksi ke AI Consultant terganggu. Detail: {str(e)}",
            "risiko": ["Konfigurasi API Key di secrets.toml mungkin belum tepat atau kuota limit tercapai."],
            "saran": "Silakan periksa kembali berkas secrets.toml Anda."
        }

# --- 2. LOGIKA DNA FISKAL (Account-Specific Spike Detection) ---
def get_granular_dna(df_combined):
    dna_store = {}
    if df_combined.empty: return dna_store
    
    all_accounts = sorted(list(set(df_combined['KDAKUN'].unique())))
    
    for akun in all_accounts:
        weight_map = {m: [] for m in MONTH_ORDER}
        spike_ratios = []; noise_map = {m: [] for m in MONTH_ORDER}
        x_baseline_list = []
        is_account_spike_prone = False
        
        available_years = sorted([y for y in df_combined['YEAR'].unique() if y < 2026])
        for year in available_years:
            df_y = df_combined[(df_combined['YEAR'] == year) & (df_combined['KDAKUN'] == akun)]
            if df_y.empty: continue
            
            m_vals = df_y.groupby('MONTH')['REAL'].sum().reindex(MONTH_ORDER).fillna(0)
            sorted_v = m_vals.sort_values()
            x_base = sorted_v.iloc[1:-3].mean() if len(sorted_v) > 3 else 0
            
            if x_base > 0:
                x_baseline_list.append(x_base)
                spike_months_val = m_vals[['MAR', 'APR', 'JUN', 'JUL']].max()
                if spike_months_val > (x_base * 1.25): 
                    is_account_spike_prone = True
                
                if akun.startswith('51'):
                    spike_ratios.extend([(sorted_v.iloc[-1]-x_base)/x_base, (sorted_v.iloc[-2]-x_base)/x_base])
                    for m in MONTH_ORDER:
                        if m_vals[m] < sorted_v.iloc[-2]:
                            noise_map[m].append((m_vals[m]-x_base)/x_base)
                            
            total_y = m_vals.sum()
            if total_y > 0:
                for m in MONTH_ORDER: weight_map[m].append(m_vals[m] / total_y)
                            
        dna_store[akun] = {
            'weights': {m: np.median(v) if v else 0.0 for m, v in weight_map.items()},
            'spike': np.median(spike_ratios) if spike_ratios else 0.0,
            'noise': {m: np.median(v) if v else 0.0 for m, v in noise_map.items()},
            'x_fallback': np.median(x_baseline_list) if x_baseline_list else 0.0,
            'is_spike_prone': is_account_spike_prone
        }
    return dna_store

data = load_data()

if not data.empty:
    st.sidebar.header("🛠️ Konfigurasi Utama")
    all_satkers = sorted(data['KDSATKER'].unique())
    selected_current = st.sidebar.selectbox("Kode Satker 2026:", all_satkers)
    selected_old_list = st.sidebar.multiselect("Kode satker lama:", options=all_satkers, default=[])
    
    st.sidebar.divider()
    st.sidebar.subheader("🧪 Sandbox 51 (Pegawai)")
    n_curr = st.sidebar.number_input("Pegawai Riil (Januari):", min_value=0, value=0)
    n_chg = st.sidebar.number_input("Rencana Mutasi/CPNS (+/-):", value=0)
    start_m_51 = st.sidebar.selectbox("Bulan Mulai Perubahan 51:", MONTH_ORDER[1:], index=None)

    st.sidebar.subheader("📅 Sandbox 53 (Override)")
    sel_months_53 = st.sidebar.multiselect("Bulan Rencana Belanja 53:", MONTH_ORDER[1:], key="sb53")

    u_26 = data[(data['KDSATKER'] == selected_current) & (data['YEAR'] == 2026)]
    dna_all = get_granular_dna(data[data['KDSATKER'].isin(list(set([selected_current] + selected_old_list)))])
    
    if not u_26.empty:
        st.title(f"Proposal RPD 2026 - {selected_current}")
        
        # --- PERUBAHAN STRUKTUR TAB: EKSPANSI MENJADI 3 TAB TANPA MERUSAK STRUKTUR ---
        tab1, tab2, tab3 = st.tabs(["📊 Simulasi Rekomendasi", "⚡ Stress Test Usulan Satker", "🤖 Konsultan AI"])
        
        akun_51_satker = u_26[u_26['KDAKUN'].str.startswith('51')]['KDAKUN'].unique()
        is_self_payer = any(akun for akun in akun_51_satker if akun not in NON_THR_51)

        pagu_efektif_map = {}; real_jan_map = {}; pagu_bruto_map = {}; pagu_blokir_map = {}
        account_prefixes = sorted(list(set(u_26['KDAKUN'].str[:2].unique())))
        final_recom = pd.DataFrame(index=MONTH_ORDER)

        global_26 = data[data['YEAR'] == 2026]
        global_real_per_month = global_26.groupby('MONTH')['REAL'].sum()
        
        global_last_idx = 0
        for i, m in enumerate(MONTH_ORDER):
            if m in global_real_per_month.index and global_real_per_month[m] > 0:
                global_last_idx = i
                
        if global_last_idx <= 0:
            available_months = ['JAN'] 
        else:
            available_months = MONTH_ORDER[:global_last_idx]
            
        latest_m = available_months[-1]
        future_months = [m for m in MONTH_ORDER if m not in available_months]
        
        curr_month_idx = global_last_idx
        curr_q = (curr_month_idx // 3) + 1

        for prefix in account_prefixes:
            p_26 = u_26[u_26['KDAKUN'].str.startswith(prefix)]
            distinct_akuns = p_26['KDAKUN'].unique()
            prefix_projections = pd.DataFrame(0, index=MONTH_ORDER, columns=distinct_akuns)
            total_prefix_pagu = 0; total_prefix_blokir = 0; total_prefix_jan = 0

            for akun in distinct_akuns:
                a_data = p_26[p_26['KDAKUN'] == akun]
                snap = a_data[a_data['MONTH'] == latest_m]
                if snap.empty: snap = a_data.head(1)
                
                p_bruto = snap['PAGU_DIPA'].sum()
                p_blokir = snap['BLOKIR'].sum()
                p_ef = round(max(0, p_bruto - p_blokir), 0)
                
                r_jan = a_data[a_data['MONTH'] == 'JAN']['REAL'].sum()
                r_to_date = a_data[a_data['MONTH'].isin(available_months)]['REAL'].sum()
                
                total_prefix_pagu += p_bruto; total_prefix_blokir += p_blokir; total_prefix_jan += r_jan
                dna = dna_all.get(akun, {'weights': {}, 'spike': 0, 'noise': {}, 'x_fallback': 0, 'is_spike_prone': False})
                sisa_ef = max(0, p_ef - r_to_date)
                
                for m in available_months:
                    prefix_projections.at[m, akun] = a_data[a_data['MONTH'] == m]['REAL'].sum()
                
                if prefix == '51':
                    pulse = r_jan if r_jan > 0 else dna['x_fallback']
                    unit_cost = (pulse / n_curr) if n_curr > 0 else 0
                    in_chg = False
                    for m in MONTH_ORDER:
                        if m == start_m_51: in_chg = True
                        if m in future_months:
                            base_val = pulse + (n_chg * unit_cost if (start_m_51 and in_chg and n_curr > 0) else 0)
                            if m in ['MAR', 'JUN'] and is_self_payer and dna['is_spike_prone']:
                                val = base_val * (1 + dna['spike'])
                            else:
                                val = base_val * (1 + dna['noise'].get(m, 0))
                            prefix_projections.at[m, akun] = round(val, 0)
                
                elif prefix == '53':
                    if sel_months_53 and sisa_ef > 0 and future_months:
                        valid_sel_months = [m for m in sel_months_53 if m in future_months]
                        if valid_sel_months:
                            w_map = {m: (1/len(valid_sel_months) if m in valid_sel_months else 0) for m in future_months}
                            rt = 0
                            for m in future_months[:-1]:
                                v = round(sisa_ef * w_map.get(m, 0), 0); prefix_projections.at[m, akun] = v; rt += v
                            prefix_projections.at[future_months[-1], akun] = sisa_ef - rt
                else:
                    if sisa_ef > 0 and future_months:
                        raw_w = {m: dna['weights'].get(m, 0) for m in future_months}
                        tw = sum(raw_w.values()); w_map = {m: (v/tw if tw > 0 else 1/len(future_months)) for m, v in raw_w.items()}
                        rt = 0
                        for m in future_months[:-1]:
                            v = round(sisa_ef * w_map.get(m, 0), 0); prefix_projections.at[m, akun] = v; rt += v
                        prefix_projections.at[future_months[-1], akun] = sisa_ef - rt

                for m in future_months:
                    actual_so_far = a_data[a_data['MONTH'] == m]['REAL'].sum()
                    if prefix_projections.at[m, akun] < actual_so_far:
                        prefix_projections.at[m, akun] = actual_so_far

            pagu_bruto_map[prefix] = total_prefix_pagu
            pagu_blokir_map[prefix] = total_prefix_blokir
            pagu_efektif_map[prefix] = round(max(0, total_prefix_pagu - total_prefix_blokir), 0)
            real_jan_map[prefix] = total_prefix_jan
            final_recom[f"Akun {prefix}"] = prefix_projections.sum(axis=1)

        with tab1:
            st.subheader("Rekomendasi Berdasarkan Analisis Komponen Akun")
            if '51' in account_prefixes:
                if is_self_payer:
                    prone_akuns = [a for a in akun_51_satker if a not in NON_THR_51 and dna_all.get(a, {}).get('is_spike_prone')]
                    st.success(f"✅ **Status**: Satker membayar THR dan Gaji Ke-13 sendiri. Akun pemicu: {', '.join(prone_akuns)}")
                else:
                    st.warning("⚠️ **Status**: Satker terdeteksi tidak membayar THR dan Gaji Ke-13 mandiri (Hanya memiliki akun statis).")

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Pagu DIPA", f"Rp {sum(pagu_bruto_map.values()):,.0f}")
            m2.metric("Total Pagu Efektif", f"Rp {sum(pagu_efektif_map.values()):,.0f}")
            m3.metric("Total Rencana RPD", f"Rp {final_recom.sum().sum():,.0f}")
            
            detail_pagu_data = []
            for p in account_prefixes:
                total_rencana = final_recom[f"Akun {p}"].sum()
                selisih = pagu_efektif_map[p] - total_rencana
                status_keuangan = "OK" if selisih >= 0 else f"OVER Rp {abs(selisih):,.0f} ⚠️"
                detail_pagu_data.append({
                    "Akun": p, "Pagu Bruto": pagu_bruto_map[p], "Blokir": pagu_blokir_map[p],
                    "Pagu Efektif": pagu_efektif_map[p], "Total Rencana": total_rencana,
                    "Selisih Pagu": selisih, "Keterangan": status_keuangan
                })
            st.table(pd.DataFrame(detail_pagu_data).style.format("{:,.0f}", subset=["Pagu Bruto", "Blokir", "Pagu Efektif", "Total Rencana", "Selisih Pagu"]))

            recom_display = final_recom.copy()
            if 'Akun 53' in recom_display.columns and not sel_months_53:
                recom_display['Akun 53'] = recom_display['Akun 53'].astype(object)
                start_warn_m = future_months[0] if future_months else 'JAN'
                recom_display.at[start_warn_m, 'Akun 53'] = "⚠️ PILIH BULAN"
                for m in (future_months[1:] if future_months else []): recom_display.at[m, 'Akun 53'] = "-"

            def highlight_insufficient(df):
                style_df = pd.DataFrame('', index=df.index, columns=df.columns)
                for col in df.columns:
                    if "Akun" in col:
                        prefix = col.split(' ')[-1]
                        limit = pagu_efektif_map.get(prefix, 0)
                        numeric_vals = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        cum_sum = numeric_vals.cumsum()
                        style_df[col] = cum_sum.apply(lambda x: 'background-color: #ffcccc' if x > limit + 1 else '')
                return style_df

            st.dataframe(recom_display.style.apply(highlight_insufficient, axis=None).format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x), use_container_width=True)

        with tab2:
            q_months = MONTH_ORDER[(curr_q-1)*3 : curr_q*3]
            remaining_q_months = [m for m in q_months if m in future_months]
            
            st.subheader(f"⌨️ Uji Usulan Mandiri Satker (Triwulan {curr_q})")
            
            target_q_map = {
                1: {'51': 0.20, '52': 0.15, '53': 0.10, '57': 0.25},
                2: {'51': 0.50, '52': 0.50, '53': 0.40, '57': 0.50},
                3: {'51': 0.75, '52': 0.70, '53': 0.70, '57': 0.75},
                4: {'51': 1.00, '52': 1.00, '53': 1.00, '57': 1.00}
            }
            targets_map = target_q_map.get(curr_q, target_q_map[1])
            
            satker_plan = {}
            in_cols = st.columns(len(account_prefixes))
            for i, p in enumerate(account_prefixes):
                with in_cols[i]:
                    st.write(f"**Akun {p} (dalam ribuan)**")
                    plans = {}
                    for m in remaining_q_months:
                        raw = st.text_input(f"{m} ({p})", value="0", key=f"raw_{m}_{p}")
                        def clean_val(val_str):
                            try:
                                clean = val_str.replace('.', '').strip()
                                return float(clean) * 1000 if clean != "0" else 0.0
                            except: return 0.0
                        plans[m] = clean_val(raw)
                    satker_plan[p] = plans
            st.divider()
            summary_stress = []
            
            for p in account_prefixes:
                closed_q_months = [m for m in available_months if MONTH_ORDER.index(m) <= MONTH_ORDER.index(q_months[-1])]
                total_kom_past = u_26[(u_26['KDAKUN'].str.startswith(p)) & (u_26['MONTH'].isin(closed_q_months))]['REAL'].sum()
                
                total_q_plan = total_kom_past + sum(satker_plan[p].values())
                p_ef = pagu_efektif_map[p]
                
                row = {"Akun": p, "Pagu Efektif": p_ef, f"Total Komulatif {q_months[-1]}": total_q_plan}
                for pref, target in targets_map.items():
                    col_name = f"Target T{curr_q} ({int(target*100)}%)"
                    row[col_name] = p_ef * target if p == pref else np.nan
                summary_stress.append(row)
                
            df_stress = pd.DataFrame(summary_stress)
            st.table(df_stress.style.format("{:,.0f}", subset=[c for c in df_stress.columns if c != "Akun"], na_rep="-"))
            
            st.write("### 🔍 Analisis Capaian Target")
            res_cols = st.columns(len(account_prefixes))
            for i, p in enumerate(account_prefixes):
                with res_cols[i]:
                    p_ef = pagu_efektif_map[p]
                    tar_pct = targets_map.get(p, 0.15)
                    nominal_target = p_ef * tar_pct
                    
                    closed_q_months = [m for m in available_months if MONTH_ORDER.index(m) <= MONTH_ORDER.index(q_months[-1])]
                    total_kom_past = u_26[(u_26['KDAKUN'].str.startswith(p)) & (u_26['MONTH'].isin(closed_q_months))]['REAL'].sum()
                    
                    total_q_plan = total_kom_past + sum(satker_plan[p].values())
                    act_pct = total_q_plan / p_ef if p_ef > 0 else 0
                    
                    st.metric(f"Progress {p}", f"{act_pct:.1%}", f"{(act_pct - tar_pct):+.1%}")
                    if (nominal_target - total_q_plan) > 1:
                        st.error(f"❌ **GAGAL T{curr_q}**")
                        st.markdown(f'<div style="background-color:#ff4b4b; padding:10px; border-radius:5px; color:white;">🚨 <b>Kurang: Rp {(nominal_target - total_q_plan):,.0f}</b></div>', unsafe_allow_html=True)
                    elif p_ef > 0: 
                        st.success(f"✅ **LULUS T{curr_q}**")
                        
        # --- TAB 3: ISOLASI TOTAL FITUR KONSULTAN AI INTERAKTIF (JSON MODE) ---
        with tab3:
            st.subheader("🤖 Konsultan Obrolan RPD AI")
            st.caption("Gunakan ruang ini untuk mendiskusikan rencana taktis atau kendala realisasi di lapangan secara interaktif.")
            
            # Merender seluruh riwayat percakapan dari session state (Conversational UI)
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    if msg["role"] == "user":
                        st.markdown(msg["content"])
                    else:
                        # Parsing data terstruktur JSON yang disimpan di dalam state
                        data_json = msg["content"]
                        st.markdown(f"**🔍 Analisis:** {data_json.get('analisis', '')}")
                        st.markdown("**⚠️ Risiko & Peringatan Pagu:**")
                        for r in data_json.get('risiko', []):
                            st.markdown(f"- {r}")
                        st.markdown(f"**💡 Rekomendasi Solusi:** {data_json.get('saran', '')}")
            
            # Komponen Chat Input Native Streamlit
            if user_input := st.chat_input("Contoh: Rencana pencairan belanja modal 53 diundur seluruhnya ke Oktober karena lelang ulang..."):
                # 1. Tampilkan input user secara instan
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state.chat_messages.append({"role": "user", "content": user_input})
                
                # 2. Ambil respons terstruktur dari Groq JSON Mode
                with st.chat_message("assistant"):
                    with st.spinner("Mengalkulasi dampak fiskal terhadap target triwulan..."):
                        res_json = get_ai_consultant_json(
                            messages_history=st.session_state.chat_messages,
                            recom_df=final_recom,
                            pagu_map=pagu_efektif_map,
                            current_q=curr_q
                        )
                        
                        st.markdown(f"**🔍 Analisis:** {res_json.get('analisis', '')}")
                        st.markdown("**⚠️ Risiko & Peringatan Pagu:**")
                        for r in res_json.get('risiko', []):
                            st.markdown(f"- {r}")
                        st.markdown(f"**💡 Rekomendasi Solusi:** {res_json.get('saran', '')}")
                
                # 3. Simpan objek JSON ke dalam state dan segarkan komponen halaman
                st.session_state.chat_messages.append({"role": "assistant", "content": res_json})
                st.rerun()

    else: st.warning("Data 2026 tidak ditemukan.")
else: st.error("File master_data.parquet tidak ditemukan.")
