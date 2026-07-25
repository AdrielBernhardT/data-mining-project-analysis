"""
components/filter_bar.py
==========================
Filter bar (slicer) yang konsisten di semua halaman - menjawab catatan dosen
"setiap page at least ada slicernya".

Dataset PaySim tidak punya atribut spasial maupun temporal yang bermakna
(sudah dicek ulang - lihat config.py), jadi filter di sini semuanya diturunkan
dari atribut yang BENAR-BENAR ADA di data: jenis tujuan transaksi (Merchant/
Nasabah, dari isDestMerchant), status saldo terkuras (dari origDrainedToZero),
segmen, jenis transaksi, level risiko, jenis anomali, kategori investigasi,
dan pencarian bebas.
"""
from __future__ import annotations

from dash import dcc, html

import config as cfg
from data_backend.base import Filters

SEGMENT_OPTIONS = [{"label": f"Segmen {i}: {cfg.SEGMENT_NAMES[i]}", "value": i} for i in sorted(cfg.SEGMENT_NAMES)]
JENIS_OPTIONS = [{"label": v, "value": k} for k, v in cfg.TRANSACTION_TYPE_LABELS.items()]
RISK_OPTIONS = [{"label": r, "value": r} for r in cfg.RISK_LEVELS]
DEST_TYPE_OPTIONS = [{"label": w, "value": w} for w in cfg.DEST_TYPE_LIST]
DRAIN_STATUS_OPTIONS = [{"label": w, "value": w} for w in cfg.DRAIN_STATUS_LIST]
ANOMALY_TYPE_OPTIONS = [{"label": a, "value": a} for a in cfg.ANOMALY_TYPE_LABELS]
INVESTIGATION_OPTIONS = [{"label": a, "value": a} for a in cfg.INVESTIGATION_CATEGORY_LABELS]

RULE_GROUP_OPTIONS = [{"label": g, "value": g} for g in cfg.RULE_GROUP_ORDER]
def _atoms_by_prefix(*prefixes, contains=None, exclude=None):
    out = []
    for k in cfg.ITEM_LABELS:
        if exclude and any(x in k for x in exclude):
            continue
        if prefixes and k.startswith(prefixes):
            out.append(k)
        elif contains and any(c in k for c in contains):
            out.append(k)
    return sorted(({"label": cfg.humanize_item(k), "value": k} for k in out), key=lambda o: o["label"])


RULE_ATTR_GROUPS = [
    ("jenis-transaksi", "Jenis Transaksi", _atoms_by_prefix("type_")),
    ("segmen-atom", "Segmen", _atoms_by_prefix("cluster_kmeans")),
    ("nominal", "Nominal Transaksi", _atoms_by_prefix("amount_")),
    ("saldo-awal", "Saldo Awal", _atoms_by_prefix("oldbalance")),
    ("selisih-saldo", "Selisih Saldo", _atoms_by_prefix("origError", "destError")),
    ("status-kuras-atom", "Status Kuras Saldo", _atoms_by_prefix("orig_drained")),
    ("tujuan-atom", "Jenis Tujuan", _atoms_by_prefix("dest_merchant")),
    ("outlier-atom", "Outlier Struktural", _atoms_by_prefix("hdbscan")),
    ("status-fraud", "Status Fraud", _atoms_by_prefix("isFraud")),
]

RULE_ATTRIBUTE_OPTIONS = sorted(
    [{"label": cfg.humanize_item(k), "value": k} for k in cfg.ITEM_LABELS],
    key=lambda o: o["label"],
)


def _dd(id_, options, placeholder, multi=True):
    return dcc.Dropdown(
        id=id_, options=options, multi=multi, placeholder=placeholder,
        className="paysim-dropdown", clearable=True, persistence=False,
    )


