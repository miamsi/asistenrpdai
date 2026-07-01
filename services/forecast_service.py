from core.forecasting_engine import calculate_rpd_forecast
import json

def execute_forecast_service(df, args_json: str) -> str:
    """Parses LLM arguments, calls the core engine, and returns a JSON string result."""
    try:
        args = json.loads(args_json)
        satker = args.get("satker_code")
        mutasi = args.get("mutasi_count", 0)
        n_curr = args.get("n_curr", 50)
        override_blokir_52_pct = args.get("override_blokir_52_pct", 0.0)
        plan_53_months = args.get("plan_53_months", None)
        
        result = calculate_rpd_forecast(
            df=df, 
            satker_code=satker, 
            mutasi_count=mutasi, 
            n_curr=n_curr, 
            override_blokir_52_pct=override_blokir_52_pct,
            plan_53_json=plan_53_months
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
