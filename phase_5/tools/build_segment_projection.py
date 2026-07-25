"""
tools/build_segment_projection.py
=================================
Menghasilkan koordinat proyeksi (UMAP / t-SNE) untuk visualisasi scatter
segmen di halaman Segmentasi Nasabah dashboard. Default 3D (bisa diputar).

KENAPA PERLU: scatter plot butuh koordinat (x, y) per titik. Menjalankan
UMAP/t-SNE pada 6,3 juta baris tidak feasible (berjam-jam + browser tak sanggup
render sejuta titik). Skrip ini MENGAMBIL SAMPEL stratified 5.000 titik per
segmen (~25 ribu total), menghitung proyeksi di sampel itu, lalu menyimpannya
sebagai parquet kecil yang dibaca pipeline phase 5.

CARA PAKAI (jalankan sekali di mesin yang punya data phase 4):

    python tools/build_segment_projection.py \
        --input /path/ke/datasets/phase_4/paysim_full_scored.parquet \
        --output /path/ke/datasets/phase_4/segment_projection.parquet

    --per-segment 5000     jumlah sampel per segmen (default 5000)
    --method umap          umap | tsne | auto (default auto: umap kalau ada, else tsne)
    --seed 42

Skrip ini TIDAK menjalankan ulang clustering - ia memakai kolom cluster_kmeans
yang SUDAH ada di paysim_full_scored.parquet. Jadi jauh lebih ringan daripada
menjalankan ulang seluruh phase 2.

Setelah file segment_projection.parquet dihasilkan, taruh di folder yang sama
dengan paysim_full_scored.parquet (di dalam datasets/phase_4/). Pipeline phase 5
(flow.py) akan otomatis mendeteksi & memuatnya. Kalau file ini tidak ada,
dashboard tetap jalan normal - hanya scatter segmen yang menampilkan pesan
"jalankan tools/build_segment_projection.py untuk mengaktifkan".
"""
from __future__ import annotations

import argparse
import sys
import numpy as np
import pandas as pd

NON_FEATURE_COLS = [
    "isFraud", "isFlaggedFraud", "step", "cluster_kmeans", "cluster_hdbscan",
    "cluster_birch", "cluster_birch_hdbscan", "is_birch_hdbscan_outlier",
    "risk_score", "risk_level", "anomaly_type", "investigation_category",
    "high_risk", "nameOrig", "nameDest", "jenis_tujuan",
]


def _pick_feature_columns(df: pd.DataFrame) -> list[str]:
    """Ambil hanya kolom numerik yang merupakan fitur (bukan label/metadata)."""
    feats = []
    for c in df.columns:
        if c in NON_FEATURE_COLS:
            continue
        if pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]):
            feats.append(c)
    return feats


def _stratified_sample(df: pd.DataFrame, per_segment: int, seed: int) -> pd.DataFrame:
    """Ambil sampel per segmen (cluster_kmeans). Kalau segmen lebih kecil dari
    per_segment, ambil semuanya."""
    parts = []
    for cid, grp in df.groupby("cluster_kmeans"):
        n = min(per_segment, len(grp))
        parts.append(grp.sample(n=n, random_state=seed))
    return pd.concat(parts, ignore_index=True)


def _project(X: np.ndarray, method: str, seed: int, dim: int = 3):
    """Kembalikan (koordinat_dim, nama_metode). method: umap|tsne|auto.
    dim=3 menghasilkan proyeksi 3D (untuk scatter yang bisa diputar)."""
    from sklearn.preprocessing import StandardScaler
    Xs = StandardScaler().fit_transform(X)

    want = method.lower()
    if want in ("umap", "auto"):
        try:
            import umap
            reducer = umap.UMAP(
                n_components=dim, n_neighbors=15, min_dist=0.1,
                metric="euclidean", random_state=seed,
            )
            coords = reducer.fit_transform(Xs)
            return coords, "UMAP"
        except ImportError:
            if want == "umap":
                print("ERROR: umap-learn tidak terpasang. `pip install umap-learn` "
                      "atau gunakan --method tsne.", file=sys.stderr)
                sys.exit(1)
            print("[info] umap-learn tidak ada, fallback ke t-SNE ...")

    from sklearn.manifold import TSNE
    n_feat = Xs.shape[1]
    if n_feat > 30:
        from sklearn.decomposition import PCA
        Xs = PCA(n_components=30, random_state=seed).fit_transform(Xs)
    tsne = TSNE(
        n_components=dim, perplexity=30, learning_rate="auto",
        init="pca", random_state=seed, max_iter=1000,
    )
    coords = tsne.fit_transform(Xs)
    return coords, "t-SNE"


