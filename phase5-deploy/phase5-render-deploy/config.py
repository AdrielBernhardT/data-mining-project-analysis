from __future__ import annotations
import os

ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
ES_INDEX_TRANSAKSI = "paysim_transaksi"
ES_INDEX_POLA = "paysim_pola_asosiasi"
FORCE_BACKEND = os.environ.get("PAYSIM_BACKEND", "").lower()

DATA_DIR = os.environ.get("PAYSIM_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
DUCKDB_PATH = os.path.join(DATA_DIR, "paysim_dashboard.duckdb")

SEGMENT_NAMES = {
    0: "Tarik Tunai Volume Besar",
    1: "Pembayaran Merchant (Risiko Tertinggi)",
    2: "Transaksi Campuran",
    3: "Setor Tunai Bersaldo Tinggi",
    4: "Pembayaran Merchant Nominal Kecil",
}

SEGMENT_PROFILE = {
    0: "Segmen terbesar (32,7% populasi), didominasi transaksi tarik tunai "
       "(CASH_OUT ~80%) antar sesama akun nasabah. Hampir separuh transaksinya "
       "menguras saldo pengirim hingga nol. Tingkat fraud sangat rendah, namun "
       "volumenya besar sehingga penting sebagai populasi acuan operasional.",
    1: "Kelompok pembayaran ke merchant (PAYMENT ~78%) dengan ketidaksesuaian "
       "saldo pengirim yang sangat rendah. Meski bukan segmen terbesar, tingkat "
       "fraud-nya TERTINGGI di antara semua segmen (jauh di atas baseline) - "
       "segmen paling layak diprioritaskan untuk pemantauan fraud.",
    2: "Segmen paling heterogen: campuran tarik tunai, setor tunai, dan "
       "pembayaran tanpa satu jenis yang benar-benar dominan. Berguna sebagai "
       "kelompok perilaku transaksi umum yang tidak masuk pola spesifik lain.",
    3: "Kelompok yang hampir seluruhnya setor tunai (CASH_IN ~99,6%) dengan "
       "saldo awal pengirim di atas rata-rata. Lebih tepat dibaca sebagai "
       "segmen perilaku likuiditas dibanding segmen fraud (fraud sangat rendah).",
    4: "Kelompok pembayaran ke merchant (PAYMENT ~99,2%) bernominal kecil dengan "
       "saldo pengirim rendah. Nyaris tidak ada fraud - profil transaksi ritel "
       "rutin bernilai rendah.",
}

SEGMENT_VALUE = {
    0: "Gunakan sebagai populasi acuan (baseline) tarik tunai untuk perbandingan kebijakan.",
    1: "Prioritaskan untuk aturan pemantauan/review fraud - konsentrasi fraud tertinggi.",
    2: "Berguna sebagai kelompok perilaku umum; pantau bila ada pergeseran komposisi jenis transaksi.",
    3: "Berguna untuk memantau perilaku pendanaan/likuiditas setor tunai bersaldo tinggi.",
    4: "Cocok sebagai kelompok transaksi ritel rutin bernilai rendah dengan risiko minimal.",
}

SEGMENT_BEHAVIOR = {
    0: "Tarik tunai antar nasabah, sebagian besar menguras saldo pengirim",
    1: "Pembayaran ke merchant dengan ketidaksesuaian saldo pengirim rendah",
    2: "Perilaku transaksi campuran tanpa jenis dominan tunggal",
    3: "Setor tunai dengan saldo awal pengirim tinggi",
    4: "Pembayaran ke merchant bernominal kecil",
}

SEGMENT_ICON = {0: "💸", 1: "⚠️", 2: "🔀", 3: "💰", 4: "🛒"}


DEST_TYPE_LIST = ["Merchant", "Nasabah"]
DEST_TYPE_DESC = "Merchant = tujuan berupa akun bisnis (prefix 'M' pada ID tujuan asli). Nasabah = tujuan berupa akun perorangan (prefix 'C')."

DRAIN_STATUS_LIST = ["Terkuras Habis", "Tidak Terkuras"]
DRAIN_STATUS_DESC = "'Terkuras Habis' berarti saldo pengirim menjadi Rp0 tepat setelah transaksi ini - pola yang relevan untuk kasus pengurasan akun (account takeover)."

TRANSACTION_TYPE_LABELS = {
    "CASH_IN": "Setor Tunai",
    "CASH_OUT": "Tarik Tunai",
    "DEBIT": "Debit",
    "PAYMENT": "Pembayaran",
    "TRANSFER": "Transfer",
}


def humanize_transaction_type(value) -> str:
    key = str(value).strip().upper()
    return TRANSACTION_TYPE_LABELS.get(key, str(value).replace("_", " ").title())


RISK_LEVELS = ["Normal", "Rendah", "Sedang", "Tinggi", "Kritis"]
RISK_SCORE_TO_LEVEL = {0: "Normal", 1: "Rendah", 2: "Sedang", 3: "Tinggi", 4: "Tinggi", 5: "Kritis", 6: "Kritis"}
HIGH_RISK_THRESHOLD = 3
CRITICAL_RISK_THRESHOLD = 5

RISK_LEVEL_EN_TO_ID = {"Normal": "Normal", "Low": "Rendah", "Medium": "Sedang", "High": "Tinggi", "Critical": "Kritis"}
ANOMALY_TYPE_EN_TO_ID = {
    "No Statistical Anomaly": "Tidak Ada Anomali Statistik",
    "Balance Mismatch": "Ketidaksesuaian Saldo",
    "Extreme Transaction Amount": "Nominal Transaksi Ekstrem",
    "Multiple Indicators": "Banyak Indikator Sekaligus",
    "Cluster Outlier": "Klaster Menyimpang (Outlier)",
    "Behavioral Outlier": "Perilaku Menyimpang (Outlier)",
    "Behavioral and Cluster Outlier": "Perilaku & Struktur Klaster Menyimpang",
}
INVESTIGATION_CATEGORY_EN_TO_ID = {
    "Normal / Low Concern": "Normal / Perlu Perhatian Rendah",
    "Possible Data Quality Issue": "Kemungkinan Masalah Kualitas Data",
    "Potential Risk / Monitor": "Berpotensi Perlu Dipantau",
    "Potential Fraud": "Berpotensi Fraud",
    "Rare Legitimate Transaction": "Transaksi Sah yang Jarang Terjadi",
}

RISK_LEVEL_DESC = {
    "Normal": "Tidak ada indikator kejanggalan yang terpicu.",
    "Rendah": "Satu indikator ringan terpicu (umumnya nominal di luar rentang wajar/IQR).",
    "Sedang": "Kombinasi indikator dengan bobot menengah - secara historis justru menyimpan "
              "konsentrasi fraud tertinggi di antara semua level (lihat halaman Anomali).",
    "Tinggi": "Beberapa indikator bobot tinggi terpicu bersamaan (mis. Isolation Forest + HDBSCAN).",
    "Kritis": "Hampir seluruh indikator anomali terpicu bersamaan.",
}

ANOMALY_TYPE_LABELS = [
    "Tidak Ada Anomali Statistik",
    "Ketidaksesuaian Saldo",
    "Nominal Transaksi Ekstrem",
    "Banyak Indikator Sekaligus",
    "Klaster Menyimpang (Outlier)",
    "Perilaku Menyimpang (Outlier)",
    "Perilaku & Struktur Klaster Menyimpang",
]

ANOMALY_TYPE_DESC = {
    "Tidak Ada Anomali Statistik": "Tidak ada metode deteksi yang menandai transaksi ini.",
    "Ketidaksesuaian Saldo": "Selisih antara saldo yang diharapkan dan saldo aktual (origError/destError) "
                             "berada di luar rentang wajar - bisa jadi indikasi kesalahan pencatatan atau upaya penyamaran transaksi.",
    "Nominal Transaksi Ekstrem": "Nominal transaksi jauh di luar rentang wajar populasi (ditandai IQR dan/atau Z-Score).",
    "Banyak Indikator Sekaligus": "Tiga atau lebih metode deteksi menandai transaksi yang sama - sinyal paling kuat untuk ditindaklanjuti.",
    "Klaster Menyimpang (Outlier)": "Transaksi ini menyimpang dari struktur klaster keseluruhan (BIRCH+HDBSCAN) walau nominalnya sendiri tidak ekstrem.",
    "Perilaku Menyimpang (Outlier)": "Ditandai model perilaku (Isolation Forest) saja - kombinasi fitur numeriknya tidak wajar walau tidak masuk kategori lain.",
    "Perilaku & Struktur Klaster Menyimpang": "Ditandai baik oleh model perilaku (Isolation Forest) maupun struktur klaster (HDBSCAN) - kombinasi dua sudut pandang berbeda.",
}

INVESTIGATION_CATEGORY_LABELS = [
    "Normal / Perlu Perhatian Rendah",
    "Kemungkinan Masalah Kualitas Data",
    "Berpotensi Perlu Dipantau",
    "Berpotensi Fraud",
    "Transaksi Sah yang Jarang Terjadi",
]

ANOMALY_METHODS = [
    dict(
        key="flag_IQR", nama="IQR (Interquartile Range)", bobot=1, kategori="Univariat",
        fitur=["amount"],
        deskripsi="Menandai transaksi bila nominalnya berada di luar rentang "
                  "[Q1 − 1.5×IQR, Q3 + 1.5×IQR]. Sederhana, cepat, dan jadi jaring pertama.",
    ),
    dict(
        key="flag_ZScore", nama="Z-Score", bobot=1, kategori="Univariat",
        fitur=["amount"],
        deskripsi="Menandai transaksi bila nominalnya berjarak lebih dari 3 deviasi "
                  "standar dari rata-rata. Melihat sudut pandang yang mirip IQR namun "
                  "dengan asumsi sebaran berbeda - hampir selalu tumpang tindih dengan IQR.",
    ),
    dict(
        key="flag_IsoForest", nama="Isolation Forest", bobot=2, kategori="Multivariat",
        fitur=["amount", "origError", "destError"],
        deskripsi="Melihat KOMBINASI tiga fitur sekaligus, bukan satu-satu. Bisa menangkap "
                  "transaksi yang masing-masing nilainya biasa saja, tapi kombinasinya tidak wajar.",
    ),
    dict(
        key="flag_HDBSCAN", nama="BIRCH + HDBSCAN (outlier struktural)", bobot=2, kategori="Struktural",
        fitur=["seluruh fitur hasil rekayasa Phase 1-2 (bukan hanya nominal)"],
        deskripsi="Menandai transaksi yang posisinya menyimpang dari struktur klaster populasi "
                  "secara keseluruhan. Terbukti menangkap ratusan transaksi yang TIDAK tertangkap "
                  "oleh ketiga metode berbasis nominal di atas (lihat kajian tumpang-tindih metode).",
    ),
    dict(
        key="flag_BalanceMismatch", nama="Ketidaksesuaian Saldo", bobot=0, kategori="Cross-check",
        fitur=["origError", "destError"],
        deskripsi="Pemeriksaan silang terpisah (IQR pada origError/destError) - tidak menambah "
                  "skor risiko numerik, tapi dipakai untuk mengklasifikasikan jenis & kategori investigasi.",
    ),
]

ANOMALY_METHODS_LOOKUP = {m["key"]: m["nama"] for m in ANOMALY_METHODS}

ANOMALY_JUSTIFICATION = (
    "Tidak dipakai satu metode saja karena masing-masing metode punya titik buta yang berbeda. "
    "IQR dan Z-Score sama-sama hanya melihat satu angka (nominal transaksi) sehingga cepat namun "
    "mudah dilewati transaksi yang nominalnya biasa tapi polanya aneh. Isolation Forest melihat "
    "kombinasi tiga fitur numerik sekaligus sehingga bisa menangkap kombinasi yang tidak wajar. "
    "BIRCH+HDBSCAN melihat seluruh struktur data hasil rekayasa fitur, sehingga bisa menandai "
    "transaksi yang menyimpang dari populasi walau nominalnya sendiri tidak ekstrem. Kajian "
    "tumpang-tindih antar metode membuktikan manfaat pendekatan ini: dari seluruh transaksi yang "
    "ditandai BIRCH+HDBSCAN, sebagian besar TIDAK pernah ditandai oleh IQR: artinya mengandalkan "
    "satu metode berbasis nominal saja akan melewatkan kelompok transaksi ini sepenuhnya. Skor "
    "risiko akhir (0-6) adalah gabungan berbobot dari keempat metode ini, lalu divalidasi terhadap "
    "label fraud historis (lihat metrik validasi pada halaman Anomali)."
)

RULE_GROUP_FRAUD = "Pola Fraud"
RULE_GROUP_SEGMENT = "Pola Segmen"
RULE_GROUP_OUTLIER = "Pola Outlier"
RULE_GROUP_GENERAL = "Perilaku Umum"
RULE_GROUP_ORDER = [RULE_GROUP_FRAUD, RULE_GROUP_SEGMENT, RULE_GROUP_OUTLIER, RULE_GROUP_GENERAL]

def _segment_item_labels():
    return {f"cluster_kmeans_{i}": f"Segmen {i}: {SEGMENT_NAMES[i]}" for i in SEGMENT_NAMES}


ITEM_LABELS = {
    "isFraud_yes": "berstatus fraud terkonfirmasi",
    "isFraud_no": "tidak berlabel fraud",
    "hdbscan_outlier": "outlier klaster (struktural)",
    "hdbscan_normal": "posisi klaster normal",
    "orig_drained_yes": "saldo pengirim terkuras hingga nol",
    "orig_drained_no": "saldo pengirim tidak terkuras hingga nol",
    "dest_merchant_yes": "tujuan berupa akun merchant",
    "dest_merchant_no": "tujuan berupa akun nasabah",
    "type_CASH_IN": "transaksi setor tunai",
    "type_CASH_OUT": "transaksi tarik tunai",
    "type_DEBIT": "transaksi debit",
    "type_PAYMENT": "transaksi pembayaran",
    "type_TRANSFER": "transaksi transfer",
    **_segment_item_labels(),
    "amount_very_low": "nominal transaksi sangat rendah",
    "amount_low": "nominal transaksi rendah",
    "amount_medium": "nominal transaksi sedang",
    "amount_high": "nominal transaksi tinggi",
    "amount_very_high": "nominal transaksi sangat tinggi",
    "oldbalanceOrg_very_low": "saldo awal pengirim sangat rendah",
    "oldbalanceOrg_low": "saldo awal pengirim rendah",
    "oldbalanceOrg_medium": "saldo awal pengirim sedang",
    "oldbalanceOrg_high": "saldo awal pengirim tinggi",
    "oldbalanceOrg_very_high": "saldo awal pengirim sangat tinggi",
    "oldbalanceDest_very_low": "saldo awal penerima sangat rendah",
    "oldbalanceDest_low": "saldo awal penerima rendah",
    "oldbalanceDest_medium": "saldo awal penerima sedang",
    "oldbalanceDest_high": "saldo awal penerima tinggi",
    "oldbalanceDest_very_high": "saldo awal penerima sangat tinggi",
    "origError_very_low": "ketidaksesuaian saldo pengirim sangat rendah",
    "origError_low": "ketidaksesuaian saldo pengirim rendah",
    "origError_medium": "ketidaksesuaian saldo pengirim sedang",
    "origError_high": "ketidaksesuaian saldo pengirim tinggi",
    "origError_very_high": "ketidaksesuaian saldo pengirim sangat tinggi",
    "destError_very_low": "ketidaksesuaian saldo penerima sangat rendah",
    "destError_low": "ketidaksesuaian saldo penerima rendah",
    "destError_medium": "ketidaksesuaian saldo penerima sedang",
    "destError_high": "ketidaksesuaian saldo penerima tinggi",
    "destError_very_high": "ketidaksesuaian saldo penerima sangat tinggi",
}


def humanize_item(item: str) -> str:
    item = str(item).strip()
    return ITEM_LABELS.get(item, item.replace("_", " "))


def humanize_item_list(items) -> str:
    if isinstance(items, str):
        parts = [humanize_item(p) for p in items.split(",") if p.strip()]
    else:
        parts = [humanize_item(p) for p in items]
    if not parts:
        return "-"
    if len(parts) == 1:
        return parts[0]
    return " DAN ".join(parts)


def format_pct(value, decimals: int = 2) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{v * 100:.{decimals}f}%".replace(".", ",")


def format_int(value) -> str:
    try:
        return f"{int(round(float(value))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def format_rupiah(value, decimals: int = 0) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    s = f"{v:,.{decimals}f}"
    s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"Rp{s}"


def format_multiplier(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{v:,.1f}x".replace(".", ",")


def day_from_step(step) -> str:
    try:
        step_int = int(step)
    except (TypeError, ValueError):
        return "-"
    day = (step_int - 1) // 24 + 1
    hour = (step_int - 1) % 24
    return f"Hari ke-{day}, {hour:02d}:00"


PHASE1_FINDINGS = [
    dict(icon="🔒", title="Datanya bersih dan rapi",
         text="Tidak ada transaksi kembar, tidak ada angka minus yang aneh, dan tidak ada transaksi ke rekening sendiri. Data siap dianalisis."),
    dict(icon="🆔", title="Penomoran rekening konsisten",
         text="Pengirim selalu nasabah biasa; penerima bisa nasabah atau toko. Toko tidak pernah jadi pengirim: polanya rapi."),
    dict(icon="📅", title="Rentang waktu hampir penuh",
         text="Data mencakup 743 dari 744 jam. Yang satu itu memang batas akhir simulasi, bukan data yang hilang."),
    dict(icon="🏪", title="Saldo toko selalu nol",
         text="Ini bawaan simulator, bukan data rusak. Artinya jumlah pembayaran = jumlah transaksi yang masuk ke toko."),
    dict(icon="⚖️", title="Saldo penerima sering tak cocok: dan itu petunjuk",
         text="Di 66% transaksi, saldo penerima tidak sesuai hitungan. Sekitar separuh penipuan ada di kelompok ini, jadi ini kami jadikan petunjuk penting."),
    dict(icon="🔍", title="Cuma 2 transaksi ganjil di sisi pengirim",
         text="Dua transaksi yang saldonya malah naik setelah mengirim uang: terlalu sedikit untuk berpengaruh, jadi diabaikan."),
    dict(icon="📥", title="Saldo penerima turun jarang berarti penipuan",
         text="Ada 44 ribu transaksi yang saldonya turun setelah menerima uang, tapi hampir semua normal. Ini ciri simulator, bukan tanda penipuan."),
    dict(icon="🎯", title="Penipuan cuma di dua jenis transaksi",
         text="Penipuan HANYA muncul saat menarik tunai dan transfer. Tidak pernah di setor tunai, pembayaran, atau debit. Ini mempersempit pencarian kami."),
    dict(icon="🛡️", title="Toko tidak pernah jadi korban",
         text="Semua transaksi menuju toko aman. Penipuan hanya terjadi antar sesama nasabah."),
    dict(icon="💧", title="Menguras saldo habis = tanda bahaya besar",
         text="Transaksi yang menyedot saldo pengirim sampai nol hampir 140× lebih mungkin penipuan. Ini salah satu petunjuk terkuat kami."),
    dict(icon="📉", title="Penipuan sangat langka",
         text="Dari 6,36 juta transaksi, hanya sekitar 8 ribu (0,13%) yang penipuan. Mencari mereka seperti mencari jarum di tumpukan jerami."),
    dict(icon="🧹", title="16 transaksi kosong dibuang saat pembersihan",
         text="Ada 16 transaksi bernilai nol rupiah: bukan aktivitas nyata, jadi dihapus. Data akhir jadi 6.362.604 baris."),
]

RECOMMENDATIONS = [
    dict(
        id="rec-seg0-queue", priority="Tinggi", category="Segmentasi",
        title="Buat antrean pemantauan khusus untuk transaksi bernilai eksepsional",
        description=(
            "Segmen 0 hanya 0,03% dari seluruh transaksi dan 0% berlabel fraud secara historis, tapi "
            "79% masuk kategori high-risk dengan rata-rata skor 4,66 dari 6: jauh di atas segmen lain. "
            "Kalau hanya mengandalkan label fraud historis, kelompok ini akan terlewat sepenuhnya."
        ),
        evidence="Segmen 0: Transfer Bernilai Sangat Tinggi: 1.648 transaksi, 79,13% high-risk, 0 fraud historis.",
        related_segment=0, related_anomaly_type=None, related_rule_group=None,
    ),
    dict(
        id="rec-hdbscan-escalate", priority="Tinggi", category="Deteksi Anomali",
        title="Jadikan penanda struktural (HDBSCAN) sebagai pemicu eskalasi otomatis",
        description=(
            "872 transaksi tertandai oleh metode struktural (BIRCH+HDBSCAN) namun TIDAK tertandai oleh "
            "metode berbasis nominal (IQR/Z-Score/Isolation Forest). Kalau metode ini tidak dijalankan "
            "terpisah, ratusan transaksi berisiko akan lolos tanpa terdeteksi sama sekali."
        ),
        evidence="Kajian tumpang-tindih metode: 3.923 transaksi ditandai HDBSCAN, hanya 3.051 beririsan dengan IQR.",
        related_segment=None, related_anomaly_type="Klaster Menyimpang (Outlier)", related_rule_group=None,
    ),
    dict(
        id="rec-fraud-rules-autoblock", priority="Tinggi", category="Pola & Asosiasi",
        title="Jadikan kombinasi pola fraud sebagai aturan pemblokiran/review otomatis",
        description=(
            "Beberapa kombinasi atribut (mis. saldo pengirim terkuras total + ketidaksesuaian saldo sangat "
            "rendah) berkonfidensi 100% menuju fraud terkonfirmasi dengan lift di atas 700x. Pola sekuat ini "
            "terlalu berharga untuk hanya jadi laporan pasif."
        ),
        evidence="Pola teratas: saldo pengirim terkuras + ketidaksesuaian saldo sangat rendah → fraud (confidence 100%, lift 776x).",
        related_segment=None, related_anomaly_type=None, related_rule_group=RULE_GROUP_FRAUD,
    ),
    dict(
        id="rec-medium-risk-review", priority="Tinggi", category="Deteksi Anomali",
        title="Tinjau ulang transaksi level 'Sedang', jangan hanya fokus ke 'Kritis'",
        description=(
            "Secara berlawanan dengan intuisi, transaksi berskor risiko 2 ('Sedang') justru punya konsentrasi "
            "fraud lebih tinggi (44,3%) dibanding transaksi berskor 6 ('Kritis', 20,7%). Kalau prioritas "
            "investigasi hanya mengikuti urutan skor, kelompok Sedang berisiko diabaikan padahal justru paling padat fraud-nya."
        ),
        evidence="fraud_by_score: skor 2 (Sedang) = 44,32% fraud rate vs skor 6 (Kritis) = 20,71% fraud rate.",
        related_segment=None, related_anomaly_type=None, related_rule_group=None,
    ),
    dict(
        id="rec-debit-monitor", priority="Sedang", category="Pola & Asosiasi",
        title="Tambahkan aturan pemantauan khusus untuk transaksi jenis Debit",
        description=(
            "Transaksi Debit secara konsisten berasosiasi dengan nominal sangat rendah dan ketidaksesuaian "
            "saldo tertentu pada beberapa pola sekaligus (confidence 83-91%). Pola yang konsisten ini bisa "
            "dijadikan aturan bisnis tambahan di luar model machine learning utama."
        ),
        evidence="2 pola independen dgn confidence >80% melibatkan jenis transaksi Debit.",
        related_segment=None, related_anomaly_type=None, related_rule_group=RULE_GROUP_GENERAL,
    ),
    dict(
        id="rec-liquidity-segments", priority="Sedang", category="Segmentasi",
        title="Pisahkan kebijakan segmen likuiditas dari kebijakan anti-fraud",
        description=(
            "Segmen 2 dan 3 (total 7,6% populasi) didominasi perilaku setor tunai bersaldo sangat tinggi. "
            "Tingkat fraud-nya mendekati rata-rata populasi, sehingga lebih tepat ditangani sebagai isu "
            "pemantauan likuiditas/kepatuhan dibanding target utama investigasi fraud."
        ),
        evidence="Segmen 2 & 3: fraud rate 0,26% dan 0,11%, mendekati baseline 0,13%.",
        related_segment=2, related_anomaly_type=None, related_rule_group=RULE_GROUP_SEGMENT,
    ),
    dict(
        id="rec-balance-mismatch-dq", priority="Sedang", category="Kualitas Data",
        title="Telusuri akar penyebab 'Ketidaksesuaian Saldo' sebagai isu kualitas data",
        description=(
            "22,6% dari seluruh transaksi tergolong 'Ketidaksesuaian Saldo': proporsi yang cukup besar untuk "
            "diasumsikan seluruhnya fraud. Sebagian besar kemungkinan adalah isu pencatatan/timing sistem, "
            "namun proporsi sebesar ini tetap layak ditelusuri akar penyebabnya."
        ),
        evidence="anomaly_type: Ketidaksesuaian Saldo = 1.439.370 transaksi (22,62% dari populasi).",
        related_segment=None, related_anomaly_type="Ketidaksesuaian Saldo", related_rule_group=None,
    ),
    dict(
        id="rec-rare-legit", priority="Rendah", category="Kualitas Data",
        title="Dokumentasikan pola 'Transaksi Sah yang Jarang Terjadi' sebagai pengecualian resmi",
        description=(
            "Hanya segelintir transaksi masuk kategori ini: kombinasi anomali yang jarang namun terverifikasi "
            "bukan fraud. Mendokumentasikannya sebagai pengecualian resmi mencegah tim investigasi mengulang "
            "analisis yang sama di masa depan."
        ),
        evidence="investigation_category: Transaksi Sah yang Jarang Terjadi = hanya 3 transaksi dari 6,3 juta.",
        related_segment=None, related_anomaly_type=None, related_rule_group=None,
    ),
    dict(
        id="rec-rule-transfer-drain-chain",
        priority="Tinggi", category="Pola & Asosiasi",
        title="Pantau rangkaian TRANSFER lalu CASH_OUT yang menguras saldo",
        description=(
            "Pola menunjukkan transaksi TRANSFER kerap diikuti pengurasan saldo pengirim, dan kombinasi "
            "'saldo terkuras + Segmen 1' berkonfidensi 82,7% menuju fraud. Ini menyerupai pola klasik "
            "pemindahan dana korban lalu pencairan cepat. Menjadikannya aturan pemantauan rantai (bukan per "
            "transaksi) bisa menangkap fraud lebih dini, sebelum dana benar-benar keluar."
        ),
        evidence="Pola: Segmen 1 + saldo pengirim terkuras -> fraud (confidence 82,7%, lift 642x).",
        related_segment=1, related_anomaly_type=None, related_rule_group="Pola Fraud",
    ),
    dict(
        id="rec-rule-outlier-confirm",
        priority="Tinggi", category="Pola & Asosiasi",
        title="Perlakukan pola berpenanda outlier struktural sebagai sinyal prioritas",
        description=(
            "Aturan yang memuat penanda outlier struktural (dari clustering) plus ketidaksesuaian saldo "
            "tinggi menuju fraud dengan konfidensi sangat tinggi. Karena sinyal ini berasal dari metode yang "
            "berbeda (clustering) namun menyimpulkan hal yang sama, kesepakatan lintas-metode ini membuat "
            "polanya sangat layak dipercaya dan dijadikan pemicu review otomatis."
        ),
        evidence="Pola: outlier struktural + ketidaksesuaian saldo penerima tinggi -> fraud (confidence 73,3%, lift 569x).",
        related_segment=None, related_anomaly_type=None, related_rule_group="Pola Outlier",
    ),
    dict(
        id="rec-rule-payment-safe-whitelist",
        priority="Sedang", category="Pola & Asosiasi",
        title="Manfaatkan pola PAYMENT-ke-merchant yang bersih untuk mengurangi beban review",
        description=(
            "Beberapa pola menunjukkan transaksi PAYMENT ke merchant hampir selalu jatuh ke segmen yang "
            "sepenuhnya bebas fraud, dengan konfidensi tinggi. Alih-alih hanya mengejar fraud, pola 'aman' "
            "sekuat ini bisa dipakai sebagai daftar putih (whitelist) untuk melewati review manual, sehingga "
            "tim bisa memusatkan tenaga ke transaksi yang benar-benar berisiko."
        ),
        evidence="Pola: Segmen 4 -> PAYMENT ke merchant + saldo awal sangat rendah (confidence 82,7%, lift 5,67x).",
        related_segment=4, related_anomaly_type=None, related_rule_group="Pola Segmen",
    ),
    dict(
        id="rec-rule-refresh-cadence",
        priority="Sedang", category="Pola & Asosiasi",
        title="Segarkan aturan asosiasi secara berkala mengikuti perubahan perilaku",
        description=(
            "Pola fraud yang ditemukan hari ini mencerminkan perilaku pada periode data ini. Penipu berganti "
            "taktik, sehingga aturan yang kuat sekarang bisa melemah seiring waktu. Menjadwalkan pelatihan "
            "ulang aturan asosiasi secara berkala menjaga agar daftar pola tetap relevan dan tidak "
            "mengandalkan pola usang."
        ),
        evidence="Total pola tersaring cukup banyak; kekuatan tiap pola bergantung pada periode data saat penambangan.",
        related_segment=None, related_anomaly_type=None, related_rule_group=None,
    ),
    dict(
        id="rec-combine-score-and-rules",
        priority="Tinggi", category="Deteksi Anomali",
        title="Gabungkan skor risiko dengan pencocokan pola untuk prioritas akhir",
        description=(
            "Skor risiko menyoroti anomali secara umum, sementara aturan asosiasi menunjuk kombinasi spesifik "
            "yang terbukti menuju fraud. Menggabungkan keduanya - misalnya menaikkan prioritas transaksi yang "
            "berskor tinggi DAN cocok pola fraud - menghasilkan antrean investigasi yang jauh lebih tajam "
            "daripada memakai salah satunya saja."
        ),
        evidence="Antrean high-risk memekatkan fraud 24x; pola teratas berkonfidensi hingga 100% (lift 776x).",
        related_segment=None, related_anomaly_type=None, related_rule_group="Pola Fraud",
    ),
    dict(
        id="rec-focus-segment1-capacity",
        priority="Tinggi", category="Segmentasi",
        title="Alokasikan kapasitas investigasi terbesar ke Segmen 1",
        description=(
            "Segmen 1 menampung mayoritas fraud dan seluruh transaksi berkategori Kritis. Alih-alih menyebar "
            "tenaga merata ke semua segmen, memusatkan kapasitas review ke Segmen 1 akan memberi hasil "
            "tangkapan fraud tertinggi per jam kerja investigator."
        ),
        evidence="Segmen 1: menampung bagian terbesar fraud dan 100% transaksi kategori Kritis.",
        related_segment=1, related_anomaly_type=None, related_rule_group=None,
    ),
    dict(
        id="rec-monitor-drift-metrics",
        priority="Rendah", category="Kualitas Data",
        title="Pantau pergeseran proporsi anomali sebagai indikator dini",
        description=(
            "Proporsi tiap jenis anomali dan ukuran tiap segmen relatif stabil pada periode ini. Perubahan "
            "mendadak pada proporsi tersebut - misalnya lonjakan tiba-tiba kategori tertentu - bisa menjadi "
            "sinyal dini munculnya modus baru, dan layak dipantau sebagai metrik rutin."
        ),
        evidence="Distribusi anomali & ukuran segmen konsisten pada periode data; perubahan tajam patut diselidiki.",
        related_segment=None, related_anomaly_type=None, related_rule_group=None,
    ),
]
