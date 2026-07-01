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

def calculate_rpd_forecast(df: pd.DataFrame, satker_code: str, mutasi_count: int = 0, n_curr: int = 50, override_blokir_52_pct: float = 0.0) -> dict:
    if df.empty:
        return {"error": "Dataframe is empty"}

    u_26 = df[(df['KDSATKER'] == satker_code) & (df['YEAR'] == 2026)]
    
    if u_26.empty:
        return {"error": f"No data found for Satker {satker_code} in 2026"}

    # Extract all historical data for this satker to build the DNA
    dna_all = get_granular_dna(df[df['KDSATKER'] == satker_code])
    
    akun_51_satker = u_26[u_26['KDAKUN'].str.startswith('51')]['KDAKUN'].unique()
    is_self_payer = any(akun for akun in akun_51_satker if akun not in NON_THR_51)

    pagu_efektif_map = {}
    pagu_bruto_map = {}
    pagu_blokir_map = {}
    account_prefixes = sorted(list(set(u_26['KDAKUN'].str[:2].unique())))
    final_recom = pd.DataFrame(index=MONTH_ORDER)

    # Global timeline anchor
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

    for prefix in account_prefixes:
        p_26 = u_26[u_26['KDAKUN'].str.startswith(prefix)]
        distinct_akuns = p_26['KDAKUN'].unique()
        prefix_projections = pd.DataFrame(0, index=MONTH_ORDER, columns=distinct_akuns)
        total_prefix_pagu = 0; total_prefix_blokir = 0

        for akun in distinct_akuns:
            a_data = p_26[p_26['KDAKUN'] == akun]
            snap = a_data[a_data['MONTH'] == latest_m]
            if snap.empty: snap = a_data.head(1)
            
            p_bruto = snap['PAGU_DIPA'].sum() if not snap.empty else 0
            p_blokir = snap['BLOKIR'].sum() if not snap.empty else 0
            
            # OVERRIDE: Menghitung ulang pemblokiran 52 berdasarkan persentase
            if prefix == '52' and override_blokir_52_pct > 0:
                calculated_blokir = p_bruto * (override_blokir_52_pct / 100.0)
                if calculated_blokir > p_blokir:
                    p_blokir = calculated_blokir
                    
            p_ef = round(max(0, p_bruto - p_blokir), 0)
            
            r_jan = a_data[a_data['MONTH'] == 'JAN']['REAL'].sum()
            r_to_date = a_data[a_data['MONTH'].isin(available_months)]['REAL'].sum()
            
            total_prefix_pagu += p_bruto
            total_prefix_blokir += p_blokir
            
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
                        base_val = pulse + (mutasi_count * unit_cost if (start_m_51 and in_chg and n_curr > 0) else 0)
                        if m in ['MAR', 'JUN'] and is_self_payer and dna['is_spike_prone']:
                            val = base_val * (1 + dna['spike'])
                        else:
                            val = base_val * (1 + dna['noise'].get(m, 0))
                        prefix_projections.at[m, akun] = round(val, 0)
            else:
                if sisa_ef > 0 and future_months:
                    raw_w = {m: dna['weights'].get(m, 0) for m in future_months}
                    tw = sum(raw_w.values())
                    w_map = {m: (v/tw if tw > 0 else 1/len(future_months)) for m, v in raw_w.items()}
                    rt = 0
                    for m in future_months[:-1]:
                        v = round(sisa_ef * w_map.get(m, 0), 0)
                        prefix_projections.at[m, akun] = v
                        rt += v
                    prefix_projections.at[future_months[-1], akun] = sisa_ef - rt

            for m in future_months:
                actual_so_far = a_data[a_data['MONTH'] == m]['REAL'].sum()
                if prefix_projections.at[m, akun] < actual_so_far:
                    prefix_projections.at[m, akun] = actual_so_far

        pagu_bruto_map[prefix] = total_prefix_pagu
        pagu_blokir_map[prefix] = total_prefix_blokir
        pagu_efektif_map[prefix] = round(max(0, total_prefix_pagu - total_prefix_blokir), 0)
        final_recom[f"Akun {prefix}"] = prefix_projections.sum(axis=1)

    summary = {
        "satker_code": satker_code,
        "is_self_payer": is_self_payer,
        "total_pagu_dipa": sum(pagu_bruto_map.values()),
        "total_pagu_efektif": sum(pagu_efektif_map.values()),
        "total_rencana_rpd": final_recom.sum().sum(),
        "detail_per_jenis_belanja": []
    }
    
    for p in account_prefixes:
        total_rencana = final_recom[f"Akun {p}"].sum()
        selisih = pagu_efektif_map[p] - total_rencana
        summary["detail_per_jenis_belanja"].append({
            "jenis_belanja": p,
            "pagu_efektif": pagu_efektif_map[p],
            "total_rencana": total_rencana,
            "selisih": selisih,
            "status": "Aman" if selisih >= 0 else f"Defisit Rp {abs(selisih):.0f}"
        })
        
    summary["monthly_projections"] = final_recom.to_dict(orient="index")
    return summary
