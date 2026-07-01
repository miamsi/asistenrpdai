from groq import Groq
import streamlit as st
import json

def generate_plan(user_query: str, tools_schemas: list) -> list:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    system_prompt = """
    Anda adalah asisten AI Kemenkeu/DJPb. Tugas utama Anda adalah membantu perencana keuangan.
    Jika user menyebutkan kata 'RPD', 'Rencana Penarikan Dana', atau meminta 'forecast' untuk sebuah Satker, 
    Anda WAJIB menggunakan tool 'run_forecast_simulation'.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    
    # 1. Kita ubah format pemanggilan Groq di sini
    response = client.chat.completions.create(
        model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=messages,
        tools=tools_schemas,    # <-- Memasukkan schema secara native ke API
        tool_choice="auto"      # <-- Memaksa Groq memilih tool jika relevan
    )
    
    plan = []
    message = response.choices[0].message
    
    # 2. Tangkap hasil tool calling native dari Groq
    if message.tool_calls:
        for tool_call in message.tool_calls:
            try:
                plan.append({
                    "tool": tool_call.function.name,
                    "args": json.loads(tool_call.function.arguments)
                })
            except Exception as e:
                print(f"Error parsing tool args: {e}")
                
    return plan
