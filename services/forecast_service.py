from core.forecasting_engine import calculate_rpd_forecast
import json

def execute_forecast_service(df, args_json: str) -> str:
    """Parses LLM arguments, calls the core engine, and returns a JSON string result."""
    try:
        args = json.loads(args_json)
        satker = args.get("satker_code")
        mutasi = args.get("mutasi_count", 0)
        n_curr = args.get("n_curr", 50)
        
        result = calculate_rpd_forecast(df, satker, mutasi, n_curr)
        # Handle numpy floats for clean JSON conversion
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
