# Panduan Config & Perintah Dashboard Phase 5

Semua perintah dijalankan dari dalam folder `phase_5` (folder yang berisi
`app.py` dan `config.py`). Kalau belum, `cd phase_5` dulu.

Ada 3 skrip pembantu supaya tak perlu ketik panjang:
- `.\cek.ps1`          cek kondisi DuckDB (tab kosong? kolom hilang? berapa pola?)
- `.\rebuild.ps1`      bangun ulang DuckDB dari data phase 4
- `.\buat_proyeksi.ps1` buat scatter segmen UMAP/t-SNE 2D & 3D

Kalau PowerShell menolak menjalankan skrip (.ps1), sekali saja jalankan:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Kalau skrip tetap tak dikenali ("not recognized"), pastikan kamu berada di
folder `phase_5` dan file `.ps1` memang ada di situ (`dir *.ps1`). Sebagai
alternatif, semua skrip bisa diganti perintah manual di bawah.

---

## 1. Menjalankan dashboard

```powershell
python app.py
```
Buka http://localhost:8050

Ganti port kalau 8050 dipakai:
```powershell
$env:PORT=8060 ; python app.py
```

Mode debug (auto-reload saat kode berubah):
```powershell
$env:DASH_DEBUG="true" ; python app.py
```

---

## 2. Rebuild DuckDB (paling sering dipakai)

Dipakai setiap kali mengubah kode pipeline/enrich atau data phase 4.
Perubahan tampilan (grafik, warna, layout) TIDAK perlu rebuild - cukup restart.

Cara mudah:
```powershell
.\rebuild.ps1
```

Cara manual (sama persis dengan isi rebuild.ps1):
```powershell
python -m pipeline.flow --mode real --data-root "D:\Paysim\College\Cawu 5\Data Mining\project\data-mining"
```

`--data-root` = folder yang DI DALAMNYA ada `datasets\phase_4\paysim_full_scored.parquet`.
Selalu pakai tanda kutip kalau path ada spasi.

Cek berhasil: di log muncul `transaksi=6.362.604`. Kalau `pola=` menunjukkan
angka 2000-an, berarti pool aturan berhasil dimuat. Kalau `pola=10`, cek bahwa
`datasets\phase_3\report_worthy_rules.csv` ada.

---

## 3. Backend: DuckDB vs Elasticsearch

Dashboard otomatis pakai Elasticsearch kalau hidup, kalau tidak pakai DuckDB.

Paksa DuckDB saja:
```powershell
$env:PAYSIM_BACKEND="duckdb" ; python app.py
```

Pakai Elasticsearch:
```powershell
docker-compose up -d
python -m pipeline.flow --mode real --data-root "<PATH>" --es-url http://localhost:9200
docker-compose down
```

---

## 4. Scatter segmen 3D (UMAP/t-SNE)

Supaya dropdown UMAP/t-SNE + radio 2D/3D di halaman Segmentasi berfungsi:

```powershell
.\buat_proyeksi.ps1
.\rebuild.ps1
python app.py
```

Manual:
```powershell
pip install umap-learn
python tools/build_segment_projection.py --all-variants `
    --input "<PATH>\datasets\phase_4\paysim_full_scored.parquet" `
    --output "<PATH>\datasets\phase_4\segment_projection.parquet"
```

---

## 5. Association rules: menampilkan SEMUA rule (bukan cuma 10)

Dashboard memuat pool rule dari `datasets\phase_3\report_worthy_rules.csv`.
Kalau file itu ada, rebuild akan memuat seluruh rule (ribuan). Kalau dashboard
cuma menampilkan 10, berarti pool belum termuat.

Cek berapa rule termuat:
```powershell
python -c "import sys; sys.path.insert(0,'.'); import config,duckdb; print('total pola:', duckdb.connect(config.DUCKDB_PATH,read_only=True).execute('SELECT COUNT(*) FROM pola').fetchone()[0])"
```
Kalau cuma ~10, pastikan `datasets\phase_3\report_worthy_rules.csv` ada, lalu
rebuild ulang.

---

## 6. Ubah ambang risiko (opsional)

Di `config.py`:
```python
HIGH_RISK_THRESHOLD = 3
CRITICAL_RISK_THRESHOLD = 5
```
Setelah mengubah ini, rebuild supaya kolom high_risk dihitung ulang.

---

## Ringkasan: kapan perlu rebuild?

| Yang diubah                                   | Perlu rebuild? |
|-----------------------------------------------|----------------|
| Warna, layout, teks, grafik (charts, pages, theme, css) | Tidak - cukup `python app.py` |
| Kode pipeline/enrich.py                        | Ya |
| Data phase 4 (paysim_full_scored.parquet)      | Ya |
| Ambang risiko di config.py                     | Ya |
| Tambah/ubah file rule phase 3                  | Ya |
| Buat proyeksi scatter baru                     | Ya |
