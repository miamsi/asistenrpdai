from groq import Groq
import streamlit as st
import json

def generate_plan(user_query: str, tools_schemas: list) -> list:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    system_prompt = """
    You are an AI planner for a financial application. 
    Your job is to read the user's request and output a strict JSON array of tool calls required to answer the query.
    Do not include any other text. Only output valid JSON.
    Example: [{"tool": "run_forecast_simulation", "args": {"satker_code": "123456", "mutasi_count": 5}}]
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
