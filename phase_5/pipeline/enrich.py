"""
pipeline/enrich.py
====================
Fungsi transformasi "lapisan presentasi" yang dipakai pipeline/flow.py.

PENTING - batas tanggung jawab: modul ini TIDAK menghitung ulang clustering,
association rules, atau anomaly detection (itu tugas Phase 2-4 kelompok yang
sudah selesai dan HASILNYA dianggap final/benar). Modul ini HANYA menambah
lapisan presentasi di atas hasil tsb: label Indonesia, dimensi filter
kategorikal TAMBAHAN yang diturunkan dari kolom asli (isDestMerchant,
origDrainedToZero - lihat catatan di config.py kenapa TIDAK ada dimensi
spasial/temporal buatan), teks alasan anomali, dan penggabungan pool aturan
asosiasi - supaya angka hasil analisis asli tidak pernah diubah/ditimpa.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

import config as cfg


def derive_dest_type(df: pd.DataFrame) -> pd.Series:
    """'Merchant' / 'Nasabah' - langsung dari kolom isDestMerchant asli
    (diturunkan Phase 1 dari prefix ID tujuan: M=merchant, C=customer).
    Bukan dimensi buatan - ini atribut yang sudah ada di data.

    Kebal tipe: isDestMerchant bisa berupa bool (True/False), int (1/0), atau
    string ('1'/'0'/'True'/'M'). Semua diperlakukan benar - kalau dulu hanya
    menangani bool, nilai integer/string bikin SEMUA jadi 'Nasabah' (Merchant
    hilang dari filter)."""
    if "isDestMerchant" not in df.columns:
        return pd.Series(cfg.DEST_TYPE_LIST[1], index=df.index)
    col = df["isDestMerchant"]
    if col.dtype == bool:
        is_merchant = col
    elif pd.api.types.is_numeric_dtype(col):
        is_merchant = col.fillna(0).astype(int) == 1
    else:
        s = col.astype(str).str.strip().str.lower()
        is_merchant = s.isin(["true", "1", "1.0", "m", "merchant", "yes", "y"])
    return pd.Series(np.where(is_merchant, "Merchant", "Nasabah"), index=df.index)


def derive_drain_status(df: pd.DataFrame) -> pd.Series:
    """'Terkuras Habis' / 'Tidak Terkuras' - langsung dari kolom origDrainedToZero
    asli (saldo pengirim jadi 0 setelah transaksi). Bukan dimensi buatan."""
    if "origDrainedToZero" not in df.columns:
        return pd.Series(cfg.DRAIN_STATUS_LIST[1], index=df.index)
    return df["origDrainedToZero"].map({True: "Terkuras Habis", False: "Tidak Terkuras"}).fillna("Tidak Terkuras")


def translate_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Terjemahkan string kategori Phase 4 (Inggris) -> Indonesia. Aman dipanggil
    berkali-kali (no-op kalau kolom sudah berbahasa Indonesia). Memodifikasi df
    di tempat (TIDAK copy) - baris bisa jutaan, copy berulang = boros memori."""
    if "risk_level" in df.columns and set(df["risk_level"].unique()) & set(cfg.RISK_LEVEL_EN_TO_ID):
        df["risk_level"] = df["risk_level"].astype(str).map(lambda v: cfg.RISK_LEVEL_EN_TO_ID.get(v, v))
    if "anomaly_type" in df.columns and set(df["anomaly_type"].unique()) & set(cfg.ANOMALY_TYPE_EN_TO_ID):
        df["anomaly_type"] = df["anomaly_type"].astype(str).map(lambda v: cfg.ANOMALY_TYPE_EN_TO_ID.get(v, v))
    if "investigation_category" in df.columns and set(df["investigation_category"].unique()) & set(cfg.INVESTIGATION_CATEGORY_EN_TO_ID):
        df["investigation_category"] = df["investigation_category"].astype(str).map(
            lambda v: cfg.INVESTIGATION_CATEGORY_EN_TO_ID.get(v, v)
        )
    return df


_REASON_LOOKUP_CACHE = None


