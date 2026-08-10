param(
    [string]$DataRoot = "/home/adriel/Desktop/Coding/data-mining-project-analysis/phase/phase_5"
)

Write-Host "=== REBUILD DUCKDB DASHBOARD ===" -ForegroundColor Cyan
Write-Host "Data root: $DataRoot"
Write-Host ""

$phase4 = Join-Path $DataRoot "datasets\phase_4\paysim_full_scored.parquet"
if (-not (Test-Path $phase4)) {
    Write-Host "[PERINGATAN] Tidak menemukan: $phase4" -ForegroundColor Yellow
    Write-Host "Pastikan -DataRoot menunjuk folder yang berisi datasets\phase_4\paysim_full_scored.parquet" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Menjalankan pipeline (bisa beberapa menit untuk 6,3 juta baris)..." -ForegroundColor Green
python -m pipeline.flow --mode real --data-root "$DataRoot"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== REBUILD SELESAI ===" -ForegroundColor Green
    Write-Host "Jalankan dashboard dengan:  python app.py" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "=== REBUILD GAGAL (exit code $LASTEXITCODE) ===" -ForegroundColor Red
    Write-Host "Cek pesan error di atas. Sering karena -DataRoot salah." -ForegroundColor Yellow
}
