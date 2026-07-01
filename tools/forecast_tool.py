def get_forecast_schema():
    return {
        "type": "function",
        "function": {
            "name": "run_forecast_simulation",
            "description": "WAJIB DIGUNAKAN apabila user meminta pembuatan 'RPD', 'Rencana Penarikan Dana', 'forecast', atau 'anggaran' untuk sebuah Satker. Alat ini menghitung proyeksi keuangan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "satker_code": {
                        "type": "string",
                        "description": "Kode Satker 6 digit (contoh: '006817'). Ekstrak dari teks user atau riwayat percakapan."
                    },
                    "mutasi_count": {
                        "type": "integer",
                        "description": "Jumlah perubahan pegawai. Default ke 0 jika tidak disebutkan."
                    },
                    "n_curr": {
                        "type": "integer",
                        "description": "Estimasi jumlah pegawai saat ini untuk kalkulasi unit cost. Default ke 50 jika tidak ada data."
                    },
                    "override_blokir_52_pct": {
                        "type": "number",
                        "description": "Persentase blokir tambahan manual untuk jenis belanja 52 jika disebutkan user (contoh: isi 7.0 jika user mengatakan blokir 52 sebesar 7%)."
                    }
                },
                "required": ["satker_code"]
            }
        }
    }