def _reason_lookup() -> np.ndarray:
    global _REASON_LOOKUP_CACHE
    if _REASON_LOOKUP_CACHE is not None:
        return _REASON_LOOKUP_CACHE
    labels = [
        "Nominal tinggi tak wajar (IQR)",
        "Nominal ekstrem (Z-Score)",
        "Kombinasi perilaku tak wajar (Isolation Forest)",
        "Menyimpang dari struktur klaster (BIRCH+HDBSCAN)",
        "Ketidaksesuaian saldo asal/tujuan",
    ]
    lookup = np.empty(32, dtype=object)
    for c in range(32):
        bits = [(c >> b) & 1 for b in range(5)]
        parts = [lbl for bit, lbl in zip(bits, labels) if bit]
        lookup[c] = "; ".join(parts) if parts else "Tidak ada indikator yang terpicu"
    _REASON_LOOKUP_CACHE = lookup
    return lookup


def compute_anomaly_reason(df: pd.DataFrame) -> pd.Series:
    """Vectorized (lookup 32 kombinasi) - JANGAN pakai df.apply(axis=1) di sini,
    terbukti lambat/OOM pada 6+ juta baris (lihat catatan proses)."""
    code = (
        df["flag_IQR"].astype(int).values * 1
        + df["flag_ZScore"].astype(int).values * 2
        + df["flag_IsoForest"].astype(int).values * 4
        + df["flag_HDBSCAN"].astype(int).values * 8
        + df.get("flag_BalanceMismatch", pd.Series(0, index=df.index)).astype(int).values * 16
    )
    return pd.Series(_reason_lookup()[code], index=df.index)


def ensure_transaction_id(df: pd.DataFrame) -> pd.Series:
    if "transaction_id" in df.columns:
        return df["transaction_id"]
    return pd.Series([f"TX{i:08d}" for i in range(len(df))], index=df.index)


def derive_anomaly_type(df: pd.DataFrame) -> pd.Series:
    """Turunkan 'anomaly_type' dari kolom flag_* ketika phase 4 tidak
    mengekspornya. Logika mengikuti definisi di config.ANOMALY_TYPE_LABELS:
    - tidak ada flag -> Tidak Ada Anomali Statistik
    - >=3 metode menandai -> Banyak Indikator Sekaligus
    - IsoForest + HDBSCAN -> Perilaku & Struktur Klaster Menyimpang
    - HDBSCAN saja -> Klaster Menyimpang (Outlier)
    - IsoForest saja -> Perilaku Menyimpang (Outlier)
    - BalanceMismatch dominan -> Ketidaksesuaian Saldo
    - IQR/ZScore (nominal) -> Nominal Transaksi Ekstrem
    """
    import numpy as np
    n = len(df)
    zero = pd.Series(0, index=df.index)
    iqr = df["flag_IQR"].astype(int) if "flag_IQR" in df.columns else zero
    zsc = df["flag_ZScore"].astype(int) if "flag_ZScore" in df.columns else zero
    iso = df["flag_IsoForest"].astype(int) if "flag_IsoForest" in df.columns else zero
    hdb = df["flag_HDBSCAN"].astype(int) if "flag_HDBSCAN" in df.columns else zero
    bal = df["flag_BalanceMismatch"].astype(int) if "flag_BalanceMismatch" in df.columns else zero

    total = iqr + zsc + iso + hdb
    out = np.full(n, "Tidak Ada Anomali Statistik", dtype=object)
    out = np.where((iqr | zsc).astype(bool) & (out == "Tidak Ada Anomali Statistik"),
                   "Nominal Transaksi Ekstrem", out)
    out = np.where(bal.astype(bool) & ~(iso | hdb).astype(bool),
                   "Ketidaksesuaian Saldo", out)
    out = np.where(iso.astype(bool) & (out != "Banyak Indikator Sekaligus"),
                   "Perilaku Menyimpang (Outlier)", out)
    out = np.where(hdb.astype(bool) & (out != "Banyak Indikator Sekaligus"),
                   "Klaster Menyimpang (Outlier)", out)
    out = np.where((iso & hdb).astype(bool),
                   "Perilaku & Struktur Klaster Menyimpang", out)
    out = np.where(total >= 3, "Banyak Indikator Sekaligus", out)
    return pd.Series(out, index=df.index)


