def get_forecast_schema():
    return {
        "type": "function",
        "function": {
            "name": "run_forecast_simulation",
            "description": "Calculates the financial RPD forecast for a given Satker, taking into account employee mutations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "satker_code": {
                        "type": "string",
                        "description": "The 6-digit Satker code (e.g., '403812')"
                    },
                    "mutasi_count": {
                        "type": "integer",
                        "description": "Expected change in employees (+ or -). Default is 0."
                    }
                },
                "required": ["satker_code"]
            }
        }
    }
