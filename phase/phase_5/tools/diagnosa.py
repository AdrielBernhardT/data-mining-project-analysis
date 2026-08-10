from __future__ import annotations
import os
import sys

_PHASE5_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PHASE5_DIR not in sys.path:
    sys.path.insert(0, _PHASE5_DIR)

try:
    os.system("")
except Exception:
    pass

def _ok(msg): print(f"  \033[92m[OK]\033[0m {msg}")
def _bad(msg): print(f"  \033[91m[MASALAH]\033[0m {msg}")
def _info(msg): print(f"  [info] {msg}")


def main():
    print("=" * 68)
    print("DIAGNOSA DASHBOARD PHASE 5")
    print("=" * 68)

    try:
        import config as cfg
    except Exception as e:
        _bad(f"Tidak bisa import config.py: {e}")
        return
    db_path = cfg.DUCKDB_PATH
    print(f"\n1. FILE DUCKDB  ({db_path})")
    if not os.path.exists(db_path):
        _bad("File DuckDB TIDAK ADA. Pipeline belum dijalankan atau gagal.")
        _info("Solusi: jalankan pipeline (lihat CARA_REBUILD.md langkah 2).")
        return
    size_mb = os.path.getsize(db_path) / 1e6
    _ok(f"File ada ({size_mb:.1f} MB)")
    if size_mb < 0.1:
        _bad("Ukuran file sangat kecil - kemungkinan pipeline gagal di tengah.")

    print("\n2. TABEL DI DALAM DUCKDB")
    try:
        import duckdb
        con = duckdb.connect(db_path, read_only=True)
    except Exception as e:
        _bad(f"Tidak bisa koneksi DuckDB: {e}")
        return
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    for t in ["transaksi", "cube", "pola", "projection"]:
        if t in tables:
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            _ok(f"tabel '{t}' ada ({n:,} baris)")
        else:
            if t == "projection":
                _info(f"tabel '{t}' tidak ada (opsional - scatter segmen nonaktif)")
            else:
                _bad(f"tabel '{t}' TIDAK ADA - ini sumber masalah!")

    print("\n3. KOLOM PENTING DI TABEL CUBE")
    if "cube" not in tables:
        _bad("Tabel cube tidak ada - lewati pengecekan kolom.")
        con.close()
        return
    cube_cols = [d[0] for d in con.execute("SELECT * FROM cube LIMIT 0").description]

    needed_segmentasi = ["cluster_kmeans", "isFraud", "risk_score", "high_risk"]
    needed_anomali = ["anomaly_type", "investigation_category",
                      "flag_IQR", "flag_ZScore", "flag_IsoForest", "flag_HDBSCAN"]

    print("   Untuk tab SEGMENTASI:")
    for c in needed_segmentasi:
        (_ok if c in cube_cols else _bad)(f"kolom '{c}' {'ada' if c in cube_cols else 'HILANG'}")
    print("   Untuk tab ANOMALI:")
    for c in needed_anomali:
        (_ok if c in cube_cols else _bad)(f"kolom '{c}' {'ada' if c in cube_cols else 'HILANG'}")

    print("\n4. ISI DATA SEGMEN")
    if "cluster_kmeans" in cube_cols:
        rows = con.execute("SELECT cluster_kmeans, SUM(n) FROM cube GROUP BY cluster_kmeans ORDER BY cluster_kmeans").fetchall()
        if rows:
            _ok(f"{len(rows)} segmen ditemukan:")
            for cid, n in rows:
                print(f"        segmen {cid}: {int(n):,} transaksi")
        else:
            _bad("cluster_kmeans ada tapi tidak ada baris - cube kosong?")

    print("\n5. ISI DATA ANOMALI")
    if "anomaly_type" in cube_cols:
        rows = con.execute("SELECT anomaly_type, SUM(n) FROM cube GROUP BY anomaly_type").fetchall()
        if rows and any(r[1] for r in rows):
            _ok(f"{len(rows)} jenis anomali ditemukan:")
            for at, n in rows[:8]:
                print(f"        {at}: {int(n):,}")
        else:
            _bad("anomaly_type kosong.")
    else:
        _bad("Kolom anomaly_type tidak ada di cube.")
        _info("Ini kenapa tab Anomali kosong. Pastikan pakai paysim_full_scored.parquet")
        _info("dari phase 4 (yang berisi flag_* & anomaly_type), lalu rebuild.")

    con.close()
    print("\n" + "=" * 68)
    print("SELESAI. Kirim seluruh output ini kalau masih bingung.")
    print("=" * 68)


if __name__ == "__main__":
    main()
