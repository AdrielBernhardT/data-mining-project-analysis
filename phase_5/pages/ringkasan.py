from __future__ import annotations

import dash
from dash import html, dcc, Input, Output, callback

import config as cfg
from app import BACKEND
from data_backend.base import Filters
from components.filter_bar import make_filter_bar, read_filters, page_shell, sidebar_toggle_callback
from components.cards import kpi_row, section_header, info_banner
import components.charts as ch

dash.register_page(__name__, path="/", name="Ringkasan Eksekutif", title="Ringkasan Eksekutif")

PAGE = "ringkasan"

_hero = html.Div([
    html.Div("EXECUTIVE SUMMARY", className="page-hero-eyebrow"),
    html.H1("Ringkasan Deteksi Fraud"),
    html.P(
        "Menemukan penipuan itu seperti mencari jarum di tumpukan jerami: hanya sekitar 1 dari 800 "
        "transaksi yang menipu. Sistem ini menyaring 6,3 juta transaksi menjadi daftar pendek yang "
        "jauh lebih mungkin berisi penipuan, supaya tim bisa fokus memeriksanya. Gunakan filter di kiri untuk menelusuri."
    ),
], className="page-hero")

layout = page_shell(PAGE, hero=_hero, filter_bar=make_filter_bar(PAGE, jenis_tujuan=True, segmen=True, jenis=True), content=[

    html.Div(id=f"{PAGE}-kpi-container"),

    section_header("Bagaimana Sistem Menyaring Penipuan",
                   "Corong ini menunjukkan penyaringan bertahap: dari semua transaksi, mengecil sampai ke "
                   "penipuan yang berhasil masuk daftar prioritas untuk diperiksa."),
    html.Div([
        html.Div([
            html.Div("Perjalanan dari populasi ke fraud", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-fraud-funnel", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Antrean high-risk jauh lebih pekat fraud", className="chart-card-title"),
            html.Div("Bandingkan tingkat fraud di antrean vs rata-rata seluruh populasi.", className="chart-card-note"),
            dcc.Graph(id=f"{PAGE}-enrichment", config={"displayModeBar": False}),
            html.Div(id=f"{PAGE}-enrichment-caption", className="chart-card-note"),
        ], className="chart-card"),
    ], className="grid-2-equal"),

    section_header("Fraud Tidak Selalu di Skor Tertinggi",
                   "Batang = jumlah transaksi (skala log). Garis merah = tingkat fraud. Perhatikan skor menengah."),
    html.Div([
        dcc.Graph(id=f"{PAGE}-fraud-by-score", config={"displayModeBar": False}),
    ], className="chart-card"),

    section_header("Di Mana Risiko Terkonsentrasi"),
    html.Div([
        html.Div([
            html.Div("Populasi vs skor risiko per segmen", className="chart-card-title"),
            html.Div("Ukuran lingkaran = jumlah transaksi. Detail di tab Segmentasi.", className="chart-card-note"),
            dcc.Graph(id=f"{PAGE}-segment-landscape", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Tujuan transaksi: merchant vs nasabah", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-dest-type-bar", config={"displayModeBar": False}),
        ], className="chart-card"),
    ], className="grid-2-equal"),

    section_header("Apa yang Kami Pelajari dari Data di Awal",
                   "Sebelum menganalisis lebih jauh, kami memeriksa datanya dan menemukan hal-hal penting ini. "
                   "Semua analisis berikutnya dibangun dari temuan-temuan ini."),
    html.Div([
        html.Div([
            html.Div(fnd["icon"], className="finding-icon"),
            html.Div([
                html.Div(fnd["title"], className="finding-title"),
                html.Div(fnd["text"], className="finding-text"),
            ]),
        ], className="finding-card")
        for fnd in cfg.PHASE1_FINDINGS
    ], className="findings-grid"),

    section_header("Jelajahi Lebih Dalam"),
    html.Div(id=f"{PAGE}-nav-summary", className="grid-2-equal"),
])

