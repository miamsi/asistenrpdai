from agents.planner import generate_plan
from agents.executor import execute_plan
from tools.registry import AVAILABLE_TOOLS_SCHEMAS

def process_agentic_workflow(user_query, df, state):
    yield {"trace": "🧠 Perencanaan dengan State..."}
    plan, updated_state = generate_plan(user_query, state)
    yield {"new_state": updated_state}
    
    if plan:
        yield {"trace": "⚙️ Eksekusi deterministik..."}
        context = execute_plan(plan, df)
        yield {"final_answer": context} # Simplified for brevity
    else:
        yield {"final_answer": "Mohon maaf, saya memerlukan kode Satker untuk melanjutkan."}
