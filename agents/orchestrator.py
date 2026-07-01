from groq import Groq
import streamlit as st
from agents.planner import generate_plan
from agents.executor import execute_plan

def process_agentic_workflow(user_query: str, df, state: dict, chat_history: list):
    yield {"trace": "🧠 Menganalisis kebutuhan & memperbarui parameter sandbox..."}
    
    # Teruskan chat_history ke Planner
    plan, updated_state = generate_plan(user_query, state, chat_history)
    yield {"new_state": updated_state}
    
    if not plan:
        yield {"trace": "⚠️ Memerlukan informasi kode Satker 6 digit yang valid."}
        yield {"final_answer": "Mohon maaf, silakan masukkan informasi kode Satker 6 digit angka yang valid untuk memproses estimasi RPD Anda."}
        return

    yield {"trace": "⚙️ Mengeksekusi kalkulasi core finansial berbasis aturan..."}
    final_context = execute_plan(plan, df)
    yield {"trace": "📊 Menyusun analisis kepatuhan target & tabel rencana..."}
    
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    # Ambil 4 obrolan terakhir untuk memori sintesis
    rolling_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-4:]])
    
    synthesis_prompt = f"""
    Anda adalah asisten AI Kemenkeu/DJPb Otoritatif. 
    Tugas Anda adalah memformat jawaban hasil analisis keuangan dari context yang diberikan.
    
    ATURAN UTAMA PRESENTASI:
    1. Anda WAJIB menampilkan seluruh 'Proyeksi Bulanan' (Januari s.d Desember) untuk Akun 51, 52, dan 53 dalam bentuk TABEL MARKDOWN tunggal yang rapi agar mudah dibaca oleh Satker.
    2. Tampilkan pula ringkasan Pagu DIPA, Pagu Efektif, Sisa Anggaran, serta Analisis Capaian Target Triwulanan yang ada pada context.
    3. Jawablah menggunakan Bahasa Indonesia yang formal dan lugas.
    
    Riwayat Percakapan Sebelumnya:
    {rolling_history}
    
    Context Data Eksekusi (OTORITATIF): 
    {final_context}
    
    Query User: {user_query}
    """
    
    response = client.chat.completions.create(
        model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": synthesis_prompt}]
    )
    
    yield {"final_answer": response.choices[0].message.content}
