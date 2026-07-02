import pandas as pd
import numpy as np

MONTH_ORDER = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']
NON_THR_51 = ['511129', '512211', '511628', '512212', '511179']

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

def calculate_rpd_forecast(df: pd.DataFrame, satker_code: str, mutasi_count: int = 0, n_curr: int = 50, override_blokir_52_pct: float = 0.0, plan_53_json: dict = None, **kwargs) -> dict:
    if df.empty:
        return {"error": "Dataframe is empty"}

    satker_code = str(satker_code).strip().zfill(6)
    u_26 = df[(df['KDSATKER'] == satker_code) & (df['YEAR'] == 2026)]
    
    if u_26.empty:
        return {"error": f"No data found for Satker {satker_code} in 2026"}

    # Ekstraksi seluruh DNA Satker
    dna_all = get_granular_dna(df[df['KDSATKER'] == satker_code])
    
    akun_51_satker = u_26[u_26['KDAKUN'].str.startswith('51')]['KDAKUN'].unique()
    is_self_payer = any(akun for akun in akun_51_satker if akun not in NON_THR_51)

    pagu_efektif_map = {}; pagu_bruto_map = {}; blokir_map = {}
    account_prefixes = sorted(list(set(u_26['KDAKUN'].str[:2].unique())))
    
    # 1. GLOBAL TIMELINE ANCHOR (Sinkronisasi dari Base Code)
    global_26 = df[df['YEAR'] == 2026]
    global_real_per_month = global_26.groupby('MONTH')['REAL'].sum()
    
    global_last_idx = 0
    for i, m in enumerate(MONTH_ORDER):
        if m in global_real_per_month.index and global_real_per_month[m] > 0:
            global_last_idx = i
            
    available_months = ['JAN'] if global_last_idx <= 0 else MONTH_ORDER[:global_last_idx]
    latest_m = available_months[-1]
    future_months = [m for m in MONTH_ORDER if m not in available_months]
    start_m_51 = future_months[0] if future_months else None

    # Inisialisasi struktur plan bulanan
    monthly_plan = {m: {p: 0.0 for p in account_prefixes} for m in MONTH_ORDER}

    for prefix in account_prefixes:
        p_26 = u_26[u_26['KDAKUN'].str.startswith(prefix)]
        distinct_akuns = p_26['KDAKUN'].unique()
        prefix_projections = pd.DataFrame(0.0, index=MONTH_ORDER, columns=distinct_akuns)
        total_prefix_pagu = 0.0; total_prefix_blokir = 0.0

        for akun in distinct_akuns:
            a_data = p_26[p_26['KDAKUN'] == akun]
            snap = a_data[a_data['MONTH'] == latest_m]
            if snap.empty: snap = a_data.head(1)
            
            p_bruto = float(snap['PAGU_DIPA'].sum()) if not snap.empty else 0.0
            p_blokir = float(snap['BLOKIR'].sum()) if not snap.empty else 0.0
            
            # OVERRIDE MURNI
            if prefix == '52' and override_blokir_52_pct > 0:
                p_blokir = p_bruto * (override_blokir_52_pct / 100.0)
                    
            p_ef = round(max(0, p_bruto - p_blokir), 0)
            
            r_jan = float(a_data[a_data['MONTH'] == 'JAN']['REAL'].sum())
            r_to_date = float(a_data[a_data['MONTH'].isin(available_months)]['REAL'].sum())
            
            total_prefix_pagu += p_bruto
            total_prefix_blokir += p_blokir
            
            dna = dna_all.get(akun, {'weights': {}, 'spike': 0, 'noise': {}, 'x_fallback': 0, 'is_spike_prone': False})
            sisa_ef = max(0.0, p_ef - r_to_date)
            
            # 2. PENGUNCIAN BULAN LALU (Strict Actuals)
            for m in available_months:
                prefix_projections.at[m, akun] = float(a_data[a_data['MONTH'] == m]['REAL'].sum())
            
            # 3. PROYEKSI MASA DEPAN BERDASARKAN DNA (Bukan lagi / 12)
            if prefix == '51':
                pulse = r_jan if r_jan > 0 else dna['x_fallback']
                unit_cost = (pulse / n_curr) if n_curr > 0 else 0
                in_chg = False
                for m in MONTH_ORDER:
                    if m == start_m_51: in_chg = True
                    if m in future_months:
                        base_val = pulse + (mutasi_count * unit_cost if (start_m_51 and in_chg and n_curr > 0) else 0)
                        if m in ['MAR', 'JUN'] and is_self_payer and dna['is_spike_prone']:
                            val = base_val * (1 + dna['spike'])
                        else:
                            val = base_val * (1 + dna['noise'].get(m, 0))
                        prefix_projections.at[m, akun] = round(val, 0)
                        
            elif prefix == '53':
                if plan_53_json and sisa_ef > 0 and future_months:
                    valid_sel_months = [m for m in plan_53_json.keys() if m in future_months]
                    if valid_sel_months:
                        w_map = {m: (1/len(valid_sel_months) if m in valid_sel_months else 0) for m in future_months}
                        rt = 0.0
                        for m in future_months[:-1]:
                            v = round(sisa_ef * w_map.get(m, 0), 0)
                            prefix_projections.at[m, akun] = v
                            rt += v
                        prefix_projections.at[future_months[-1], akun] = sisa_ef - rt
                # Jika tidak ada plan_53, biarkan 0 agar memicu status defisit/kosong.
                
            else:
                # Akun 52 dan 57
                if sisa_ef > 0 and future_months:
                    raw_w = {m: dna['weights'].get(m, 0) for m in future_months}
                    tw = sum(raw_w.values())
                    w_map = {m: (v/tw if tw > 0 else 1/len(future_months)) for m, v in raw_w.items()}
                    rt = 0.0
                    for m in future_months[:-1]:
                        v = round(sisa_ef * w_map.get(m, 0), 0)
                        prefix_projections.at[m, akun] = v
                        rt += v
                    prefix_projections.at[future_months[-1], akun] = sisa_ef - rt

            # 4. ONGOING MONTH SAFEGUARD
            for m in future_months:
                actual_so_far = float(a_data[a_data['MONTH'] == m]['REAL'].sum())
                if prefix_projections.at[m, akun] < actual_so_far:
                    prefix_projections.at[m, akun] = actual_so_far

        pagu_bruto_map[prefix] = total_prefix_pagu
        blokir_map[prefix] = total_prefix_blokir
        pagu_efektif_map[prefix] = round(max(0, total_prefix_pagu - total_prefix_blokir), 0)
        
        # Agregasi ke monthly_plan
        for m in MONTH_ORDER:
            monthly_plan[m][prefix] = float(prefix_projections.loc[m].sum())

    # 5. DETEKSI TRIWULAN DINAMIS (Bukan Hardcode T1)
    curr_q = (global_last_idx // 3) + 1
    q_months = MONTH_ORDER[(curr_q-1)*3 : curr_q*3]
    
    target_q_map = {
        1: {'51': 0.20, '52': 0.15, '53': 0.10, '57': 0.25},
        2: {'51': 0.50, '52': 0.50, '53': 0.40, '57': 0.50},
        3: {'51': 0.75, '52': 0.70, '53': 0.70, '57': 0.75},
        4: {'51': 1.00, '52': 1.00, '53': 1.00, '57': 1.00}
    }
    targets_map = target_q_map.get(curr_q, target_q_map[1])
    target_status = {}
    
    for p in account_prefixes:
        p_ef = pagu_efektif_map[p]
        tar_pct = targets_map.get(p, 0.15)
        
        # Evaluasi kumulatif dari Januari hingga bulan terakhir di kuartal aktif
        eval_months = MONTH_ORDER[:MONTH_ORDER.index(q_months[-1])+1]
        total_q_plan = sum([monthly_plan[m][p] for m in eval_months])
        act_pct = total_q_plan / p_ef if p_ef > 0 else 0.0
        
        status_txt = "AMAN" if act_pct >= tar_pct else "❌ GAGAL TARGET"
        target_status[p] = {
            "target_pct": tar_pct,
            "actual_pct": act_pct,
            "status": status_txt
        }

    return {
        "satker_code": satker_code,
        "pagu_bruto_total": sum(pagu_bruto_map.values()),
        "pagu_efektif_total": sum(pagu_efektif_map.values()),
        "pagu_efektif_detail": pagu_efektif_map,
        "monthly_plan": monthly_plan,
        "target_status": target_status,
        "current_quarter": curr_q
    }