def derive_investigation_category(df: pd.DataFrame) -> pd.Series:
    """Turunkan 'investigation_category' dari risk_score + isFraud + flags saat
    phase 4 tidak mengekspornya (config.INVESTIGATION_CATEGORY_LABELS)."""
    import numpy as np
    n = len(df)
    score = df["risk_score"] if "risk_score" in df.columns else pd.Series(0, index=df.index)
    fraud = df["isFraud"].astype(bool) if "isFraud" in df.columns else pd.Series(False, index=df.index)
    zero = pd.Series(0, index=df.index)
    bal = df["flag_BalanceMismatch"].astype(int) if "flag_BalanceMismatch" in df.columns else zero
    iso = df["flag_IsoForest"].astype(int) if "flag_IsoForest" in df.columns else zero
    hdb = df["flag_HDBSCAN"].astype(int) if "flag_HDBSCAN" in df.columns else zero

    out = np.full(n, "Normal / Perlu Perhatian Rendah", dtype=object)
    out = np.where(bal.astype(bool) & ~(iso | hdb).astype(bool),
                   "Kemungkinan Masalah Kualitas Data", out)
    out = np.where(score >= cfg.HIGH_RISK_THRESHOLD, "Berpotensi Perlu Dipantau", out)
    out = np.where(score >= cfg.CRITICAL_RISK_THRESHOLD, "Berpotensi Fraud", out)
    out = np.where((score >= cfg.CRITICAL_RISK_THRESHOLD) & (~fraud),
                   "Transaksi Sah yang Jarang Terjadi", out)
    return pd.Series(out, index=df.index)


