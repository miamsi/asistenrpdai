def get_forecast_schema():
    return {
        "type": "function",
        "function": {
            "name": "run_forecast_simulation",
            "parameters": {
                "type": "object",
                "properties": {
                    "satker_code": {"type": "string", "minLength": 6, "maxLength": 6},
                    "override_blokir_52_pct": {"type": "number", "minimum": 0, "maximum": 100}
                },
                "required": ["satker_code"]
            }
        }
    }
