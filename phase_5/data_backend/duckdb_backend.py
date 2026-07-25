"""
data_backend/duckdb_backend.py
===============================
Implementasi DataBackend memakai DuckDB. Berkas .duckdb dibangun oleh
pipeline (pipeline/flow.py) sekali di awal; dashboard hanya membukanya
sebagai READ-ONLY sehingga aman diakses banyak request sekaligus.

KUNCI PERFORMA <100ms: dua tabel dengan peran berbeda -
  - `cube`      : hasil pra-agregasi (group-by seluruh dimensi filter yang ada).
                  Semua KPI/ringkasan/statistik query tabel ini (ribuan baris,
                  bukan jutaan) sehingga tetap sangat cepat walau berjalan di
                  satu core CPU sekalipun.
  - `transaksi` : tabel baris-per-baris lengkap (6,3 juta baris), HANYA dipakai
                  untuk pencarian/penjelajahan transaksi individual (Jelajah
                  Data, Anomali) yang memang butuh baris asli, bukan agregat.
Filter rentang nominal (amount_min/max) & pencarian teks HANYA berlaku pada
`transaksi` (butuh baris individual); tidak memengaruhi ringkasan agregat.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import duckdb

from data_backend.base import DataBackend, Filters

CUBE_FILTER_COLS = {
    "jenis_tujuan": "jenis_tujuan",
    "status_kuras": "status_kuras",
    "jenis_transaksi": "transaction_type",
    "segmen": "cluster_kmeans",
    "risk_level": "risk_level",
    "investigation_category": "investigation_category",
    "anomaly_type": "anomaly_type",
}


def _cube_where(filters: Filters) -> tuple[str, list]:
    clauses, params = [], []
    mapping = {
        "jenis_tujuan": filters.jenis_tujuan,
        "status_kuras": filters.status_kuras,
        "jenis_transaksi": filters.jenis_transaksi,
        "segmen": [int(s) for s in filters.segmen] if filters.segmen else [],
        "risk_level": filters.risk_level,
        "investigation_category": filters.investigation_category,
        "anomaly_type": filters.anomaly_type,
    }
    for key, values in mapping.items():
        if values:
            clauses.append(f"{CUBE_FILTER_COLS[key]} = ANY(?)")
            params.append(list(values))
    if filters.risk_score_min is not None:
        clauses.append("risk_score >= ?")
        params.append(int(filters.risk_score_min))
    if filters.risk_score_max is not None:
        clauses.append("risk_score <= ?")
        params.append(int(filters.risk_score_max))
    if not clauses:
        return "1=1", []
    return " AND ".join(clauses), params


import re

SEARCH_KEYWORD_TO_FLAG = {
    "iqr": "flag_IQR",
    "z-score": "flag_ZScore", "zscore": "flag_ZScore", "z score": "flag_ZScore",
    "isolation forest": "flag_IsoForest", "isolation": "flag_IsoForest",
    "hdbscan": "flag_HDBSCAN", "birch": "flag_HDBSCAN", "klaster": "flag_HDBSCAN", "cluster": "flag_HDBSCAN",
    "saldo": "flag_BalanceMismatch", "balance": "flag_BalanceMismatch",
}
_ID_PATTERN = re.compile(r"^TX?\d+$", re.IGNORECASE)
_FULL_ID_LEN = 10


def _row_where(filters: Filters) -> tuple[str, list, Optional[str]]:
    """Where-clause utk tabel `transaksi` baris-penuh (dipakai search_transactions).
    Mengembalikan juga `search_mode` (None/id_prefix/keyword/ilike) supaya
    search_transactions tahu apakah count boleh diambil cepat dari cube atau
    harus scan tabel penuh (hanya saat mode='ilike' teks bebas)."""
    clauses, params = [], []
    mapping = {
        "jenis_tujuan": filters.jenis_tujuan,
        "status_kuras": filters.status_kuras,
        "transaction_type": filters.jenis_transaksi,
        "cluster_kmeans": [int(s) for s in filters.segmen] if filters.segmen else [],
        "risk_level": filters.risk_level,
        "investigation_category": filters.investigation_category,
        "anomaly_type": filters.anomaly_type,
    }
    for col, values in mapping.items():
        if values:
            clauses.append(f"{col} = ANY(?)")
            params.append(list(values))
    if filters.amount_min is not None:
        clauses.append("amount >= ?")
        params.append(float(filters.amount_min))
    if filters.amount_max is not None:
        clauses.append("amount <= ?")
        params.append(float(filters.amount_max))
    if filters.risk_score_min is not None:
        clauses.append("risk_score >= ?")
        params.append(int(filters.risk_score_min))
    if filters.risk_score_max is not None:
        clauses.append("risk_score <= ?")
        params.append(int(filters.risk_score_max))
    search_mode = None
    if filters.search:
        text = filters.search.strip()
        if _ID_PATTERN.match(text):
            prefix = text.upper()
            if not prefix.startswith("TX"):
                prefix = "TX" + prefix.lstrip("T").lstrip("X")
            if len(prefix) >= _FULL_ID_LEN:
                search_mode = "id_exact"
                clauses.append("transaction_id = ?")
                params.append(prefix[:_FULL_ID_LEN])
            else:
                search_mode = "id_prefix"
                clauses.append("transaction_id LIKE ?")
                params.append(f"{prefix}%")
        elif text.lower() in SEARCH_KEYWORD_TO_FLAG:
            search_mode = "keyword"
            clauses.append(f"{SEARCH_KEYWORD_TO_FLAG[text.lower()]} = true")
        else:
            search_mode = "ilike"
            clauses.append("(transaction_id ILIKE ? OR anomaly_reason ILIKE ?)")
            needle = f"%{text}%"
            params.extend([needle, needle])
    if not clauses:
        return "1=1", [], None
    return " AND ".join(clauses), params, search_mode


class DuckDBBackend(DataBackend):
    name = "duckdb"

    def __init__(self, db_path: str, read_only: bool = True):
        self.db_path = db_path
        self._con = duckdb.connect(db_path, read_only=read_only)

    def ping(self) -> bool:
        try:
            self._con.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def _rows(self, sql: str, params: list) -> list[dict]:
        cur = self._con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _cube_has(self, column: str) -> bool:
        """True kalau `column` ada di tabel cube. Dipakai untuk menjaga agar
        query anomali tidak error saat phase 4 tak mengekspor kolom tsb -
        grafik cukup kosong dengan pesan, bukan crash seluruh halaman."""
        try:
            cols = [d[0] for d in self._con.execute("SELECT * FROM cube LIMIT 0").description]
            return column in cols
        except Exception:
            return False

    def get_kpi(self, filters: Filters) -> dict[str, Any]:
        where, params = _cube_where(filters)
        sql = f"""
            SELECT
                SUM(n)                                            AS total_transaksi,
                SUM(CASE WHEN isFraud THEN n ELSE 0 END)           AS total_fraud,
                SUM(CASE WHEN high_risk THEN n ELSE 0 END)         AS total_high_risk,
                SUM(CASE WHEN risk_level='Kritis' THEN n ELSE 0 END) AS total_kritis,
                SUM(risk_score * n)::DOUBLE / NULLIF(SUM(n), 0)    AS avg_risk_score,
                SUM(CASE WHEN high_risk AND isFraud THEN n ELSE 0 END) AS high_risk_fraud_n
            FROM cube WHERE {where}
        """
        row = self._rows(sql, params)[0]
        total = row["total_transaksi"] or 0
        fraud = row["total_fraud"] or 0
        high_risk = row["total_high_risk"] or 0
        fraud_rate = (fraud / total) if total else 0.0
        high_risk_rate = (high_risk / total) if total else 0.0
        baseline_fraud_rate = 0.0012883
        high_risk_fraud_rate = (row["high_risk_fraud_n"] / high_risk) if high_risk else None
        enrichment = (high_risk_fraud_rate / baseline_fraud_rate) if high_risk_fraud_rate else None
        return dict(
            total_transaksi=total, total_fraud=fraud, total_high_risk=high_risk,
            total_kritis=row["total_kritis"] or 0,
            fraud_rate=fraud_rate, high_risk_rate=high_risk_rate,
            avg_risk_score=row["avg_risk_score"] or 0.0,
            high_risk_fraud_rate=high_risk_fraud_rate, fraud_enrichment=enrichment,
        )

    def get_segment_summary(self, filters: Filters) -> list[dict]:
        where, params = _cube_where(filters)
        sql = f"""
            SELECT cluster_kmeans,
                   SUM(n) AS transactions,
                   SUM(CASE WHEN isFraud THEN n ELSE 0 END) AS fraud_count,
                   SUM(risk_score * n)::DOUBLE / NULLIF(SUM(n),0) AS avg_risk_score,
                   SUM(CASE WHEN high_risk THEN n ELSE 0 END) AS high_risk_count,
                   SUM(CASE WHEN risk_level='Kritis' THEN n ELSE 0 END) AS critical_count
            FROM cube WHERE {where}
            GROUP BY cluster_kmeans ORDER BY cluster_kmeans
        """
        rows = self._rows(sql, params)
        total_all = sum(r["transactions"] for r in rows) or 1
        for r in rows:
            r["population_share"] = r["transactions"] / total_all
            r["fraud_rate"] = (r["fraud_count"] / r["transactions"]) if r["transactions"] else 0.0
            r["high_risk_rate"] = (r["high_risk_count"] / r["transactions"]) if r["transactions"] else 0.0
        return rows

    def get_risk_summary(self, filters: Filters) -> list[dict]:
        where, params = _cube_where(filters)
        sql = f"SELECT risk_level, SUM(n) AS transactions FROM cube WHERE {where} GROUP BY risk_level"
        rows = self._rows(sql, params)
        total = sum(r["transactions"] for r in rows) or 1
        for r in rows:
            r["percentage"] = 100.0 * r["transactions"] / total
        return rows

    def get_anomaly_type_summary(self, filters: Filters) -> list[dict]:
        if not self._cube_has("anomaly_type"):
            return []
        where, params = _cube_where(filters)
        sql = f"SELECT anomaly_type, SUM(n) AS transactions FROM cube WHERE {where} GROUP BY anomaly_type"
        rows = self._rows(sql, params)
        total = sum(r["transactions"] for r in rows) or 1
        for r in rows:
            r["percentage"] = 100.0 * r["transactions"] / total
        return rows

    def get_investigation_summary(self, filters: Filters) -> list[dict]:
        if not self._cube_has("investigation_category"):
            return []
        where, params = _cube_where(filters)
        sql = f"SELECT investigation_category, SUM(n) AS transactions FROM cube WHERE {where} GROUP BY investigation_category"
        rows = self._rows(sql, params)
        total = sum(r["transactions"] for r in rows) or 1
        for r in rows:
            r["percentage"] = 100.0 * r["transactions"] / total
        return rows

    def get_segment_projection(self, filters: Filters, method: str | None = None, dim: int | None = None) -> list[dict]:
        """Kembalikan titik koordinat UMAP/t-SNE untuk scatter segmen. Membaca
        tabel `projection`. method ('umap'/'tsne') & dim (2/3) memilih varian
        kalau file punya beberapa varian (kolom method/dim). Kalau tabel/varian
        tak ada, kembalikan [] supaya dashboard tetap jalan."""
        try:
            has = self._con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'projection'"
            ).fetchone()[0]
        except Exception:
            has = 0
        if not has:
            return []

        conds, params = [], []
        proj_cols = [d[0] for d in self._con.execute("SELECT * FROM projection LIMIT 0").description]
        if method and "method" in proj_cols:
            conds.append("method = ?")
            params.append(method.lower())
        if dim and "dim" in proj_cols:
            conds.append("dim = ?")
            params.append(int(dim))
        if getattr(filters, "jenis_tujuan", None) and "jenis_tujuan" in proj_cols:
            conds.append("jenis_tujuan = ANY(?)")
            params.append(list(filters.jenis_tujuan))
        if getattr(filters, "segmen", None):
            conds.append("cluster_kmeans = ANY(?)")
            params.append([int(s) for s in filters.segmen])
        where = " AND ".join(conds) if conds else "TRUE"
        want_z = ("proj_z" in proj_cols) and (dim != 2)
        z_col = ", proj_z" if want_z else ""
        max_points = 3000
        try:
            total = self._con.execute(
                f"SELECT COUNT(*) FROM projection WHERE {where}", params
            ).fetchone()[0]
        except Exception:
            total = 0
        sample_clause = ""
        if total > max_points:
            pct = max(1.0, (max_points / total) * 100.0)
            sample_clause = f" USING SAMPLE {pct:.2f} PERCENT (bernoulli, 42)"
        sql = f"SELECT proj_x, proj_y{z_col}, cluster_kmeans, isFraud FROM projection WHERE {where}{sample_clause}"
        return self._rows(sql, params)

    def get_cluster_profile(self, filters: Filters) -> list[dict]:
        """Profil tiap segmen dari cube: komposisi jenis transaksi dominan,
        tingkat fraud, high-risk, dan tujuan merchant. Dipakai untuk kartu/tabel
        profil di halaman Segmentasi. Kebal terhadap kolom yang hilang -
        kolom yang tak ada cukup dilewati, bukan menjatuhkan seluruh halaman."""
        if not self._cube_has("cluster_kmeans"):
            return []
        where, params = _cube_where(filters)

        has_merchant = self._cube_has("jenis_tujuan")
        has_drain = self._cube_has("status_kuras")
        merchant_expr = "SUM(CASE WHEN jenis_tujuan='Merchant' THEN n ELSE 0 END)" if has_merchant else "0"
        drain_expr = "SUM(CASE WHEN status_kuras='Terkuras Habis' THEN n ELSE 0 END)" if has_drain else "0"

        sql = f"""
            SELECT cluster_kmeans,
                   SUM(n) AS total,
                   SUM(CASE WHEN isFraud THEN n ELSE 0 END) AS fraud,
                   SUM(CASE WHEN high_risk THEN n ELSE 0 END) AS high_risk,
                   {merchant_expr} AS to_merchant,
                   {drain_expr} AS drained
            FROM cube WHERE {where}
            GROUP BY cluster_kmeans ORDER BY cluster_kmeans
        """
        rows = self._rows(sql, params)

        dominant = {}
        if self._cube_has("transaction_type"):
            sql2 = f"""
                SELECT cluster_kmeans, transaction_type, SUM(n) AS n
                FROM cube WHERE {where}
                GROUP BY cluster_kmeans, transaction_type
            """
            for r in self._rows(sql2, params):
                cid = r["cluster_kmeans"]
                if cid not in dominant or r["n"] > dominant[cid][1]:
                    dominant[cid] = (r["transaction_type"], r["n"])

        for r in rows:
            t = r["total"] or 1
            cid = r["cluster_kmeans"]
            r["fraud_rate"] = r["fraud"] / t
            r["high_risk_rate"] = r["high_risk"] / t
            r["merchant_share"] = (r["to_merchant"] / t) if has_merchant else 0.0
            r["drained_share"] = (r["drained"] / t) if has_drain else 0.0
            dom = dominant.get(cid, ("-", 0))
            r["dominant_type"] = dom[0]
            r["dominant_type_share"] = (dom[1] / t) if t else 0.0
        return rows

    def get_fraud_by_score(self, filters: Filters) -> list[dict]:
        where, params = _cube_where(filters)
        sql = f"""
            SELECT risk_score, SUM(n) AS transactions,
                   SUM(CASE WHEN isFraud THEN n ELSE 0 END) AS fraud_count
            FROM cube WHERE {where} GROUP BY risk_score ORDER BY risk_score
        """
        rows = self._rows(sql, params)
        for r in rows:
            r["fraud_rate"] = (r["fraud_count"] / r["transactions"]) if r["transactions"] else 0.0
        return rows

    def get_method_overlap(self, filters: Filters) -> list[dict]:
        methods = ["flag_IQR", "flag_ZScore", "flag_IsoForest", "flag_HDBSCAN"]
        if not all(self._cube_has(m) for m in methods):
            return []
        where, params = _cube_where(filters)
        select_bits = []
        for m1 in methods:
            for m2 in methods:
                select_bits.append(f"SUM(CASE WHEN {m1} AND {m2} THEN n ELSE 0 END) AS {m1}__{m2}")
        sql = f"SELECT {', '.join(select_bits)} FROM cube WHERE {where}"
        row = self._rows(sql, params)[0]
        matrix = []
        for m1 in methods:
            entry = {"method": m1}
            for m2 in methods:
                entry[m2] = row.get(f"{m1}__{m2}", 0) or 0
            matrix.append(entry)
        return matrix

    def get_dest_type_breakdown(self, filters: Filters) -> list[dict]:
        where, params = _cube_where(filters)
        sql = f"""
            SELECT jenis_tujuan, SUM(n) AS transactions,
                   SUM(CASE WHEN isFraud THEN n ELSE 0 END) AS fraud_count,
                   SUM(CASE WHEN high_risk THEN n ELSE 0 END) AS high_risk_count,
                   SUM(risk_score * n)::DOUBLE / NULLIF(SUM(n),0) AS avg_risk_score
            FROM cube WHERE {where} GROUP BY jenis_tujuan ORDER BY transactions DESC
        """
        rows = self._rows(sql, params)
        total = sum(r["transactions"] for r in rows) or 1
        for r in rows:
            r["share"] = r["transactions"] / total
            r["fraud_rate"] = (r["fraud_count"] / r["transactions"]) if r["transactions"] else 0.0
            r["high_risk_rate"] = (r["high_risk_count"] / r["transactions"]) if r["transactions"] else 0.0
        return rows

    def get_drain_status_breakdown(self, filters: Filters) -> list[dict]:
        where, params = _cube_where(filters)
        sql = f"""
            SELECT status_kuras, SUM(n) AS transactions,
                   SUM(CASE WHEN isFraud THEN n ELSE 0 END) AS fraud_count,
                   SUM(CASE WHEN high_risk THEN n ELSE 0 END) AS high_risk_count,
                   SUM(risk_score * n)::DOUBLE / NULLIF(SUM(n),0) AS avg_risk_score
            FROM cube WHERE {where} GROUP BY status_kuras ORDER BY transactions DESC
        """
        rows = self._rows(sql, params)
        total = sum(r["transactions"] for r in rows) or 1
        for r in rows:
            r["share"] = r["transactions"] / total
            r["fraud_rate"] = (r["fraud_count"] / r["transactions"]) if r["transactions"] else 0.0
            r["high_risk_rate"] = (r["high_risk_count"] / r["transactions"]) if r["transactions"] else 0.0
        return rows

    def get_transaction_type_breakdown(self, filters: Filters) -> list[dict]:
        if not self._cube_has("transaction_type"):
            return []
        where, params = _cube_where(filters)
        sql = f"""
            SELECT transaction_type, SUM(n) AS transactions,
                   SUM(CASE WHEN isFraud THEN n ELSE 0 END) AS fraud_count
            FROM cube WHERE {where} GROUP BY transaction_type ORDER BY transactions DESC
        """
        rows = self._rows(sql, params)
        total = sum(r["transactions"] for r in rows) or 1
        for r in rows:
            r["share"] = r["transactions"] / total
            r["fraud_rate"] = (r["fraud_count"] / r["transactions"]) if r["transactions"] else 0.0
        return rows

    def search_transactions(
        self, filters: Filters, sort_col: str = "risk_score", sort_dir: str = "desc",
        page: int = 1, page_size: int = 25,
    ) -> tuple[list[dict], int]:
        where, params, search_mode = _row_where(filters)
        safe_cols = {
            "risk_score", "amount", "step", "transaction_type", "jenis_tujuan",
            "cluster_kmeans", "risk_level", "isFraud", "anomaly_type",
        }
        if sort_col not in safe_cols:
            sort_col = "risk_score"
        sort_dir = "DESC" if str(sort_dir).lower().startswith("desc") else "ASC"

        no_amount_filter = filters.amount_min is None and filters.amount_max is None
        skip_count = False
        if search_mode is None and no_amount_filter:
            total = self.count(filters)
        elif search_mode == "id_exact":
            skip_count = True
            total = None
        else:
            count_sql = f"SELECT COUNT(*) AS n FROM (SELECT 1 FROM transaksi WHERE {where} LIMIT 50001)"
            total = self._rows(count_sql, params)[0]["n"]

        offset = max(0, (page - 1) * page_size)
        order_clause = f"ORDER BY {sort_col} {sort_dir}" if search_mode != "id_exact" else ""
        wanted = ["transaction_id", "step", "transaction_type", "amount", "jenis_tujuan",
                  "status_kuras", "cluster_kmeans", "risk_score", "risk_level",
                  "investigation_category", "anomaly_type", "anomaly_reason", "isFraud"]
        try:
            present = {d[0] for d in self._con.execute("SELECT * FROM transaksi LIMIT 0").description}
        except Exception:
            present = set(wanted)
        select_cols = ", ".join(c if c in present else f"NULL AS {c}" for c in wanted)
        data_sql = f"""
            SELECT {select_cols}
            FROM transaksi WHERE {where}
            {order_clause}
            LIMIT ? OFFSET ?
        """
        rows = self._rows(data_sql, params + [page_size, offset])
        if skip_count:
            total = len(rows)
        return rows, total

    def get_rules(self, rule_group: Optional[str] = None, min_lift: float = 0.0,
                  search: str = "", limit: Optional[int] = None,
                  min_confidence: float = 0.0, attribute: Optional[str] = None) -> list[dict]:
        clauses = ["1=1"]
        params: list = []
        if rule_group:
            clauses.append("rule_group = ?")
            params.append(rule_group)
        if min_lift:
            clauses.append("lift >= ?")
            params.append(float(min_lift))
        if min_confidence:
            clauses.append("confidence >= ?")
            params.append(float(min_confidence))
        if attribute:
            clauses.append("(antecedents_str ILIKE ? OR consequents_str ILIKE ?)")
            atom = f"%{attribute}%"
            params.extend([atom, atom])
        if search:
            clauses.append("(when_text ILIKE ? OR then_text ILIKE ?)")
            needle = f"%{search}%"
            params.extend([needle, needle])
        where = " AND ".join(clauses)
        sql = f"SELECT * FROM pola WHERE {where} ORDER BY is_top10 DESC, lift DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(int(limit))
        return self._rows(sql, params)

    def count(self, filters: Filters) -> int:
        where, params = _cube_where(filters)
        row = self._rows(f"SELECT SUM(n) AS n FROM cube WHERE {where}", params)[0]
        return row["n"] or 0

    def close(self):
        self._con.close()


def benchmark(db_path: str, n_iterations: int = 25) -> dict:
    """Ukur latensi nyata beberapa jenis query - dipakai README bagian performa."""
    backend = DuckDBBackend(db_path, read_only=True)
    scenarios = {
        "kpi_tanpa_filter": lambda: backend.get_kpi(Filters()),
        "kpi_dgn_filter_jenis_tujuan": lambda: backend.get_kpi(Filters(jenis_tujuan=["Merchant"])),
        "kpi_filter_kompleks": lambda: backend.get_kpi(
            Filters(jenis_tujuan=["Merchant"], status_kuras=["Terkuras Habis"], risk_level=["Tinggi", "Kritis"], segmen=[1, 2])
        ),
        "segmen_summary": lambda: backend.get_segment_summary(Filters()),
        "dest_type_breakdown": lambda: backend.get_dest_type_breakdown(Filters()),
        "drain_status_breakdown": lambda: backend.get_drain_status_breakdown(Filters()),
        "method_overlap": lambda: backend.get_method_overlap(Filters()),
        "cari_transaksi_hal_1": lambda: backend.search_transactions(Filters(), page=1, page_size=25),
        "cari_dgn_filter_kompleks": lambda: backend.search_transactions(
            Filters(risk_level=["Tinggi", "Kritis"], jenis_tujuan=["Merchant"], status_kuras=["Terkuras Habis"]), page=1, page_size=25,
        ),
        "cari_dgn_teks": lambda: backend.search_transactions(Filters(search="TX0001"), page=1, page_size=25),
    }
    results = {}
    for label, fn in scenarios.items():
        durations = []
        for _ in range(n_iterations):
            t0 = time.perf_counter()
            fn()
            durations.append((time.perf_counter() - t0) * 1000)
        durations.sort()
        results[label] = {
            "min_ms": round(durations[0], 2),
            "median_ms": round(durations[len(durations) // 2], 2),
            "max_ms": round(durations[-1], 2),
        }
    backend.close()
    return results