def main():
    ap = argparse.ArgumentParser(description="Bangun koordinat proyeksi segmen untuk dashboard.")
    ap.add_argument("--input", required=True, help="Path ke paysim_full_scored.parquet (punya kolom cluster_kmeans).")
    ap.add_argument("--output", required=True, help="Path output segment_projection.parquet.")
    ap.add_argument("--per-segment", type=int, default=5000, help="Sampel per segmen (default 5000).")
    ap.add_argument("--method", default="umap", choices=["auto", "umap", "tsne"],
                    help="Algoritma proyeksi. 'umap' (default) bagus untuk 3D; fallback t-SNE bila umap-learn tak ada.")
    ap.add_argument("--dim", type=int, default=3, choices=[2, 3],
                    help="Dimensi proyeksi: 3 (default, scatter bisa diputar) atau 2.")
    ap.add_argument("--all-variants", action="store_true",
                    help="Buat SEMUA varian (UMAP & t-SNE, masing-masing 2D & 3D) dalam satu file "
                         "supaya dashboard bisa dropdown metode + radio dimensi. Disarankan.")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"[1/5] Membaca {args.input} ...")
    df = pd.read_parquet(args.input)
    if "cluster_kmeans" not in df.columns:
        print("ERROR: kolom 'cluster_kmeans' tidak ada di file input. Pastikan ini "
              "paysim_full_scored.parquet dari phase 4 (yang membawa label KMeans phase 2).",
              file=sys.stderr)
        sys.exit(1)
    print(f"      total {len(df):,} baris, {df['cluster_kmeans'].nunique()} segmen")

    print(f"[2/5] Mengambil sampel stratified {args.per_segment}/segmen ...")
    sample = _stratified_sample(df, args.per_segment, args.seed)
    print(f"      sampel: {len(sample):,} baris")

    feats = _pick_feature_columns(sample)
    if not feats:
        print("ERROR: tidak menemukan kolom fitur numerik untuk diproyeksikan.", file=sys.stderr)
        sys.exit(1)
    print(f"[3/5] Memakai {len(feats)} fitur: {', '.join(feats[:8])}{' ...' if len(feats) > 8 else ''}")

    X = sample[feats].astype(np.float32).fillna(0.0).to_numpy()

    variants = []
    if args.all_variants:
        for m in ("umap", "tsne"):
            for d in (2, 3):
                variants.append((m, d))
    else:
        variants.append((args.method, args.dim))

    all_out = []
    for m, d in variants:
        print(f"[proyeksi] method={m} dim={d}D - menghitung ...")
        try:
            coords, used = _project(X, m, args.seed, dim=d)
        except SystemExit:
            if args.all_variants:
                print(f"  lewati {m} {d}D (library tak tersedia)")
                continue
            raise
        part = pd.DataFrame({
            "method": used.lower().replace("-", ""),
            "dim": d,
            "proj_x": coords[:, 0].astype(np.float32),
            "proj_y": coords[:, 1].astype(np.float32),
            "proj_z": (coords[:, 2].astype(np.float32) if d == 3 else np.float32(0.0)),
            "cluster_kmeans": sample["cluster_kmeans"].astype("int16").to_numpy(),
            "isFraud": sample["isFraud"].astype(bool).to_numpy() if "isFraud" in sample.columns else False,
        })
        for opt in ("jenis_tujuan", "risk_level"):
            if opt in sample.columns:
                part[opt] = sample[opt].to_numpy()
        all_out.append(part)
        print(f"  selesai ({used} {d}D)")

    if not all_out:
        print("ERROR: tidak ada proyeksi yang berhasil dibuat.", file=sys.stderr)
        sys.exit(1)

    out = pd.concat(all_out, ignore_index=True)
    print(f"[simpan] {len(out):,} baris ({len(variants)} varian) ke {args.output} ...")
    out.to_parquet(args.output, index=False)
    print(f"SELESAI. Varian: {[f'{m}-{d}D' for m, d in variants]}. Taruh file ini di datasets/phase_4/ lalu jalankan ulang "
          f"pipeline phase 5 (python -m pipeline.flow --mode real --data-root <root>).")


if __name__ == "__main__":
    main()
