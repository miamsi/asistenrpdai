from services.forecast_service import execute_forecast_service
from tools.forecast_tool import get_forecast_schema

AVAILABLE_TOOLS_SCHEMAS = [
    get_forecast_schema()
]

def get_tool_execution_map():
    return {
        "run_forecast_simulation": execute_forecast_service
    }
