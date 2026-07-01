import pandas as pd
import numpy as np

def calculate_rpd_forecast(df: pd.DataFrame, satker_code: str, mutasi_count: int = 0) -> dict:
    """
    Core business logic for calculating the RPD forecast.
    """
    if df.empty:
        return {"error": "Dataframe is empty"}

    # Filter for the specific Satker and Year (hardcoded to 2026 for this example)
    u_26 = df[(df['KDSATKER'] == satker_code) & (df['YEAR'] == 2026)]
    
    if u_26.empty:
        return {"error": f"No data found for Satker {satker_code} in 2026"}

    pagu_bruto = float(u_26['PAGU_DIPA'].sum())
    pagu_blokir = float(u_26['BLOKIR'].sum())
    pagu_efektif = max(0, pagu_bruto - pagu_blokir)

    # Simplified forecast simulation logic
    base_forecast = pagu_efektif * 0.8 
    mutation_impact = mutasi_count * 5000000  # Assuming 5M IDR per employee
    adjusted_forecast = base_forecast + mutation_impact

    return {
        "satker_code": satker_code,
        "pagu_efektif": pagu_efektif,
        "simulated_mutasi": mutasi_count,
        "projected_rpd_total": adjusted_forecast,
        "status": "Target achievable" if adjusted_forecast <= pagu_efektif else "Warning: Over budget"
    }
