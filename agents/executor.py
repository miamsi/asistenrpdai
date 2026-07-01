from tools.registry import get_tool_execution_map
import json

def execute_plan(plan: list, df) -> str:
    execution_map = get_tool_execution_map()
    results = []
    
    for step in plan:
        tool_name = step.get("tool")
        args = step.get("args", {})
        
        if tool_name in execution_map:
            # Call the mapped service function
            func = execution_map[tool_name]
            # Convert args back to JSON string for the service layer
            step_result = func(df, json.dumps(args)) 
            results.append(f"Result of {tool_name}: {step_result}")
        else:
            results.append(f"Error: Tool {tool_name} not found.")
            
    return "\n".join(results)
