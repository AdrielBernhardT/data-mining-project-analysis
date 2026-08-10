param(
    [string]$DataRoot = "/home/adriel/Desktop/Coding/data-mining-project-analysis/phase/phase_5",
    [switch]$SkipUmapInstall
)

Write-Host "=== BUAT PROYEKSI SCATTER SEGMEN ===" -ForegroundColor Cyan

if (-not $SkipUmapInstall) {
    Write-Host "Memasang umap-learn (untuk opsi UMAP)..." -ForegroundColor Green
    pip install umap-learn
    Write-Host ""
}

$inputPath  = Join-Path $DataRoot "datasets\phase_4\paysim_full_scored.parquet"
$outputPath = Join-Path $DataRoot "datasets\phase_4\segment_projection.parquet"

if (-not (Test-Path $inputPath)) {
    Write-Host "[GAGAL] Tidak menemukan input: $inputPath" -ForegroundColor Red
    exit 1
}

Write-Host "Menghitung 4 varian (UMAP/t-SNE x 2D/3D) - bisa beberapa menit..." -ForegroundColor Green
python tools/build_segment_projection.py --all-variants --input "$inputPath" --output "$outputPath"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== PROYEKSI SELESAI ===" -ForegroundColor Green
    Write-Host "Langkah berikut:  .\rebuild.ps1  lalu  python app.py" -ForegroundColor Cyan
} else {
    Write-Host "=== GAGAL (exit $LASTEXITCODE) ===" -ForegroundColor Red
}
