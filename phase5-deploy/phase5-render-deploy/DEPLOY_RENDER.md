================================================================================
 PANDUAN DEPLOY DASHBOARD PHASE 5 KE RENDER.COM
================================================================================

Dokumen ini adalah lanjutan dari STRUKTUR_PHASE_5.txt, khusus soal cara naikkan
dashboard ini ke internet lewat Render.com (https://dashboard.render.com/web/new).


--------------------------------------------------------------------------------
 KENAPA TIDAK BISA LANGSUNG "GIT PUSH" SEMUA FILE?
--------------------------------------------------------------------------------

Dashboard butuh file `data/paysim_dashboard.duckdb` supaya bisa jalan (lihat
BAGIAN 3 di STRUKTUR_PHASE_5.txt - ini hasil bangunan pipeline dari data
Phase 4, ~6,3 juta baris).

Masalahnya:
  - File .duckdb yang sudah dibangun ukurannya ~185 MB.
  - GitHub MENOLAK file di atas 100 MB kalau di-push langsung (tanpa Git LFS).
  - Data mentahnya (paysim_full_scored.parquet) malah lebih besar lagi (138 MB)
    dan masih perlu proses build lagi di server - boros waktu & RAM kalau
    dilakukan tiap kali deploy.

SOLUSI yang dipakai di paket ini:
  1. Database .duckdb SUDAH dibangun duluan (index-nya juga sudah disederhanakan
     supaya ukurannya turun dari ~1,1 GB jadi ~185 MB - lihat catatan di bawah).
  2. File itu di-upload sebagai "Release asset" di GitHub (BUKAN lewat git push
     biasa) - GitHub mengizinkan file sampai 2 GB lewat jalur ini, tanpa perlu
     Git LFS.
  3. Saat Render melakukan build, dia men-download file itu lewat `curl` sebelum
     menjalankan aplikasi.

Kode aplikasi sendiri (app.py, pages/, components/, dst) totalnya cuma ~650 KB,
jadi aman di-push biasa lewat git.

CATATAN TEKNIS soal index database:
  Database asli (hasil `python -m pipeline.flow --mode real`) otomatis membuat
  9 index (idx_jenis_tujuan, idx_risk_score, dst) yang bikin ukurannya membengkak
  ke ~1,1 GB. Untuk deployment ini, index-index itu SENGAJA tidak dibuat (tabel,
  kolom, dan isinya tetap 100% sama - transaksi=6.362.604, pola=2.702, cube=144).
  DuckDB tetap cukup cepat untuk ukuran data ini walau tanpa index karena mesin
  kolumnarnya sudah punya zonemap otomatis. Kalau nanti terasa ada query yang
  lambat, index bisa ditambahkan lagi manual lewat DuckDB.


--------------------------------------------------------------------------------
 LANGKAH 1 - PUSH KODE KE GITHUB
--------------------------------------------------------------------------------

Dari folder hasil ekstrak paket ini (folder ini juga):

  git init
  git add .
  git commit -m "Phase 5 dashboard - siap deploy"
  git branch -M main
  git remote add origin https://github.com/<username-kamu>/<nama-repo>.git
  git push -u origin main

(Buat dulu repo kosong di GitHub kalau belum ada: https://github.com/new)

Repo boleh PUBLIC atau PRIVATE. Kalau PUBLIC, langkah download database di
Render (Langkah 3) lebih simpel karena tidak perlu token. PaySim adalah dataset
sintetis publik, jadi tidak ada isu privasi kalau repo dibuat public.


--------------------------------------------------------------------------------
 LANGKAH 2 - UPLOAD DATABASE KE GITHUB RELEASE
--------------------------------------------------------------------------------

  1. Buka repo kamu di GitHub -> tab "Releases" (di sidebar kanan) -> "Create a
     new release" (atau lewat URL: github.com/<user>/<repo>/releases/new).
  2. Isi "Tag" misalnya: data-v1
  3. Judul release bebas, misalnya: "Dashboard database (real data)"
  4. Di bagian "Attach binaries", drag-and-drop file
     `paysim_dashboard.duckdb` (file terpisah yang saya siapkan, ~185 MB).
  5. Klik "Publish release".
  6. Klik kanan pada nama file di halaman release itu -> "Copy link address".
     Link-nya berbentuk:
       https://github.com/<user>/<repo>/releases/download/data-v1/paysim_dashboard.duckdb
     SIMPAN link ini, dipakai di Langkah 3.


--------------------------------------------------------------------------------
 LANGKAH 3 - SETUP DI RENDER (https://dashboard.render.com/web/new)
--------------------------------------------------------------------------------

  1. Pilih "Build and deploy from a Git repository" -> connect akun GitHub kamu
     (atau pilih "Public Git Repository" kalau repo kamu public dan tidak mau
     connect akun).
  2. Pilih repo yang tadi di-push.
  3. Isi form:
       Name              : bebas, mis. paysim-fraud-dashboard
       Region            : Singapore (paling dekat dari Indonesia)
       Branch            : main
       Root Directory    : (kosongkan - app.py ada di root repo)
       Runtime           : Python 3
       Build Command     :
         pip install -r requirements.txt && mkdir -p data && curl -L -o data/paysim_dashboard.duckdb "PASTE_LINK_RELEASE_DARI_LANGKAH_2"
       Start Command     :
         gunicorn app:server --workers 1 --threads 4 --timeout 120
       Instance Type     : Free (cukup untuk demo; lihat catatan di bawah)
  4. Buka bagian "Advanced" -> "Environment Variables" -> tambah:
       PAYSIM_BACKEND = duckdb
     (Ini memaksa dashboard langsung pakai DuckDB tanpa buang waktu coba
     ping Elasticsearch dulu - mempercepat startup.)
  5. Klik "Create Web Service" / "Deploy Web Service".
  6. Tunggu build selesai (pantau log-nya di tab "Deploys"/"Logs"). Kalau
     berhasil, log terakhir akan menunjukkan:
       ✅ DuckDB aktif (.../data/paysim_dashboard.duckdb) - dashboard memakai mode lokal DuckDB.
  7. Dashboard bisa diakses di URL *.onrender.com yang diberikan Render.


--------------------------------------------------------------------------------
 CATATAN PENTING SOAL FREE TIER RENDER
--------------------------------------------------------------------------------

  - RAM  : 512 MB, 0.1 CPU. Sudah dites - dashboard ini cuma pakai ~170 MB RAM
           saat jalan, jadi masih longgar.
  - Sleep: layanan Free "tidur" setelah 15 menit tanpa ada yang akses, lalu
           butuh ~30-60 detik untuk "bangun" lagi saat diakses berikutnya.
           Kalau dashboard ini mau dipakai untuk presentasi/demo langsung ke
           dosen dan tidak mau ada jeda loading di awal, pertimbangkan naik ke
           paket Starter ($7/bulan, selalu aktif).
  - Kuota: 750 jam instance gratis/bulan, 100 GB bandwidth, 500 menit build.
           Untuk dashboard kuliah, ini jauh lebih dari cukup.
  - Free tier TIDAK punya persistent disk - makanya strategi di panduan ini
    men-download ulang file .duckdb tiap kali build (bukan disimpan permanen
    di server). Setiap kali redeploy, file itu didownload ulang dari GitHub
    Release - prosesnya cuma beberapa detik karena file-nya ada di CDN GitHub.


--------------------------------------------------------------------------------
 TROUBLESHOOTING
--------------------------------------------------------------------------------

  "FileNotFoundError: Tidak menemukan data/paysim_dashboard.duckdb"
    -> Build Command gagal download. Cek lagi link Release-nya (harus link
       LANGSUNG ke file, bukan link ke halaman release), dan pastikan repo/
       release-nya bisa diakses publik.

  Build gagal karena pip install lama/timeout
    -> requirements.txt di paket ini sudah ditrim (tanpa elasticsearch/prefect
       yang berat dan tidak dipakai saat runtime), jadi harusnya cepat
       (< 1 menit). Kalau masih lambat, cek log spesifiknya di tab Logs.

  Dashboard kebuka tapi grafik kosong / error 500 saat klik tab tertentu
    -> Cek Logs di Render, biasanya kelihatan traceback Python-nya. Paling
       sering karena Build Command belum sukses download database (cek ukuran
       filenya di log build, harus ~185 MB bukan 0 byte / halaman HTML error).

  Mau update data (misalnya nanti ada Phase 4 versi baru)
    -> Build ulang .duckdb secara lokal (python -m pipeline.flow --mode real
       --data-root <path>), upload lagi sebagai Release baru (tag baru, mis.
       data-v2), lalu update link di Build Command Render, lalu "Manual Deploy"
       di Render.
