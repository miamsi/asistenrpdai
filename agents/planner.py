import json
import re
from groq import Groq
import streamlit as st
from tools.registry import AVAILABLE_TOOLS_SCHEMAS

def generate_plan(user_query, state, chat_history):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    new_state = state.copy()
    
    system_prompt = f"""
    Anda adalah modul perencana agen finansial. Tugas Anda adalah menentukan apakah aplikasi harus mengeksekusi fungsi simulasi RPD.
    Anda dibekali State Memori Aplikasi saat ini:
    - Satker Terpilih Sebelumnya: {new_state.get('satker')}
    - Nilai Mutasi Pegawai: {new_state.get('mutasi')}
    - Persentase Blokir Belanja 52: {new_state.get('override_blokir_52')}%

    Gunakan data di atas untuk melengkapi parameter jika user memberikan perintah lanjutan yang tidak menyebutkan ulang kode Satker (contoh: "tambahkan blokir menjadi 5%").
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-4:]:
        if msg["role"] in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_query})
    
    response = client.chat.completions.create(
        model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=messages,
        tools=AVAILABLE_TOOLS_SCHEMAS,
        tool_choice="auto"
    )
    
    plan = []
    message = response.choices[0].message
    
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "run_forecast_simulation":
                try:
                    args = json.loads(tool_call.function.arguments)
                    
                    # Sinkronisasi Terarah Berbasis State & Parameter Validasi
                    satker = args.get("satker_code") or new_state.get("satker")
                    mutasi = args.get("mutasi_count") if args.get("mutasi_count") is not None else new_state.get("mutasi", 0)
                    override_blokir = args.get("override_blokir_52_pct") if args.get("override_blokir_52_pct") is not None else new_state.get("override_blokir_52", 0.0)
                    
                    if satker:
                        satker = str(satker).strip().zfill(6)
                        if len(satker) == 6 and satker.isdigit():
                            new_state["satker"] = satker
                        else:
                            satker = None
                            
                    new_state["mutasi"] = int(mutasi)
                    new_state["override_blokir_52"] = float(override_blokir)
                    
                    if new_state["satker"]:
                        plan.append({
                            "tool": "run_forecast_simulation",
                            "args": {
                                "satker_code": new_state["satker"],
                                "mutasi_count": new_state["mutasi"],
                                "override_blokir_52_pct": new_state["override_blokir_52"]
                            }
                        })
                except Exception as e:
                    print(f"Gagal memvalidasi argumen model: {e}")
                    
    # Heuristic Fallback Robustness: Jaga-jaga jika LLM mengembalikan teks mentah tanpa memanggil tool
    if not plan:
        satker_match = re.search(r'\b\d{6}\b', user_query)
        if satker_match:
            new_state["satker"] = satker_match.group(0)
            
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', user_query)
        if pct_match and ("52" in user_query or "blokir" in user_query):
            new_state["override_blokir_52"] = float(pct_match.group(1))
            
        if new_state["satker"]:
            plan.append({
                "tool": "run_forecast_simulation",
                "args": {
                    "satker_code": new_state["satker"],
                    "mutasi_count": new_state["mutasi"],
                    "override_blokir_52_pct": new_state["override_blokir_52"]
                }
            })
            
    return plan, new_state
