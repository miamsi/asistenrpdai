from tools.registry import get_tool_execution_map
import json

def execute_plan(plan: list, df) -> str:
    execution_map = get_tool_execution_map()
    results = []
    
    for step in plan:
        tool_name = step.get("tool")
        args = step.get("args", {})
        
        if tool_name in execution_map:
            # Panggil fungsi service (yang mengharapkan df dan argumen dalam format string JSON)
            func = execution_map[tool_name]
            step_result = func(df, json.dumps(args)) 
            results.append(step_result)
        else:
            results.append(json.dumps({"error": f"Tool {tool_name} not found."}))
            
    # Mengembalikan hasil eksekusi pertama (karena alur saat ini 1 plan = 1 eksekusi utama)
    return results[0] if results else "{}"
