def get_forecast_schema():
    return {
        "type": "function",
        "function": {
            "name": "run_forecast_simulation",
            "description": "Menghitung simulasi proyeksi RPD bulanan untuk Satker tertentu berdasarkan DNA Fiskal historis dan parameter penyesuaian.",
            "parameters": {
                "type": "object",
                "properties": {
                    "satker_code": {
                        "type": "string", 
                        "minLength": 6, 
                        "maxLength": 6,
                        "description": "Kode unik identitas Satker 6 digit angka penuh."
                    },
                    "mutasi_count": {
                        "type": "integer",
                        "minimum": -500,
                        "maximum": 500,
                        "description": "Jumlah penambahan atau pengurangan net pegawai di Satker tersebut."
                    },
                    "override_blokir_52_pct": {
                        "type": "number", 
                        "minimum": 0.0, 
                        "maximum": 100.0,
                        "description": "Nilai persentase pemblokiran anggaran manual yang dipaksakan khusus jenis belanja 52 (0-100)."
                    }
                },
                "required": ["satker_code"]
            }
        }
    }
