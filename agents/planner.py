import json
from groq import Groq
import streamlit as st

def generate_plan(user_query, state):
    # Logika inferensi state dari user_query
    # (Di sini Anda bisa menambahkan regex atau parsing sederhana)
    new_state = state.copy()
    if "006817" in user_query: new_state["satker"] = "006817"
    if "7%" in user_query: new_state["override_blokir_52"] = 7.0
    
    # Validasi Satker
    if not new_state["satker"] or len(new_state["satker"]) != 6:
        return None, new_state
        
    tool_call = {
        "tool": "run_forecast_simulation",
        "args": {
            "satker_code": new_state["satker"],
            "override_blokir_52_pct": new_state["override_blokir_52"]
        }
    }
    return [tool_call], new_state
