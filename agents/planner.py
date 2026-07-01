import re

def generate_plan(user_query: str, state: dict, chat_history: list) -> tuple:
    """
    Menganalisis teks input user secara kontekstual, memperbarui state sandbox, 
    dan menyusun instruksi eksekusi untuk core engine.
    """
    new_state = state.copy()
    
    # Ekstraksi kode Satker 6 digit
    satker_match = re.search(r'\b\d{6}\b', user_query)
    if satker_match:
        new_state["satker"] = satker_match.group(0)
        
    # Ekstraksi override blokir persen
    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', user_query)
    if pct_match:
        new_state["override_blokir_52"] = float(pct_match.group(1))

    # --- FITUR INTERAKTIF SANDBOX TERMIN BELANJA 53 ---
    months_pattern = r'(JAN|FEB|MAR|APR|MEI|JUN|JUL|AGS|SEP|OKT|NOV|DES)'
    found_months = re.findall(months_pattern, user_query.upper())
    
    if "53" in user_query and found_months:
        if "plan_53_months" not in new_state or not isinstance(new_state["plan_53_months"], dict):
            new_state["plan_53_months"] = {}
        # Set bobot yang sama untuk setiap bulan yang disebutkan
        new_state["plan_53_months"] = {m: 1 for m in found_months}

    # Jika Satker belum ada, minta input Satker
    if not new_state["satker"] or len(new_state["satker"]) != 6:
        return None, new_state
        
    tool_call = {
        "tool": "run_forecast_simulation",
        "args": {
            "satker_code": new_state["satker"],
            "mutasi_count": new_state.get("mutasi", 0),
            "n_curr": new_state.get("n_curr", 50),
            "override_blokir_52_pct": new_state.get("override_blokir_52", 0.0),
            "plan_53_months": new_state.get("plan_53_months", None)
        }
    }
    return [tool_call], new_state
