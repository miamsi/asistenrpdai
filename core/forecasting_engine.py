def calculate_rpd_forecast(df, satker_code, override_blokir_52_pct=0.0, **kwargs):
    # ... (logika filter data)
    
    # Logic Override murni
    if override_blokir_52_pct > 0:
        p_blokir = p_bruto * (override_blokir_52_pct / 100.0)
    
    # ... (sisa kalkulasi)
    return summary
