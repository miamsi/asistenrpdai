from groq import Groq
import streamlit as st
import json

def generate_plan(user_query: str, tools_schemas: list, chat_history: list) -> list:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    system_prompt = """
    Anda adalah asisten AI Kemenkeu/DJPb. Tugas utama Anda adalah membantu perencana keuangan.
    Jika user menyebutkan kata 'RPD', 'Rencana Penarikan Dana', atau meminta 'forecast' untuk sebuah Satker, 
    Anda WAJIB menggunakan tool 'run_forecast_simulation'.
    Perhatikan riwayat percakapan dengan sangat teliti untuk menangkap Satker yang sedang dibahas, parameter mutasi pegawai, atau instruksi pemblokiran anggaran secara manual.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Masukkan riwayat percakapan (maksimal 6 iterasi) ke dalam memori
    for msg in chat_history[-6:]:
        if msg["role"] in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    response = client.chat.completions.create(
        model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=messages,
        tools=tools_schemas,
        tool_choice="auto"
    )
    
    plan = []
    message = response.choices[0].message
    
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
