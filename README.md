# 🗺 Peta Digital UNJ

Sistem Informasi Geografis (SIG) interaktif untuk kampus Universitas Negeri
Jakarta (Rawamangun) — dibangun dengan **Streamlit, Folium, Plotly, Pandas,
dan SQLite**.

## ✨ Fitur

- **Peta interaktif** dengan marker berkategori (Akademik, Administrasi &
  Layanan, Fasilitas Umum, Kesehatan & Keamanan, Parkir), pencarian lokasi,
  filter kategori, dan pilihan tile layer (standar/gelap/satelit).
- **Pencarian rute terpendek antar-gedung** — dua mode:
  - **Mode OSM** (opsional, kualitas setara Google Maps): rute mengikuti
    geometri jalan/trotoar sungguhan dari data OpenStreetMap. Aktifkan
    dengan menjalankan `database/build_network.py` sekali (perlu internet
    + `pip install osmnx`).
  - **Mode fallback** (aktif otomatis, tanpa setup): graf waypoint manual
    yang mengikuti pola jalan lingkar kampus. Selalu tersedia, 100% offline.
- **Dashboard analitik** — statistik kunjungan, tren aktivitas, distribusi
  aksi pengguna, dan sebaran gedung, dibangun dari log aktivitas nyata.
- **Ekspor data** ke CSV dan GeoJSON untuk keperluan analisis lanjutan.

## 🗄 Struktur Basis Data (5 Tabel, Ternormalisasi 3NF)

| Tabel            | Deskripsi                                                              |
|-------------------|-------------------------------------------------------------------------|
| `gedung`          | Titik spasial utama kampus (nama, kategori, koordinat, jam operasional) |
| `fasilitas`       | Fasilitas/layanan yang terhubung ke gedung (relasi many-to-one)         |
| `rute`            | Graf waypoint jalur pejalan kaki (mode fallback, jarak Haversine)       |
| `pengguna_sesi`   | Metadata sesi pemakaian aplikasi                                        |
| `log_aktivitas`   | Log setiap interaksi pengguna untuk kebutuhan analitik                  |

Seluruh koordinat & deskripsi gedung diambil dari hasil pemetaan manual
kampus UNJ Rawamangun (lihat `database/seed_data.py`), bukan data sintetis.

## 🚀 Menjalankan Aplikasi

```bash
pip install -r requirements.txt
streamlit run app.py
```

Database SQLite (`database/database.sqlite`) akan **otomatis dibuat dan
di-seed** saat aplikasi pertama kali dijalankan — tidak perlu setup manual.

### 🛰️ Mengaktifkan Mode Rute OSM (opsional, disarankan)

Untuk rute yang mengikuti jalan/trotoar sungguhan (bukan garis perkiraan):

```bash
pip install osmnx
python database/build_network.py
```

Skrip ini mengunduh graf jalan kaki dari OpenStreetMap untuk area kampus
UNJ **satu kali saja** (butuh internet), lalu menyimpannya sebagai
`database/unj_walknet.graphml`. Setelah file ini ada, aplikasi otomatis
memakainya — tidak perlu internet lagi setelahnya. Tanpa langkah ini,
aplikasi tetap berjalan normal memakai mode fallback.

## 📁 Struktur Proyek

```
peta_unj/
├── app.py                  # Entry point aplikasi Streamlit
├── database/
│   ├── build_network.py     # Skrip sekali-jalan: unduh graf OSM (opsional)
│   ├── schema.sql           # Definisi 5 tabel ternormalisasi
│   └── seed_data.py         # Data asli kampus + pembangun graf rute
├── modules/
│   ├── db.py                 # Koneksi & query database
│   ├── routing.py             # Pencarian rute terpendek (offline)
│   ├── map_builder.py          # Pembangun peta Folium
│   ├── analytics.py            # Grafik Plotly untuk dashboard
│   └── export.py                # Ekspor CSV/GeoJSON
├── assets/style.css         # Tema visual navy-gold kustom
└── requirements.txt
```
