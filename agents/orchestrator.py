from groq import Groq
import streamlit as st
from agents.planner import generate_plan
from agents.executor import execute_plan
from tools.registry import AVAILABLE_TOOLS_SCHEMAS

def process_agentic_workflow(user_query: str, df, chat_history: list) -> dict:
    """Runs the Planner-Executor loop and yields trace updates with memory."""
    
    # Step 1: Plan
    yield {"trace": "🧠 Menganalisis riwayat percakapan dan membangun rencana..."}
    plan = generate_plan(user_query, AVAILABLE_TOOLS_SCHEMAS, chat_history)
    
    if not plan:
        yield {"trace": "⚠️ Tidak ada aksi yang diperlukan atau format plan gagal."}
        final_context = "No tools executed."
    else:
        # Step 2: Execute
        yield {"trace": f"⚙️ Mengeksekusi {len(plan)} langkah..."}
        final_context = execute_plan(plan, df)
        yield {"trace": "📊 Data berhasil disimulasikan sesuai instruksi."}
        
    # Step 3: Synthesize
    yield {"trace": "✍️ Menyusun kesimpulan akhir..."}
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    # Ambil 5 riwayat terakhir untuk konteks saat agen menjawab
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:]])
    
    synthesis_prompt = f"""
    Answer the user's current query using ONLY the provided execution context.
    Consider the conversation history to understand the full context of the final calculation.
    
    Conversation History:
    {history_text}
    
    Context from tools execution: {final_context}
    Current Query: {user_query}
    """
    
    response = client.chat.completions.create(
        model=st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": synthesis_prompt}]
    )
    
    yield {"final_answer": response.choices[0].message.content}
