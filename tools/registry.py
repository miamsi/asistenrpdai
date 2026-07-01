from services.forecast_service import execute_forecast_service
from tools.forecast_tool import get_forecast_schema

# Registry of schemas for the Planner
AVAILABLE_TOOLS_SCHEMAS = [
    get_forecast_schema()
    # Add rag_schema(), stress_test_schema() here later
]

# Registry of execution functions
def get_tool_execution_map():
    return {
        "run_forecast_simulation": execute_forecast_service
        # "search_regulation": execute_rag_service
    }