def make_filter_bar(page_id: str, *, jenis_tujuan=True, status_kuras=False, segmen=True, jenis=True,
                     risk_level=False, anomaly_type=False, investigation_category=False,
                     search=False, search_placeholder="Cari...",
                     rule_group=False, rule_attribute=False, rule_confidence=False, rule_lift=False) -> html.Div:
    controls = []
    if jenis_tujuan:
        controls.append(html.Div([
            html.Label("Tipe tujuan", className="filter-label"),
            _dd(f"{page_id}-filter-jenis-tujuan", DEST_TYPE_OPTIONS, "Semua tipe tujuan"),
        ], className="filter-control"))
    if status_kuras:
        controls.append(html.Div([
            html.Label("Status saldo", className="filter-label"),
            _dd(f"{page_id}-filter-status-kuras", DRAIN_STATUS_OPTIONS, "Semua status"),
        ], className="filter-control"))
    if segmen:
        controls.append(html.Div([
            html.Label("Segmen", className="filter-label"),
            _dd(f"{page_id}-filter-segmen", SEGMENT_OPTIONS, "Semua segmen"),
        ], className="filter-control"))
    if jenis:
        controls.append(html.Div([
            html.Label("Jenis transaksi", className="filter-label"),
            _dd(f"{page_id}-filter-jenis", JENIS_OPTIONS, "Semua jenis"),
        ], className="filter-control"))
    if risk_level:
        controls.append(html.Div([
            html.Label("Level risiko", className="filter-label"),
            _dd(f"{page_id}-filter-risk", RISK_OPTIONS, "Semua level"),
        ], className="filter-control"))
    if anomaly_type:
        controls.append(html.Div([
            html.Label("Jenis anomali", className="filter-label"),
            _dd(f"{page_id}-filter-anomaly", ANOMALY_TYPE_OPTIONS, "Semua jenis"),
        ], className="filter-control filter-control-wide"))
    if investigation_category:
        controls.append(html.Div([
            html.Label("Kategori investigasi", className="filter-label"),
            _dd(f"{page_id}-filter-investigation", INVESTIGATION_OPTIONS, "Semua kategori"),
        ], className="filter-control filter-control-wide"))
    if rule_group:
        controls.append(html.Div([
            html.Label("Kelompok pola", className="filter-label"),
            _dd(f"{page_id}-filter-rule-group", RULE_GROUP_OPTIONS, "Semua kelompok", multi=False),
        ], className="filter-control"))
    if rule_attribute:
        for slug, label, opts in RULE_ATTR_GROUPS:
            if not opts:
                continue
            controls.append(html.Div([
                html.Label(label, className="filter-label"),
                _dd(f"{page_id}-filter-attr-{slug}", opts, "Semua"),
            ], className="filter-control"))
    if rule_confidence:
        controls.append(html.Div([
            html.Label("Confidence minimal", className="filter-label"),
            dcc.Slider(id=f"{page_id}-filter-rule-confidence", min=0, max=100, step=5, value=0,
                       marks={0: "0%", 50: "50%", 100: "100%"},
                       tooltip={"placement": "bottom", "always_visible": False}),
        ], className="filter-control filter-control-wide"))
    if rule_lift:
        controls.append(html.Div([
            html.Label("Lift minimal", className="filter-label"),
            dcc.Slider(id=f"{page_id}-filter-rule-lift", min=0, max=50, step=1, value=0,
                       marks={0: "0", 10: "10x", 25: "25x", 50: "50x+"},
                       tooltip={"placement": "bottom", "always_visible": False}),
        ], className="filter-control filter-control-wide"))
    if search:
        controls.append(html.Div([
            html.Label("Cari", className="filter-label"),
            dcc.Input(id=f"{page_id}-filter-search", type="text", placeholder=search_placeholder,
                      className="paysim-input", debounce=True),
        ], className="filter-control"))

    controls.append(html.Div([
        html.Label("\u00A0", className="filter-label"),
        html.Button("Reset filter", id=f"{page_id}-filter-reset", className="btn-reset", n_clicks=0),
    ], className="filter-control filter-control-reset"))

    return html.Div([
        html.Div("🔎 Filter data di halaman ini", className="filter-bar-title"),
        html.Div(controls, className="filter-bar-controls"),
        html.Div(id=f"{page_id}-filter-summary", className="filter-summary"),
    ], className="filter-bar", id=f"{page_id}-filter-bar")


def page_shell(page_id: str, hero, filter_bar, content) -> html.Div:
    """Susun halaman jadi dua kolom: sidebar filter (kiri, sticky) + kolom konten
    (kanan) yang memuat hero lalu seluruh konten. Tidak mengubah ID/callback
    filter apa pun - hanya membungkus ulang posisinya."""
    if not isinstance(content, (list, tuple)):
        content = [content]

    sidebar = html.Aside([
        html.Div([
            html.Span("Filter", className="sidebar-title-text"),
            html.Button(
                "\u2630", id=f"{page_id}-sidebar-toggle", className="sidebar-toggle",
                n_clicks=0, title="Sembunyikan / tampilkan filter",
                **{"aria-label": "Sembunyikan atau tampilkan filter"},
            ),
        ], className="sidebar-header"),
        html.Div(filter_bar, id=f"{page_id}-sidebar-body", className="sidebar-body"),
    ], className="filter-sidebar", id=f"{page_id}-sidebar")

    main = html.Div([hero, *content], className="page-main")
    return html.Div([sidebar, main], className="page-with-sidebar page-fade-in")


def sidebar_toggle_callback(page_id: str):
    """Daftarkan callback collapse sidebar untuk sebuah halaman."""
    from dash import callback, Input, Output, State

    @callback(
        Output(f"{page_id}-sidebar", "className"),
        Input(f"{page_id}-sidebar-toggle", "n_clicks"),
        State(f"{page_id}-sidebar", "className"),
        prevent_initial_call=True,
    )
    def _toggle(n, current):
        base = "filter-sidebar"
        collapsed = current and "filter-sidebar-collapsed" in current
        return base if collapsed else base + " filter-sidebar-collapsed"

    return _toggle


def read_filters(page_id: str, jenis_tujuan=None, status_kuras=None, segmen=None, jenis=None, risk=None,
                  anomaly=None, investigation=None, search=None) -> Filters:
    """Bangun objek Filters dari nilai-nilai State/Input callback Dash."""
    return Filters(
        jenis_tujuan=jenis_tujuan or [], status_kuras=status_kuras or [],
        segmen=segmen or [], jenis_transaksi=jenis or [],
        risk_level=risk or [], anomaly_type=anomaly or [], investigation_category=investigation or [],
        search=search or "",
    )


def filter_summary_text(f: Filters, total_after: int, total_all: int) -> str:
    if f.is_empty():
        return f"Menampilkan semua {cfg.format_int(total_all)} transaksi (tidak ada filter aktif)."
    pct = (total_after / total_all * 100) if total_all else 0
    return (f"Menampilkan {cfg.format_int(total_after)} dari {cfg.format_int(total_all)} transaksi "
            f"({pct:.2f}%) sesuai filter aktif.".replace(".", ",", 1))