sidebar_toggle_callback(PAGE)


@callback(
    Output(f"{PAGE}-kpi-container", "children"),
    Output(f"{PAGE}-fraud-funnel", "figure"),
    Output(f"{PAGE}-enrichment", "figure"),
    Output(f"{PAGE}-enrichment-caption", "children"),
    Output(f"{PAGE}-fraud-by-score", "figure"),
    Output(f"{PAGE}-segment-landscape", "figure"),
    Output(f"{PAGE}-dest-type-bar", "figure"),
    Output(f"{PAGE}-nav-summary", "children"),
    Input(f"{PAGE}-filter-jenis-tujuan", "value"),
    Input(f"{PAGE}-filter-segmen", "value"),
    Input(f"{PAGE}-filter-jenis", "value"),
)
def _update(jenis_tujuan, segmen, jenis):
    f = read_filters(PAGE, jenis_tujuan=jenis_tujuan, segmen=segmen, jenis=jenis)
    kpi = BACKEND.get_kpi(f)
    seg_rows = BACKEND.get_segment_summary(f)
    score_rows = BACKEND.get_fraud_by_score(f)
    dest_type_rows = BACKEND.get_dest_type_breakdown(f)

    kpis = kpi_row([
        dict(label="Total Transaksi", value=cfg.format_int(kpi["total_transaksi"]), icon="📄", tone="brand",
             sublabel="sesuai filter aktif"),
        dict(label="Fraud Terkonfirmasi", value=cfg.format_int(kpi["total_fraud"]), icon="🚩", tone="danger",
             sublabel=f"tingkat fraud {cfg.format_pct(kpi['fraud_rate'], 3)}"),
        dict(label="Antrean High-Risk", value=cfg.format_int(kpi["total_high_risk"]), icon="🔎", tone="warning",
             sublabel=f"{cfg.format_pct(kpi['high_risk_rate'], 2)} dari total"),
        dict(label="Fraud Enrichment", value=(cfg.format_multiplier(kpi["fraud_enrichment"]) if kpi["fraud_enrichment"] else "-"),
             icon="🎯", tone="success", sublabel="lebih pekat vs baseline"),
    ])

    fig_funnel = ch.fraud_funnel(kpi)
    fig_enrich = ch.fraud_enrichment_gauge(kpi)
    if kpi["total_high_risk"] and kpi["fraud_enrichment"]:
        cap = (f"Antrean high-risk {cfg.format_multiplier(kpi['fraud_enrichment'])} lebih pekat fraud "
               f"dibanding menyisir seluruh populasi.")
    else:
        cap = "Tidak ada transaksi high-risk pada filter ini."

    fig_score = ch.fraud_by_score_chart(score_rows)
    fig_landscape = ch.segment_landscape(seg_rows)
    fig_dest_type = ch.category_breakdown_bar(dest_type_rows, "jenis_tujuan")

    nav_info = [
        ("/segmentasi", "🧩 Segmentasi Nasabah", "5 segmen perilaku, dari transaksi eksepsional hingga populasi harian."),
        ("/pola", "🔗 Pola & Asosiasi", "Kombinasi atribut yang paling sering menuju fraud."),
        ("/anomali", "🚨 Aktivitas Tidak Wajar", "5 metode deteksi jadi satu skor risiko, divalidasi ke fraud."),
        ("/rekomendasi", "✅ Rekomendasi", "Tindakan konkret berbasis temuan."),
    ]
    nav_cards = [
        html.Div([
            dcc.Link(html.H4(title, className="rec-title"), href=path),
            html.P(desc, className="segment-text"),
            dcc.Link("Lihat detail →", href=path, className="chip"),
        ], className="chart-card")
        for path, title, desc in nav_info
    ]

    return kpis, fig_funnel, fig_enrich, cap, fig_score, fig_landscape, fig_dest_type, nav_cards
