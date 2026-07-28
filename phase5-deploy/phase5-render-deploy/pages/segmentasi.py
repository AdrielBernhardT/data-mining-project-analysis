from __future__ import annotations

import dash
from dash import html, dcc, Input, Output, State, callback, ALL, ctx, dash_table

import config as cfg
from app import BACKEND
from components.filter_bar import make_filter_bar, read_filters, page_shell, sidebar_toggle_callback
from components.cards import kpi_row, section_header, segment_card, info_banner, empty_state
import components.charts as ch

dash.register_page(__name__, path="/segmentasi", name="Segmentasi Nasabah", title="Segmentasi Nasabah")

PAGE = "segmentasi"

_hero = html.Div([
    html.Div("CUSTOMER SEGMENTATION", className="page-hero-eyebrow"),
    html.H1("Segmentasi Nasabah"),
    html.P("Kami mengelompokkan seluruh transaksi ke dalam 5 kelompok berdasarkan kemiripannya. "
           "Klik salah satu kartu kelompok di bawah untuk menyorotnya di semua grafik."),
], className="page-hero")

layout = page_shell(PAGE, hero=_hero, filter_bar=make_filter_bar(PAGE, jenis_tujuan=True, segmen=True, jenis=True), content=[

    html.Div(id=f"{PAGE}-kpi-container"),

    section_header("Peta Sebaran Kelompok",
                   "Tiap titik adalah satu transaksi. Warna yang sama = kelompok yang sama. "
                   "Pilih 3D lalu tarik dengan mouse kalau ingin memutarnya dan melihat dari berbagai sudut. "
                   "Grafik kanan menunjukkan seberapa besar tiap kelompok."),
    html.Div([
        html.Div([
            html.Div("Sebaran transaksi tiap kelompok", className="chart-card-title"),
            html.Div([
                html.Div([
                    html.Label("Metode", className="mini-control-label"),
                    dcc.Dropdown(id=f"{PAGE}-proj-method",
                                 options=[{"label": "UMAP", "value": "umap"}, {"label": "t-SNE", "value": "tsne"}],
                                 value="umap", clearable=False, className="mini-dropdown"),
                ], className="mini-control"),
                html.Div([
                    html.Label("Dimensi", className="mini-control-label"),
                    dcc.RadioItems(id=f"{PAGE}-proj-dim",
                                   options=[{"label": "2D", "value": 2}, {"label": "3D", "value": 3}],
                                   value=2, inline=True, className="mini-radio"),
                ], className="mini-control"),
            ], className="proj-controls"),
            dcc.Graph(id=f"{PAGE}-scatter", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Ukuran tiap kelompok", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-donut", config={"displayModeBar": False}),
        ], className="chart-card"),
    ], className="grid-2-equal"),

    section_header("Kelompok Nasabah", "Klik salah satu untuk menyorotnya di semua grafik di halaman ini."),
    html.Div(id=f"{PAGE}-segment-cards", className="segment-grid"),

    section_header("Membandingkan Karakter Tiap Kelompok",
                   "Dua cara melihat apa yang membedakan kelompok-kelompok ini."),
    html.Div([
        html.Div([
            html.Div("Perbandingan karakter antar kelompok", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-radar", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Seberapa berisiko tiap kelompok", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-risk-bar", config={"displayModeBar": False}),
        ], className="chart-card"),
    ], className="grid-2-equal"),

    section_header("Melihat Risiko Tiap Kelompok Lebih Dekat",
                   "Grafik kiri fokus ke penipuan dan risiko tinggi (angkanya kecil, jadi dipisah agar terlihat). "
                   "Grafik kanan menunjukkan berapa banyak transaksi menuju toko di tiap kelompok."),
    html.Div([
        html.Div([
            html.Div("Tingkat penipuan & risiko tinggi tiap kelompok", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-risk-chart", config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Berapa banyak transaksi ke toko di tiap kelompok", className="chart-card-title"),
            dcc.Graph(id=f"{PAGE}-merchant-chart", config={"displayModeBar": False}),
        ], className="chart-card"),
    ], className="grid-2-equal"),
    html.Div(id=f"{PAGE}-profile-table-wrap"),

    dcc.Store(id=f"{PAGE}-selected-segment", data=None),
])

sidebar_toggle_callback(PAGE)


@callback(
    Output(f"{PAGE}-kpi-container", "children"),
    Output(f"{PAGE}-scatter", "figure"),
    Output(f"{PAGE}-donut", "figure"),
    Output(f"{PAGE}-segment-cards", "children"),
    Output(f"{PAGE}-radar", "figure"),
    Output(f"{PAGE}-risk-bar", "figure"),
    Output(f"{PAGE}-risk-chart", "figure"),
    Output(f"{PAGE}-merchant-chart", "figure"),
    Output(f"{PAGE}-profile-table-wrap", "children"),
    Input(f"{PAGE}-filter-jenis-tujuan", "value"),
    Input(f"{PAGE}-filter-segmen", "value"),
    Input(f"{PAGE}-filter-jenis", "value"),
    Input(f"{PAGE}-selected-segment", "data"),
    Input(f"{PAGE}-proj-method", "value"),
    Input(f"{PAGE}-proj-dim", "value"),
)
def _update(jenis_tujuan, segmen, jenis, selected, proj_method, proj_dim):
    f = read_filters(PAGE, jenis_tujuan=jenis_tujuan, segmen=segmen, jenis=jenis)
    seg_rows = BACKEND.get_segment_summary(f)
    kpi = BACKEND.get_kpi(f)
    proj_rows = BACKEND.get_segment_projection(f, method=proj_method, dim=proj_dim)
    profile_rows = BACKEND.get_cluster_profile(f)

    if segmen:
        seg_list = segmen if isinstance(segmen, list) else [segmen]
        if len(seg_list) == 1:
            terpilih = cfg.SEGMENT_NAMES.get(int(seg_list[0]), f"Segmen {seg_list[0]}")
        else:
            terpilih = f"{len(seg_list)} segmen"
    elif selected is not None:
        terpilih = cfg.SEGMENT_NAMES.get(int(selected), f"Segmen {selected}")
    else:
        terpilih = "Semua"

    kpis = kpi_row([
        dict(label="Jumlah Segmen", value=str(len(seg_rows)), tone="brand"),
        dict(label="Segmen Terbesar", value=(f"{max(r['population_share'] for r in seg_rows)*100:.1f}%".replace(".", ",") if seg_rows else "-"),
             tone="default"),
        dict(label="Total Transaksi", value=cfg.format_int(kpi["total_transaksi"])),
        dict(label="Segmen Terpilih", value=terpilih, tone="success"),
    ])

    highlight = selected
    if segmen:
        seg_list = segmen if isinstance(segmen, list) else [segmen]
        if len(seg_list) == 1:
            highlight = int(seg_list[0])

    fig_scatter = ch.segment_projection_scatter(proj_rows, selected_segment=highlight)
    fig_donut = ch.segment_proportion_donut(seg_rows, selected_segment=highlight)

    cards = [segment_card(row, selected=(highlight is not None and int(row["cluster_kmeans"]) == int(highlight)))
             for row in seg_rows] if seg_rows else [html.Div("Tidak ada data untuk filter ini.")]

    fig_radar = ch.segment_radar(seg_rows, selected_segment=highlight)
    fig_risk = ch.segment_risk_bar(seg_rows, selected_segment=highlight)
    fig_risk_profile = ch.cluster_risk_chart(profile_rows, selected_segment=highlight)
    fig_merchant = ch.cluster_merchant_chart(profile_rows, selected_segment=highlight)
    profile_table = _build_profile_table(profile_rows)

    return kpis, fig_scatter, fig_donut, cards, fig_radar, fig_risk, fig_risk_profile, fig_merchant, profile_table


def _build_profile_table(rows):
    """Tabel profil ringkas tiap segmen (jenis dominan, fraud, high-risk, dsb)."""
    if not rows:
        return empty_state("Belum ada data profil segmen untuk filter ini.")
    data = [{
        "Segmen": f"{int(r['cluster_kmeans'])}: {cfg.SEGMENT_NAMES.get(int(r['cluster_kmeans']), '')}",
        "Transaksi": cfg.format_int(r["total"]),
        "Jenis Dominan": cfg.humanize_transaction_type(r["dominant_type"]) + f" ({r['dominant_type_share']*100:.0f}%)".replace(".", ","),
        "Fraud": cfg.format_pct(r["fraud_rate"], 3),
        "High-Risk": cfg.format_pct(r["high_risk_rate"], 2),
        "Ke Merchant": cfg.format_pct(r["merchant_share"], 1),
        "Saldo Terkuras": cfg.format_pct(r["drained_share"], 1),
    } for r in rows]
    return html.Div(dash_table.DataTable(
        data=data,
        columns=[{"name": c, "id": c} for c in data[0].keys()],
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "Inter, sans-serif", "fontSize": "12.5px", "padding": "10px 12px",
                    "textAlign": "left", "whiteSpace": "normal", "height": "auto"},
        style_header={"backgroundColor": "#122A52", "color": "white", "fontWeight": "600",
                      "textTransform": "uppercase", "fontSize": "10.5px"},
    ), className="paysim-table")


@callback(
    Output(f"{PAGE}-selected-segment", "data"),
    Input({"type": "segment-card", "index": ALL}, "n_clicks"),
    State(f"{PAGE}-selected-segment", "data"),
    prevent_initial_call=True,
)
def _toggle_segment(n_clicks_list, current):
    triggered = ctx.triggered_id
    if not triggered or not any(n_clicks_list):
        return current
    clicked_index = triggered["index"]
    return None if current == clicked_index else clicked_index
