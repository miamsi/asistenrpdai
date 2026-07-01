from tools.registry import get_tool_execution_map

def execute_plan(plan, df):
    execution_map = get_tool_execution_map()
    combined_context = ""
    
    for step in plan:
        tool_name = step["tool"]
        args = step["args"]
        
        if tool_name in execution_map:
            # Perbaikan Arsitektur: Mengirim argumen dictionary secara langsung tanpa round-trip JSON string
            result = execution_map[tool_name](df, args)
            combined_context += f"\n[Hasil Otentik Alat - {tool_name}]:\n{result}\n"
        else:
            combined_context += f"\n[Error]: Eksekutor gagal menemukan fungsi {tool_name} di registry.\n"
            
    return combined_context
