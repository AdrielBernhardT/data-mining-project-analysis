from __future__ import annotations

import dash
from dash import html, dcc, Input, Output, callback, dash_table

import config as cfg
from theme import COLORS
from app import BACKEND
from data_backend.base import Filters
from components.filter_bar import make_filter_bar, read_filters, filter_summary_text, page_shell, sidebar_toggle_callback
from components.cards import kpi_row, section_header, anomaly_method_card, info_banner, empty_state
import components.charts as ch

dash.register_page(__name__, path="/anomali", name="Aktivitas Tidak Wajar", title="Aktivitas Tidak Wajar")

PAGE = "anomali"

_hero = html.Div([
    html.Div("ANOMALY DETECTION", className="page-hero-eyebrow"),
    html.H1("Aktivitas Tidak Wajar"),
    html.P("Lima metode independen digabung jadi skor risiko 0-6. Skor tinggi = prioritas ditinjau, "
           "bukan vonis fraud. Tiap transaksi ditandai punya alasan yang bisa ditelusuri."),
], className="page-hero")

layout = page_shell(PAGE, hero=_hero, filter_bar=make_filter_bar(
    PAGE, jenis_tujuan=True, status_kuras=True, segmen=True, jenis=True, risk_level=True,
    anomaly_type=True, investigation_category=True, search=True,
    search_placeholder="Cari ID transaksi atau kata kunci (mis. 'hdbscan', 'saldo')"), content=[

    html.Div(id=f"{PAGE}-kpi-container"),

    section_header("Metode Mana yang Menemukan Anomali",
                   "Tiap metode melihat sudut berbeda: itu sebabnya dipakai lima sekaligus, bukan satu."),
    html.Div([
        html.Div([
            html.Div("Jumlah transaksi ditandai per metode", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-method-bar", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Tumpang tindih antar metode", className="chart-card-title"),
            html.Div("Sel gelap = dua metode sering menandai transaksi sama.", className="chart-card-note"),
            dcc.Graph(id=f"{PAGE}-overlap-heatmap", config={"displayModeBar": False}),
        ], className="chart-card"),
    ], className="grid-2-equal"),

    section_header("Skor Menengah Justru Padat Fraud",
                   "Batang = jumlah transaksi (skala log), garis merah = tingkat fraud per skor."),
    html.Div([dcc.Graph(id=f"{PAGE}-score-chart", config={"displayModeBar": False})], className="chart-card"),
    html.Div(id=f"{PAGE}-score-callout"),

    section_header("Jenis Anomali & Kategori Investigasi"),
    html.Div([
        html.Div([
            html.Div("Jenis anomali", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-type-bar", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Kategori investigasi disarankan", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-investigation-bar", config={"displayModeBar": False}),
        ], className="chart-card"),
    ], className="grid-2-equal"),

    section_header("Rincian 5 Metode", "Fitur input & bobot tiap metode ke skor akhir."),
    html.Div([anomaly_method_card(m) for m in cfg.ANOMALY_METHODS], className="method-grid"),

    section_header("Transaksi Ditandai & Alasannya",
                   "Kolom 'Alasan Ditandai' menjelaskan metode mana yang menandai tiap transaksi: inilah justifikasi kenapa ia dianggap anomali."),
    html.Div(id=f"{PAGE}-tx-table-wrap"),
])

sidebar_toggle_callback(PAGE)


@callback(
    Output(f"{PAGE}-kpi-container", "children"),
    Output(f"{PAGE}-method-bar", "figure"),
    Output(f"{PAGE}-overlap-heatmap", "figure"),
    Output(f"{PAGE}-score-chart", "figure"),
    Output(f"{PAGE}-score-callout", "children"),
    Output(f"{PAGE}-type-bar", "figure"),
    Output(f"{PAGE}-investigation-bar", "figure"),
    Output(f"{PAGE}-tx-table-wrap", "children"),
    Output(f"{PAGE}-filter-summary", "children"),
    Input(f"{PAGE}-filter-jenis-tujuan", "value"),
    Input(f"{PAGE}-filter-status-kuras", "value"),
    Input(f"{PAGE}-filter-segmen", "value"),
    Input(f"{PAGE}-filter-jenis", "value"),
    Input(f"{PAGE}-filter-risk", "value"),
    Input(f"{PAGE}-filter-anomaly", "value"),
    Input(f"{PAGE}-filter-investigation", "value"),
    Input(f"{PAGE}-filter-search", "value"),
)
def _update(jenis_tujuan, status_kuras, segmen, jenis, risk, anomaly, investigation, search):
    f = read_filters(PAGE, jenis_tujuan=jenis_tujuan, status_kuras=status_kuras, segmen=segmen, jenis=jenis, risk=risk,
                     anomaly=anomaly, investigation=investigation, search=search)
    kpi = BACKEND.get_kpi(f)
    overlap = BACKEND.get_method_overlap(f)
    by_score = BACKEND.get_fraud_by_score(f)
    type_rows = BACKEND.get_anomaly_type_summary(f)
    inv_rows = BACKEND.get_investigation_summary(f)
    total_all = BACKEND.count(Filters())

    kpis = kpi_row([
        dict(label="Transaksi (filter aktif)", value=cfg.format_int(kpi["total_transaksi"]), icon="📄", tone="brand"),
        dict(label="Antrean High-Risk", value=cfg.format_int(kpi["total_high_risk"]), icon="🚨", tone="warning",
             sublabel=cfg.format_pct(kpi["high_risk_rate"], 2) + " dari filter"),
        dict(label="Kritis", value=cfg.format_int(kpi["total_kritis"]), icon="🔴", tone="danger"),
        dict(label="Fraud Enrichment", value=(cfg.format_multiplier(kpi["fraud_enrichment"]) if kpi["fraud_enrichment"] else "-"),
             icon="🎯", tone="success", sublabel="vs baseline populasi"),
    ])

    fig_method = ch.method_contribution_bar(overlap)
    fig_overlap = ch.method_overlap_heatmap(overlap)
    fig_score = ch.fraud_by_score_chart(by_score)

    score2 = next((r for r in by_score if r["risk_score"] == 2), None)
    score6 = next((r for r in by_score if r["risk_score"] == 6), None)
    if score2 and score6 and score2["transactions"] and score6["transactions"]:
        callout = info_banner(
            f"Transaksi skor 2 ('Sedang') punya tingkat fraud {cfg.format_pct(score2['fraud_rate'], 2)}: lebih tinggi "
            f"dari skor 6 ('Kritis', {cfg.format_pct(score6['fraud_rate'], 2)}). Jangan urut prioritas murni dari skor tertinggi.",
            icon="⚡", tone="warning",
        )
    else:
        callout = None

    fig_type = ch.category_bar(type_rows, "anomaly_type")
    fig_inv = ch.category_bar(inv_rows, "investigation_category", color=COLORS["info"])

    rows, total_match = BACKEND.search_transactions(f, sort_col="risk_score", sort_dir="desc", page=1, page_size=25)
    table = _build_table(rows) if rows else empty_state("Tidak ada transaksi yang cocok dengan kombinasi filter ini.")
    summary = filter_summary_text(f, total_match, total_all)

    return kpis, fig_method, fig_overlap, fig_score, callout, fig_type, fig_inv, table, summary


def _build_table(rows):
    data = [{
        "ID Transaksi": r["transaction_id"],
        "Jenis": cfg.humanize_transaction_type(r["transaction_type"]),
        "Segmen": int(r["cluster_kmeans"]),
        "Skor": r["risk_score"],
        "Level": r["risk_level"],
        "Jenis Anomali": r["anomaly_type"],
        "Alasan Ditandai": r["anomaly_reason"],
        "Fraud?": "Ya" if r["isFraud"] else "Tidak",
    } for r in rows]
    return html.Div(dash_table.DataTable(
        data=data,
        columns=[{"name": c, "id": c} for c in data[0].keys()],
        page_size=25, sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "Inter, sans-serif", "fontSize": "12.5px", "padding": "9px 11px",
                    "textAlign": "left", "whiteSpace": "normal", "height": "auto", "maxWidth": "300px"},
        style_cell_conditional=[
            {"if": {"column_id": "Alasan Ditandai"}, "minWidth": "220px", "maxWidth": "360px", "fontWeight": "500"},
        ],
        style_header={"backgroundColor": "#122A52", "color": "white", "fontWeight": "600", "textTransform": "uppercase", "fontSize": "10.5px"},
        style_data_conditional=[
            {"if": {"filter_query": '{Level} = "Kritis"'}, "backgroundColor": "#FBEAE8"},
            {"if": {"filter_query": '{Fraud?} = "Ya"'}, "borderLeft": "3px solid #C1483F"},
            {"if": {"column_id": "Alasan Ditandai"}, "backgroundColor": "#F7F8FC"},
        ],
    ), className="paysim-table")
