from __future__ import annotations

import dash
from dash import html, dcc, Input, Output, callback

import config as cfg
from app import BACKEND
from data_backend.base import Filters
from components.filter_bar import make_filter_bar, page_shell, sidebar_toggle_callback
from components.cards import kpi_row, section_header, recommendation_card_compact, empty_state
import components.charts as ch

dash.register_page(__name__, path="/rekomendasi", name="Rekomendasi", title="Rekomendasi Bisnis")

PAGE = "rekomendasi"
PRIORITY_ALL = "Semua prioritas"
PRIORITY_CHOICES = [PRIORITY_ALL, "Tinggi", "Sedang", "Rendah"]

_hero = html.Div([
    html.Div("BUSINESS RECOMMENDATIONS", className="page-hero-eyebrow"),
    html.H1("Rekomendasi Tindak Lanjut"),
    html.P("Tindakan konkret, tiap butir terikat ke temuan nyata. Filter tipe tujuan di sidebar "
           "menghitung ulang relevansinya."),
], className="page-hero")

layout = page_shell(PAGE, hero=_hero, filter_bar=make_filter_bar(PAGE, jenis_tujuan=True, segmen=False, jenis=False), content=[

    html.Div([
        html.Span("Prioritas:", className="chip-row-label"),
        html.Div(id=f"{PAGE}-priority-chips", className="chip-row"),
    ], className="chip-row-wrap"),

    html.Div(id=f"{PAGE}-kpi-container"),

    section_header("Rekomendasi Berdasarkan Prioritas",
                   "Berapa banyak rekomendasi di tiap tingkat prioritas, dipilah per kategori. "
                   "Arahkan kursor ke batang untuk melihat daftar rekomendasinya. Mulai dari prioritas tinggi."),
    html.Div([dcc.Graph(id=f"{PAGE}-rec-map", config={"displayModeBar": False})], className="chart-card"),

    section_header("Daftar Rekomendasi", "Ringkas: klik 'Lihat detail' untuk uraian & relevansi terkini."),
    html.Div(id=f"{PAGE}-rec-cards", className="recommendation-grid"),

    dcc.Store(id=f"{PAGE}-active-priority", data=PRIORITY_ALL),
])

sidebar_toggle_callback(PAGE)


@callback(
    Output(f"{PAGE}-active-priority", "data"),
    Output(f"{PAGE}-priority-chips", "children"),
    Input({"type": f"{PAGE}-chip", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=False,
)
def _toggle_priority(_n_clicks):
    triggered = dash.ctx.triggered_id
    active = triggered["index"] if triggered else PRIORITY_ALL
    chips = [
        html.Button(p, id={"type": f"{PAGE}-chip", "index": p}, n_clicks=0,
                    className="chip" + (" chip-active" if p == active else ""))
        for p in PRIORITY_CHOICES
    ]
    return active, chips


@callback(
    Output(f"{PAGE}-kpi-container", "children"),
    Output(f"{PAGE}-rec-map", "figure"),
    Output(f"{PAGE}-rec-cards", "children"),
    Input(f"{PAGE}-active-priority", "data"),
    Input(f"{PAGE}-filter-jenis-tujuan", "value"),
)
def _update(active_priority, jenis_tujuan):
    recs = cfg.RECOMMENDATIONS
    if active_priority and active_priority != PRIORITY_ALL:
        recs = [r for r in recs if r["priority"] == active_priority]

    order = {"Tinggi": 0, "Sedang": 1, "Rendah": 2}
    recs = sorted(recs, key=lambda r: order.get(r["priority"], 9))

    n_tinggi = sum(1 for r in cfg.RECOMMENDATIONS if r["priority"] == "Tinggi")
    kpis = kpi_row([
        dict(label="Total Rekomendasi", value=str(len(cfg.RECOMMENDATIONS)), icon="✅", tone="brand"),
        dict(label="Prioritas Tinggi", value=str(n_tinggi), icon="🔴", tone="danger"),
        dict(label="Ditampilkan", value=str(len(recs)), icon="📋"),
    ])

    fig_map = ch.recommendation_map(recs)

    f_dasar = Filters(jenis_tujuan=jenis_tujuan or [])
    cards = [_card_with_relevance(r, f_dasar) for r in recs] if recs else [
        empty_state("Tidak ada rekomendasi pada prioritas ini.")
    ]
    return kpis, fig_map, cards


def _card_with_relevance(rec: dict, f_dasar: Filters) -> html.Div:
    """Kartu ringkas + baris relevansi hidup (dihitung ulang ikut filter)."""
    card = recommendation_card_compact(rec)
    relevance_text = None
    if rec.get("related_segment") is not None:
        seg_filter = Filters(jenis_tujuan=f_dasar.jenis_tujuan, segmen=[rec["related_segment"]])
        rows = BACKEND.get_segment_summary(seg_filter)
        if rows:
            r = rows[0]
            relevance_text = (
                f"📍 Irisan saat ini: Segmen {rec['related_segment']} = {cfg.format_int(r['transactions'])} transaksi, "
                f"{cfg.format_pct(r['high_risk_rate'], 2)} high-risk."
            )
    elif rec.get("related_anomaly_type"):
        rows = BACKEND.get_anomaly_type_summary(f_dasar)
        match = next((r for r in rows if r["anomaly_type"] == rec["related_anomaly_type"]), None)
        if match:
            relevance_text = (
                f"📍 Irisan saat ini: '{rec['related_anomaly_type']}' = {cfg.format_int(match['transactions'])} transaksi "
                f"({match['percentage']:.2f}".replace(".", ",") + "% dari filter)."
            )
    elif rec.get("related_rule_group"):
        n = len(BACKEND.get_rules(rule_group=rec["related_rule_group"]))
        relevance_text = f"📍 {n} pola kelompok '{rec['related_rule_group']}' (lihat tab Pola)."

    if relevance_text:
        card.children[3] = html.Div(relevance_text, className="rec-relevance-live")
    return card