def standardize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Selaraskan nama kolom dari output Phase 1-4 asli (mis. 'type') ke skema
    yang dipakai dashboard ('transaction_type'). Aman dipanggil di data apa pun.
    TIDAK copy df (baris bisa jutaan) - pemanggil diharapkan sudah punya
    referensi frame yang aman dimodifikasi (baru dibaca dari parquet/CSV)."""
    rename_map = {"type": "transaction_type"}
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns and v not in df.columns})
    if "transaction_type" not in df.columns:
        onehot = [c for c in df.columns if c.startswith("type_")]
        if onehot:
            df["transaction_type"] = (
                df[onehot].idxmax(axis=1).str.replace("type_", "", regex=False)
            )
    if "high_risk" not in df.columns and "risk_score" in df.columns:
        hdb = df["flag_HDBSCAN"] if "flag_HDBSCAN" in df.columns else 0
        df["high_risk"] = (df["risk_score"] >= cfg.HIGH_RISK_THRESHOLD) | (hdb == 1)
    if "jenis_tujuan" not in df.columns:
        df["jenis_tujuan"] = derive_dest_type(df)
    if "status_kuras" not in df.columns:
        df["status_kuras"] = derive_drain_status(df)
    if "transaction_id" not in df.columns:
        df["transaction_id"] = ensure_transaction_id(df)
    df = translate_categories(df)
    _has_flags = all(c in df.columns for c in ["flag_IQR", "flag_ZScore", "flag_IsoForest", "flag_HDBSCAN"])
    if "anomaly_reason" not in df.columns and _has_flags:
        df["anomaly_reason"] = compute_anomaly_reason(df)
    if "anomaly_type" not in df.columns and _has_flags:
        df["anomaly_type"] = derive_anomaly_type(df)
    if "investigation_category" not in df.columns and ("risk_score" in df.columns):
        df["investigation_category"] = derive_investigation_category(df)
    return df


RULE_FILE_CANDIDATES_TOP10 = ["top_10_final_rules.csv", "top_rules_business.csv"]
RULE_FILE_CANDIDATES_POOL = ["report_worthy_rules.csv", "fraud_focused_rules.csv", "meaningful_rules.csv"]


def _rule_group_of(antecedents: str, consequents: str) -> str:
    both = f"{antecedents} {consequents}"
    if "isFraud_yes" in consequents:
        return cfg.RULE_GROUP_FRAUD
    if "cluster_kmeans" in both:
        return cfg.RULE_GROUP_SEGMENT
    if "hdbscan_outlier" in both:
        return cfg.RULE_GROUP_OUTLIER
    return cfg.RULE_GROUP_GENERAL


def _takeaway_and_recommendation(row) -> tuple[str, str]:
    ante, cons = row["antecedents_str"], row["consequents_str"]
    both = f"{ante} {cons}"
    lift, conf = row["lift"], row["confidence"]
    if "isFraud_yes" in cons:
        takeaway = ("Pola langka, tapi begitu muncul sangat terkonsentrasi ke fraud terkonfirmasi."
                    if conf >= 0.5 else "Pola ini menaikkan konsentrasi fraud namun masih perlu konfirmasi lebih lanjut.")
        rekomendasi = ("Jadikan kombinasi ini sebagai aturan pemblokiran/review otomatis pada sistem monitoring "
                       "transaksi real-time, bukan sekadar laporan pasif. Prioritaskan tim investigasi fraud untuk "
                       "transaksi yang cocok pola ini sebelum dana keluar dari sistem.")
    elif "cluster_kmeans" in both:
        takeaway = "Pola ini menjelaskan perilaku yang secara alami melekat pada satu segmen nasabah/transaksi."
        rekomendasi = ("Pakai pola ini untuk menyusun kebijakan khusus per segmen (mis. limit transaksi atau ambang "
                       "verifikasi berbeda), bukan kebijakan seragam untuk semua nasabah.")
    elif "hdbscan_outlier" in both:
        takeaway = "Pola ini mengarah ke transaksi yang berada di luar struktur normal populasi."
        rekomendasi = "Gunakan sebagai sinyal tambahan (bukan tunggal) untuk memicu peninjauan manual."
    elif lift >= 10:
        takeaway = "Pola perilaku yang kuat, berguna untuk menjelaskan bagaimana atribut transaksi bergerak bersama."
        rekomendasi = "Manfaatkan sebagai fitur tambahan pada aturan bisnis atau model deteksi berikutnya."
    else:
        takeaway = "Pola bisnis umum yang membantu menjelaskan perilaku transaksi yang sering terjadi."
        rekomendasi = "Cocok sebagai konteks/latar belakang, bukan prioritas tindakan investigasi."
    return takeaway, rekomendasi


def build_rule_pool(phase3_dir: Optional[Path], top10_fallback: Optional[pd.DataFrame] = None,
                     logger=None) -> pd.DataFrame:
    """Muat & gabungkan pool aturan asosiasi. `top10_fallback` dipakai bila
    tidak ada berkas top-10 yang ditemukan (mis. hanya cache lama yang ada)."""
    def _log(msg):
        if logger:
            logger.info(msg)

    top10 = None
    pool_frames = []
    if phase3_dir and Path(phase3_dir).exists():
        for name in RULE_FILE_CANDIDATES_TOP10:
            p = Path(phase3_dir) / name
            if p.exists():
                top10 = pd.read_csv(p)
                _log(f"  pola 10 utama dimuat dari {p.name}")
                break
        for name in RULE_FILE_CANDIDATES_POOL:
            p = Path(phase3_dir) / name
            if p.exists():
                pool_frames.append(pd.read_csv(p))
                _log(f"  pool pola tambahan dimuat dari {p.name} ({len(pool_frames[-1])} baris)")

    if top10 is None:
        if top10_fallback is None:
            raise FileNotFoundError(
                "Tidak menemukan berkas pola 10 utama (top_10_final_rules.csv / top_rules_business.csv) "
                "maupun fallback. Sertakan salah satunya."
            )
        top10 = top10_fallback
        _log("  pola 10 utama dimuat dari cache lama (top_rules_business.parquet)")

    top10 = top10.copy()
    top10["is_real"] = True
    if pool_frames:
        pool = pd.concat(pool_frames, ignore_index=True)
        pool["is_real"] = False
        key_top10 = set(zip(top10["antecedents_str"], top10["consequents_str"]))
        pool = pool[~pool.apply(lambda r: (r["antecedents_str"], r["consequents_str"]) in key_top10, axis=1)]
        all_rules = pd.concat([top10, pool], ignore_index=True)
    else:
        _log("  tidak ada pool pola tambahan (report_worthy_rules.csv dkk) - hanya 10 pola utama tersedia")
        all_rules = top10

    all_rules["rule_group"] = all_rules.apply(lambda r: _rule_group_of(r["antecedents_str"], r["consequents_str"]), axis=1)
    all_rules["when_text"] = all_rules["antecedents_str"].apply(cfg.humanize_item_list)
    all_rules["then_text"] = all_rules["consequents_str"].apply(cfg.humanize_item_list)
    all_rules["coverage_fmt"] = all_rules["support"].apply(lambda x: cfg.format_pct(x, 3))
    all_rules["confidence_fmt"] = all_rules["confidence"].apply(lambda x: cfg.format_pct(x, 1))
    all_rules["lift_fmt"] = all_rules["lift"].apply(cfg.format_multiplier)
    tk = all_rules.apply(_takeaway_and_recommendation, axis=1, result_type="expand")
    all_rules["takeaway"], all_rules["recommendation"] = tk[0], tk[1]
    all_rules = all_rules.sort_values(["is_real", "lift"], ascending=[False, False]).reset_index(drop=True)
    all_rules["is_top10"] = all_rules["is_real"]
    all_rules["rule_id"] = [f"POLA{i+1:04d}" for i in range(len(all_rules))]
    all_rules["penting"] = np.where(all_rules["is_top10"], "Insight utama", "Insight tambahan")
    return all_rules
