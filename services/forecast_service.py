from core.forecasting_engine import calculate_rpd_forecast
import json

def execute_forecast_service(df, args: dict) -> str:
    """Menerima representasi data dictionary langsung dari Executor Layer."""
    try:
        satker = args.get("satker_code")
        mutasi = args.get("mutasi_count", 0)
        n_curr = args.get("n_curr", 50)
        override_blokir_52_pct = args.get("override_blokir_52_pct", 0.0)
        
        result = calculate_rpd_forecast(df, satker, mutasi, n_curr, override_blokir_52_pct)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
