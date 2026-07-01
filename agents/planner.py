from groq import Groq
import streamlit as st
import json

def generate_plan(user_query: str, tools_schemas: list) -> list:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    system_prompt = """
    Anda adalah AI Planner khusus untuk sistem keuangan negara (Kemenkeu/DJPb).
    Konteks utama Anda adalah RPD (Rencana Penarikan Dana Fiskal), bukan Rencana Pembangunan.
    Tugas Anda HANYA membaca permintaan user dan mengeluarkan array JSON dari tool yang harus dipanggil.
    JANGAN PERNAH menjawab pertanyaan secara langsung. JANGAN PERNAH memberikan penjelasan.
    Jika user meminta RPD untuk sebuah satker, Anda WAJIB memanggil tool 'run_forecast_simulation'.
    Output harus berupa array JSON murni tanpa markdown, tanpa teks pembuka.
    Contoh Output: [{"tool": "run_forecast_simulation", "args": {"satker_code": "006817", "mutasi_count": 0}}]
    """
    
    # We pass the schemas in the prompt so the LLM knows what tools exist
    messages = [
        {"role": "system", "content": system_prompt + f"\nAvailable Tools: {json.dumps(tools_schemas)}"},
        {"role": "user", "content": user_query}
    ]
    
    response = client.chat.completions.create(
        model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=messages,
        response_format={"type": "json_object"} # Forces JSON output
    )
    
    try:
        # Assuming the model returns {"steps": [...]}
        result = json.loads(response.choices[0].message.content)
        return result.get("steps", [])
    except json.JSONDecodeError:
        return []
