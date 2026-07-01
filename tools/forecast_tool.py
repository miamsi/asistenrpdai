def get_forecast_schema():
    return {
        "type": "function",
        "function": {
            "name": "run_forecast_simulation",
            "description": "WAJIB DIGUNAKAN apabila user meminta pembuatan 'RPD', 'Rencana Penarikan Dana', 'forecast', 'sandbox', atau 'anggaran' untuk sebuah Satker. Alat ini menghitung proyeksi keuangan bulanan serta mendukung penyesuaian termin belanja 53.",
            "parameters": {
                "type": "object",
                "properties": {
                    "satker_code": {
                        "type": "string", 
                        "minLength": 6, 
                        "maxLength": 6,
                        "description": "Kode Satker 6 digit angka angka (contoh: '006817')."
                    },
                    "mutasi_count": {
                        "type": "integer",
                        "description": "Jumlah perubahan pegawai / mutasi pegawai."
                    },
                    "n_curr": {
                        "type": "integer",
                        "description": "Konfigurasi nilai n_curr."
                    },
                    "override_blokir_52_pct": {
                        "type": "number", 
                        "minimum": 0, 
                        "maximum": 100,
                        "description": "Persentase override blokir untuk jenis belanja 52."
                    },
                    "plan_53_months": {
                        "type": "object",
                        "description": "Sandbox mapping alokasi bulan untuk Belanja 53. Contoh: {'MAR': 1, 'JUN': 1} artinya dibagi rata di bulan Maret dan Juni."
                    }
                },
                "required": ["satker_code"]
            }
        }
    }
