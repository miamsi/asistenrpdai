from groq import Groq
import streamlit as st
import json
from agents.planner import generate_plan
from agents.executor import execute_plan

def process_agentic_workflow(user_query: str, df, state: dict, chat_history: list):
    yield {"trace": "🧠 Menganalisis kebutuhan & memperbarui parameter sandbox..."}
    
    plan, updated_state = generate_plan(user_query, state, chat_history)
    yield {"new_state": updated_state}
    
    if not plan:
        yield {"trace": "⚠️ Memerlukan informasi kode Satker 6 digit yang valid."}
        yield {"final_answer": "Mohon maaf, silakan masukkan informasi kode Satker 6 digit angka yang valid untuk memproses estimasi RPD Anda."}
        return

    yield {"trace": "⚙️ Mengeksekusi kalkulasi core finansial berbasis aturan..."}
    final_context_str = execute_plan(plan, df)
    
    # --- MENCEGAH HALUSINASI & MENGEKSTRAK DATA UNTUK UI ---
    try:
        context_data = json.loads(final_context_str)
        if "error" in context_data:
            yield {"trace": f"❌ Data Tidak Ditemukan: {context_data['error']}"}
            yield {"final_answer": f"Mohon maaf, kalkulasi gagal diproses: **{context_data['error']}**. Pastikan data riil Satker tersebut tersedia di database untuk tahun 2026."}
            return
        else:
            # Kirimkan data JSON bersih ini kembali ke app.py untuk merender visual
            yield {"ui_data": context_data}  
    except Exception as e:
        yield {"trace": "❌ Gagal mengurai respons engine finansial."}
        return

    yield {"trace": "📊 Menyusun respons percakapan akhir..."}
    
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    rolling_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-4:]])
    
    synthesis_prompt = f"""
    Anda adalah asisten AI Kemenkeu/DJPb Otoritatif.
    
    ATURAN UTAMA ANTI-HALUSINASI:
    1. JANGAN PERNAH MENGARANG ANGKA.
    2. Gunakan HANYA data metrik dan tabel bulanan yang ada di dalam "Context Data Eksekusi" di bawah.
    3. Rangkum hasilnya dalam tabel Markdown, lalu beritahu pengguna bahwa detail dashboard visual juga telah dilampirkan di bawah pesan ini.
    
    Riwayat Percakapan Sebelumnya:
    {rolling_history}
    
    Context Data Eksekusi (HANYA GUNAKAN DATA INI): 
    {final_context_str}
    
    Query User: {user_query}
    """
    
    response = client.chat.completions.create(
        model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": synthesis_prompt}],
        temperature=0.0 # Strict mode, tidak ada improvisasi
    )
    
    yield {"final_answer": response.choices[0].message.content}
