"""
pages/pola.py - Pola & Aturan Asosiasi (Association Rules)

Semua filter (kelompok, atribut, confidence, lift) ada di SIDEBAR untuk
konsistensi. Scatter confidence-vs-lift jadi visual utama (intuitif untuk
association rules). Teks dipangkas, rekomendasi ditambahkan.
"""
from __future__ import annotations

import dash
from dash import html, dcc, Input, Output, callback, dash_table

import config as cfg
from app import BACKEND
from components.filter_bar import make_filter_bar, page_shell, sidebar_toggle_callback
from components.cards import kpi_row, section_header, rule_card, ranked_rule_card, empty_state
import components.charts as ch

dash.register_page(__name__, path="/pola", name="Pola & Asosiasi", title="Pola & Aturan Asosiasi")

PAGE = "pola"

_hero = html.Div([
    html.Div("PATTERN MINING", className="page-hero-eyebrow"),
    html.H1("Pola & Aturan Asosiasi"),
    html.P("Kombinasi atribut yang sering muncul bersama, dibaca JIKA → MAKA. "
           "Pakai filter sidebar untuk menyaring berdasarkan atribut, confidence, atau lift."),
], className="page-hero")

layout = page_shell(PAGE, hero=_hero, filter_bar=make_filter_bar(
    PAGE, jenis_tujuan=False, segmen=False, jenis=False,
    rule_group=True, rule_attribute=True, rule_confidence=True, rule_lift=True,
    search=True, search_placeholder="Cari teks pola (JIKA/MAKA)..."), content=[

    html.Div(id=f"{PAGE}-kpi-container"),

    section_header("Seberapa Kuat Pola yang Ditemukan & Bagaimana Atribut Terhubung",
                   "Kiri: dari sekian pola, berapa yang benar-benar kuat: dan berapa yang mengarah ke penipuan (merah). "
                   "Kanan: bagaimana atribut saling terhubung; garis dan titik merah berujung ke penipuan. Arahkan kursor ke titik untuk melihat nama atributnya."),
    html.Div([
        html.Div([
            html.Div("Sebaran kekuatan pola", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-strength", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Jaringan antar-atribut", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-network", config={"displayModeBar": False}),
        ], className="chart-card"),
    ], className="grid-2-equal"),

    section_header("Pola Terkuat",
                   "10 pola terkuat yang cocok dengan pencarian & filtermu saat ini. "
                   "Ubah filter di kiri, dan daftar ini ikut berubah menampilkan 10 teratas yang baru."),
    html.Div(id=f"{PAGE}-count-banner", className="count-banner"),
    html.Div(id=f"{PAGE}-top-cards", className="rules-ranked-list"),

    section_header("Rekomendasi dari Pola Ini"),
    html.Div(id=f"{PAGE}-recommendations", className="grid-2-equal"),

    section_header("Semua Pola yang Cocok", "Bisa diurut & difilter lebih lanjut di tabel."),
    html.Div(id=f"{PAGE}-all-rules-table-wrap"),
])

sidebar_toggle_callback(PAGE)


def _rec_cards_for_group(active_group):
    """Rekomendasi yang relevan dengan kelompok pola aktif (atau semua yg terkait pola)."""
    recs = [r for r in cfg.RECOMMENDATIONS if r.get("related_rule_group")]
    if active_group:
        filtered = [r for r in recs if r["related_rule_group"] == active_group]
        recs = filtered or recs
    if not recs:
        return [empty_state("Tidak ada rekomendasi spesifik untuk filter ini.")]
    cards = []
    for r in recs[:4]:
        cards.append(html.Div([
            html.Div([
                html.Span(r["priority"], className=f"badge badge-{'danger' if r['priority']=='Tinggi' else 'warning' if r['priority']=='Sedang' else 'default'}"),
                html.Span(r["category"], className="chip"),
            ], className="rec-badges"),
            html.H4(r["title"], className="rec-title"),
            html.P(r["evidence"], className="segment-text rec-evidence"),
        ], className="chart-card rec-card"))
    return cards


@callback(
    Output(f"{PAGE}-kpi-container", "children"),
    Output(f"{PAGE}-strength", "figure"),
    Output(f"{PAGE}-network", "figure"),
    Output(f"{PAGE}-count-banner", "children"),
    Output(f"{PAGE}-top-cards", "children"),
    Output(f"{PAGE}-recommendations", "children"),
    Output(f"{PAGE}-all-rules-table-wrap", "children"),
    Input(f"{PAGE}-filter-rule-group", "value"),
    Input(f"{PAGE}-filter-attr-jenis-transaksi", "value"),
    Input(f"{PAGE}-filter-attr-segmen-atom", "value"),
    Input(f"{PAGE}-filter-attr-nominal", "value"),
    Input(f"{PAGE}-filter-attr-saldo-awal", "value"),
    Input(f"{PAGE}-filter-attr-selisih-saldo", "value"),
    Input(f"{PAGE}-filter-attr-status-kuras-atom", "value"),
    Input(f"{PAGE}-filter-attr-tujuan-atom", "value"),
    Input(f"{PAGE}-filter-attr-outlier-atom", "value"),
    Input(f"{PAGE}-filter-attr-status-fraud", "value"),
    Input(f"{PAGE}-filter-rule-confidence", "value"),
    Input(f"{PAGE}-filter-rule-lift", "value"),
    Input(f"{PAGE}-filter-search", "value"),
)
def _update(rule_group, a_type, a_seg, a_nom, a_saldo, a_selisih, a_kuras, a_tujuan, a_outlier, a_fraud,
            min_conf, min_lift, search):
    search = search or ""
    min_conf = (min_conf or 0) / 100.0
    min_lift = min_lift or 0
    attrs = []
    for group_val in (a_type, a_seg, a_nom, a_saldo, a_selisih, a_kuras, a_tujuan, a_outlier, a_fraud):
        if not group_val:
            continue
        if isinstance(group_val, list):
            attrs.extend(group_val)
        else:
            attrs.append(group_val)

    rules = BACKEND.get_rules(
        rule_group=rule_group or None, min_lift=min_lift, min_confidence=min_conf,
        attribute=attrs[0] if attrs else None, search=search,
    )
    for a in attrs[1:]:
        rules = [r for r in rules if a in (r.get("antecedents_str", "") + "," + r.get("consequents_str", ""))]

    all_rules_unfiltered = BACKEND.get_rules()

    kpis = kpi_row([
        dict(label="Total Pola", value=str(len(all_rules_unfiltered)), icon="🔗", tone="brand"),
        dict(label="Cocok Filter", value=str(len(rules)), icon="🔎", tone="default"),
        dict(label="Lift Tertinggi", value=cfg.format_multiplier(max((r["lift"] for r in rules), default=0)),
             icon="📈", tone="success"),
        dict(label="Confidence Tertinggi", value=cfg.format_pct(max((r["confidence"] for r in rules), default=0), 1),
             icon="🎯", tone="warning"),
    ])

    fig_strength = ch.rules_strength_summary(rules)
    fig_network = ch.rules_network(rules)

    top_cards = [ranked_rule_card(r, i + 1) for i, r in enumerate(rules[:10])] if rules else [empty_state("Tidak ada pola yang cocok dengan filter ini. Coba longgarkan confidence/lift atau ubah atribut.")]

    n_match = len(rules)
    n_shown = min(10, n_match)
    n_total = len(all_rules_unfiltered)
    is_filtered = (n_match != n_total)
    if n_match == 0:
        banner = None
    elif is_filtered:
        banner = html.Div([
            html.Span(f"Menampilkan {n_shown} teratas dari {n_match:,} pola", className="count-strong"),
            html.Span(f" yang cocok filter (total {n_total:,} pola).", className="count-soft"),
        ])
    else:
        banner = html.Div([
            html.Span(f"Menampilkan {n_shown} teratas dari {n_total:,} pola", className="count-strong"),
            html.Span(" (belum ada filter aktif).", className="count-soft"),
        ])

    rec_cards = _rec_cards_for_group(rule_group or None)

    table_rows = [
        {"Status": r.get("penting", ""), "Kelompok": r["rule_group"], "JIKA": r["when_text"],
         "MAKA": r["then_text"], "Coverage": r["coverage_fmt"], "Confidence": r["confidence_fmt"], "Lift": r["lift_fmt"]}
        for r in rules
    ]
    table = html.Div(dash_table.DataTable(
        data=table_rows,
        columns=[{"name": c, "id": c} for c in ["Status", "Kelompok", "JIKA", "MAKA", "Coverage", "Confidence", "Lift"]],
        page_size=15, sort_action="native", filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "Inter, sans-serif", "fontSize": "13px", "padding": "10px 12px",
                    "textAlign": "left", "whiteSpace": "normal", "height": "auto", "maxWidth": "320px"},
        style_header={"backgroundColor": "#122A52", "color": "white", "fontWeight": "600", "textTransform": "uppercase", "fontSize": "11px"},
        style_data_conditional=[{"if": {"filter_query": '{Status} = "Insight utama"'}, "backgroundColor": "#FBEDD4"}],
    ), className="paysim-table") if table_rows else empty_state("Tidak ada pola yang cocok.")

    return kpis, fig_strength, fig_network, banner, top_cards, rec_cards, table
