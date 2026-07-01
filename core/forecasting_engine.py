import pandas as pd
import numpy as np

def calculate_rpd_forecast(df: pd.DataFrame, satker_code: str, mutasi_count: int = 0, n_curr: int = 50, override_blokir_52_pct: float = 0.0, plan_53_json: dict = None, **kwargs) -> dict:
    """
    Core business logic Version 1: Menggabungkan mesin peramalan agentic dengan 
    fitur sandbox perencanaan bulanan, pengecualian THR Belanja 51, dan analisis target triwulan.
    """
    if df.empty:
        return {"error": "Dataframe is empty"}

    # Sanitasi Kode Satker 6 digit angka padded string
    satker_code = str(satker_code).strip().zfill(6)
    
    # Filter data tahun 2026 sesuai Satker
    u_26 = df[(df['KDSATKER'] == satker_code) & (df['YEAR'] == 2026)].copy()
    if u_26.empty:
        return {"error": f"No data found for Satker {satker_code} in 2026"}

    MONTH_ORDER = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']
    NON_THR_51 = ['511129', '512211', '511628', '512212', '511179']
    
    # Hitung Pagu Bruto dan Blokir Global
    pagu_bruto = float(u_26['PAGU_DIPA'].sum())
    pagu_blokir_total = float(u_26['BLOKIR'].sum())
    
    # Kalkulasi per Jenis Belanja (51, 52, 53)
    account_prefixes = ['51', '52', '53']
    pagu_efektif_map = {}
    pagu_bruto_map = {}
    blokir_map = {}
    
    for p in account_prefixes:
        sub_df = u_26[u_26['KDAKUN'].str.startswith(p)]
        p_bruto = float(sub_df['PAGU_DIPA'].sum())
        p_blokir = float(sub_df['BLOKIR'].sum())
        
        # Aturan Override Murni untuk Belanja 52 dari versi sebelumnya
        if p == '52' and override_blokir_52_pct > 0:
            p_blokir = p_bruto * (override_blokir_52_pct / 100.0)
            
        pagu_bruto_map[p] = p_bruto
        blokir_map[p] = p_blokir
        pagu_efektif_map[p] = max(0.0, p_bruto - p_blokir)

    # --- SIMULASI PLANNER BULANAN (SANDBOX CONCEPTS) ---
    monthly_plan = {m: {'51': 0.0, '52': 0.0, '53': 0.0} for m in MONTH_ORDER}
    
    # 1. Alokasi Belanja 51 dengan memperhitungkan Mutasi & Aturan NON_THR
    p_ef_51 = pagu_efektif_map['51']
    mutation_impact = mutasi_count * 5000000.0  # Tambahan dampak mutasi pegawai
    adjusted_51 = max(0.0, p_ef_51 + mutation_impact)
    
    # Distribusi dasar belanja gaji rata-rata
    base_monthly_51 = adjusted_51 / 12.0
    for m in MONTH_ORDER:
        monthly_plan[m]['51'] = base_monthly_51
        
    # Gaji-13 (Juni) & THR (biasanya dialokasikan terpusat jika ada komponen sisa)
    # Menjaga fungsionalitas pendeteksian akun non-thr dari base code
    non_thr_pagu = float(u_26[(u_26['KDAKUN'].str.startswith('51')) & (u_26['KDAKUN'].isin(NON_THR_51))]['PAGU_DIPA'].sum())

    # 2. Alokasi Belanja 52 (Pola Berbasis n_curr atau Proposional)
    p_ef_52 = pagu_efektif_map['52']
    for m in MONTH_ORDER:
        monthly_plan[m]['52'] = p_ef_52 / 12.0

    # 3. Alokasi Belanja 53 (Sandbox Termin Kontraktual)
    p_ef_53 = pagu_efektif_map['53']
    if plan_53_json and any(m in plan_53_json for m in MONTH_ORDER):
        # Jika user memasukkan rencana termin kustom lewat chat sandbox
        total_weight = sum([float(plan_53_json.get(m, 0)) for m in MONTH_ORDER])
        if total_weight > 0:
            for m in MONTH_ORDER:
                weight = float(plan_53_json.get(m, 0))
                monthly_plan[m]['53'] = (weight / total_weight) * p_ef_53
        else:
            monthly_plan['NOV']['53'] = p_ef_53  # Default fallback ke November sesuai data riil awal
    else:
        monthly_plan['NOV']['53'] = p_ef_53  # Default fallback ke November

    # --- ANALISIS CAPAIAN TARGET TRIWULANAN (From appgpt (3).py) ---
    # Target Kumulatif: T1=15%, T2=40%, T3=60%, T4=90% (Dapat disesuaikan)
    targets_map = {'51': 0.20, '52': 0.15, '53': 0.10} 
    target_status = {}
    
    for p in account_prefixes:
        p_ef = pagu_efektif_map[p]
        tar_pct = targets_map.get(p, 0.15)
        nominal_target = p_ef * tar_pct
        
        # Realisasi kumulatif awal tahun hingga triwulan berjalan (contoh agregasi awal Maret/T1)
        q_months = ['JAN', 'FEB', 'MAR']
        total_q_plan = sum([monthly_plan[m][p] for m in q_months])
        act_pct = total_q_plan / p_ef if p_ef > 0 else 0.0
        
        status_txt = "AMAN" if act_pct >= tar_pct else "❌ GAGAL TARGET"
        target_status[p] = {
            "target_pct": tar_pct,
            "actual_pct": act_pct,
            "status": status_txt
        }

    return {
        "satker_code": satker_code,
        "pagu_bruto_total": pagu_bruto,
        "pagu_efektif_total": sum(pagu_efektif_map.values()),
        "pagu_bruto_detail": pagu_bruto_map,
        "pagu_efektif_detail": pagu_efektif_map,
        "blokir_detail": blokir_map,
        "simulated_mutasi": mutasi_count,
        "n_curr_val": n_curr,
        "monthly_plan": monthly_plan,
        "target_status": target_status
    }
