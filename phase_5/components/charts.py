"""
components/charts.py
======================
Semua grafik di dashboard dibuat lewat fungsi-fungsi di sini supaya HOVER,
WARNA, dan FONT konsisten di semua halaman (catatan dosen: "yang di graph ada
yang di hover ada yang ga"). Setiap fungsi memanggil theme.apply_theme() di
akhir.

Prinsip "semua segmen harus kelihatan" (catatan dosen):
grafik populasi (population_share_bar) memakai skala LOG + label angka selalu
tampil di ujung bar, supaya segmen yang sangat kecil (mis. Segmen 0 = 0,03%)
tetap terlihat & terbaca, bukan hilang jadi garis setipis rambut.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import config as cfg
from theme import COLORS, CATEGORICAL_SEQUENCE, RISK_COLOR_MAP, RISK_ORDER, segment_color, apply_theme, FONT_MONO


def _empty_figure(message: str = "Tidak ada data untuk filter/pencarian ini.") -> go.Figure:
    """Figure placeholder yang konsisten dgn tema, dipakai semua chart saat rows kosong
    (mis. hasil filter/pencarian tidak menemukan apa pun) - supaya tidak error/crash."""
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=13.5, color=COLORS["ink_faint"]),
                        xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    apply_theme(fig, legend=False, height=240)
    return fig


def _segment_label(cid) -> str:
    try:
        return f"Segmen {int(cid)}: {cfg.SEGMENT_NAMES[int(cid)]}"
    except (KeyError, ValueError, TypeError):
        return str(cid)


def _segment_label_short(cid) -> str:
    """Label ringkas untuk sumbu grafik (mis. 'Segmen 1') - nama panjang bikin
    label ketimpa/terkompres. Nama lengkap tetap tampil di hover."""
    try:
        return f"Segmen {int(cid)}"
    except (ValueError, TypeError):
        return str(cid)


def population_share_bar(rows: list[dict], selected_segment: int | None = None) -> go.Figure:
    if not rows:
        return _empty_figure()
    """Bar horizontal skala LOG + label persentase & jumlah SELALU tampil,
    supaya segmen sekecil apa pun tetap terlihat jelas (bukan cuma di hover)."""
    df = pd.DataFrame(rows).sort_values("cluster_kmeans")
    labels = [_segment_label(c) for c in df["cluster_kmeans"]]
    colors = [segment_color(c) for c in df["cluster_kmeans"]]
    if selected_segment is not None:
        colors = [c if int(seg) == int(selected_segment) else _fade(c) for c, seg in zip(colors, df["cluster_kmeans"])]

    text = [f"{cfg.format_int(t)} transaksi ({cfg.format_pct(s, 3)})"
            for t, s in zip(df["transactions"], df["population_share"])]

    fig = go.Figure(go.Bar(
        x=df["transactions"], y=labels, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=text, textposition="outside", cliponaxis=False,
        customdata=np.stack([df["population_share"] * 100, df["fraud_rate"] * 100, df["high_risk_rate"] * 100], axis=-1),
        hovertemplate=(
            "<b>%{y}</b><br>Jumlah transaksi: %{x:,.0f}<br>Pangsa populasi: %{customdata[0]:.3f}%"
            "<br>Tingkat fraud: %{customdata[1]:.3f}%<br>Tingkat high-risk: %{customdata[2]:.2f}%<extra></extra>"
        ),
    ))
    fig.update_xaxes(type="log", title="Jumlah transaksi (skala log: supaya segmen kecil tetap terlihat)")
    fig.update_yaxes(title=None, autorange="reversed")
    apply_theme(fig, legend=False, height=280)
    fig.update_layout(margin=dict(l=10, r=90, t=20, b=45))
    return fig


def _fade(hex_color: str, alpha: float = 0.35) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def segment_risk_bar(rows: list[dict], selected_segment: int | None = None) -> go.Figure:
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows).sort_values("cluster_kmeans")
    labels = [_segment_label_short(c) for c in df["cluster_kmeans"]]
    full = [_segment_label(c) for c in df["cluster_kmeans"]]
    colors = [segment_color(c) for c in df["cluster_kmeans"]]
    if selected_segment is not None:
        colors = [c if int(seg) == int(selected_segment) else _fade(c) for c, seg in zip(colors, df["cluster_kmeans"])]

    fig = go.Figure(go.Bar(
        x=labels, y=df["high_risk_rate"] * 100,
        marker=dict(color=colors),
        text=[f"{v:.1f}%".replace(".", ",") for v in df["high_risk_rate"] * 100],
        textposition="outside", cliponaxis=False,
        customdata=np.stack([df["avg_risk_score"], df["critical_count"], full], axis=-1),
        hovertemplate=(
            "<b>%{customdata[2]}</b><br>Tingkat transaksi high-risk: %{y:.2f}%<br>Rata-rata skor risiko: %{customdata[0]:.2f} / 6"
            "<br>Jumlah transaksi Kritis: %{customdata[1]:,.0f}<extra></extra>"
        ),
    ))
    fig.update_yaxes(title="% transaksi high-risk", automargin=True)
    fig.update_xaxes(title=None, tickangle=0, automargin=True)
    apply_theme(fig, legend=False, height=300)
    fig.update_layout(margin=dict(l=60, r=20, t=20, b=40))
    return fig


def segment_radar(rows: list[dict], selected_segment: int | None = None) -> go.Figure:
    if not rows:
        return _empty_figure()
    """Radar perbandingan karakteristik antar segmen (dinormalisasi 0-1 per
    metrik) - menjawab catatan 'tambahkan grafik biar interaktif, bukan teks
    doang' pada bagian karakteristik segmen."""
    df = pd.DataFrame(rows).sort_values("cluster_kmeans")
    metrics = ["population_share", "fraud_rate", "avg_risk_score", "high_risk_rate"]
    metric_labels = ["Pangsa populasi", "Tingkat fraud", "Rata-rata skor risiko", "Tingkat high-risk"]
    norm = df[metrics].copy()
    for m in metrics:
        rng = norm[m].max() - norm[m].min()
        norm[m] = (norm[m] - norm[m].min()) / rng if rng > 0 else 0.5

    fig = go.Figure()
    for _, row in df.iterrows():
        cid = row["cluster_kmeans"]
        vals = norm.loc[row.name, metrics].tolist()
        vals.append(vals[0])
        is_dim = selected_segment is not None and int(cid) != int(selected_segment)
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=metric_labels + [metric_labels[0]],
            name=_segment_label_short(cid), mode="lines+markers",
            line=dict(color=segment_color(cid), width=1 if is_dim else 3),
            opacity=0.25 if is_dim else 0.95,
            hovertemplate="<b>" + _segment_label(cid) + "</b><br>%{theta}: nilai relatif %{r:.2f}<extra></extra>",
        ))
    fig.update_layout(polar=dict(
        radialaxis=dict(visible=True, range=[0, 1], showticklabels=False, gridcolor=COLORS["border"]),
        angularaxis=dict(gridcolor=COLORS["border"]),
        bgcolor="rgba(0,0,0,0)",
        domain=dict(x=[0, 1], y=[0.14, 1]),
    ))
    apply_theme(fig, legend=True, height=380)
    fig.update_layout(margin=dict(l=30, r=30, t=20, b=40),
                      legend=dict(orientation="h", yanchor="top", y=0.10, x=0.5, xanchor="center"))
    return fig


def segment_landscape(rows: list[dict], selected_segment: int | None = None) -> go.Figure:
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows).sort_values("cluster_kmeans")
    sizes = np.sqrt(df["transactions"].astype(float))
    sizes = 18 + 55 * (sizes - sizes.min()) / max(1e-9, (sizes.max() - sizes.min()))
    colors = [segment_color(c) for c in df["cluster_kmeans"]]
    if selected_segment is not None:
        colors = [c if int(seg) == int(selected_segment) else _fade(c, 0.4) for c, seg in zip(colors, df["cluster_kmeans"])]

    fig = go.Figure(go.Scatter(
        x=df["transactions"], y=df["avg_risk_score"], mode="markers+text",
        marker=dict(size=sizes, color=colors, line=dict(width=2, color=COLORS["surface"])),
        text=[f"Seg {c}" for c in df["cluster_kmeans"]], textposition="top center",
        customdata=np.stack([df["population_share"] * 100, df["fraud_rate"] * 100, df["high_risk_rate"] * 100], axis=-1),
        hovertemplate=(
            "<b>%{text}</b><br>Jumlah transaksi: %{x:,.0f} (%{customdata[0]:.3f}% populasi)"
            "<br>Rata-rata skor risiko: %{y:.2f} / 6<br>Tingkat fraud: %{customdata[1]:.3f}%"
            "<br>Tingkat high-risk: %{customdata[2]:.2f}%<extra></extra>"
        ),
    ))
    fig.update_xaxes(type="log", title="Jumlah transaksi (skala log)")
    fig.update_yaxes(title="Rata-rata skor risiko (0-6)")
    apply_theme(fig, legend=False, height=340)
    return fig


def risk_level_bar(rows: list[dict]) -> go.Figure:
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows)
    df["risk_level"] = pd.Categorical(df["risk_level"], categories=RISK_ORDER, ordered=True)
    df = df.sort_values("risk_level")
    colors = [RISK_COLOR_MAP.get(r, COLORS["ink_faint"]) for r in df["risk_level"]]
    fig = go.Figure(go.Bar(
        x=df["risk_level"].astype(str), y=df["transactions"], marker=dict(color=colors),
        text=[f"{p:.2f}%".replace(".", ",") for p in df["percentage"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>Level %{x}</b><br>Jumlah transaksi: %{y:,.0f}<br>Persentase: %{text}<extra></extra>",
    ))
    fig.update_yaxes(title="Jumlah transaksi", type="log")
    fig.update_xaxes(title=None)
    apply_theme(fig, legend=False, height=300)
    return fig


def category_bar(rows: list[dict], cat_col: str, label_map: dict | None = None, color=None,
                  orientation: str = "h", height: int = 320) -> go.Figure:
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows).sort_values("transactions", ascending=(orientation == "h"))
    labels = [label_map.get(v, v) if label_map else v for v in df[cat_col]]
    color = color or COLORS["brand"]
    text = [f"{cfg.format_int(t)} ({p:.2f}%)".replace(".", ",", 1) for t, p in zip(df["transactions"], df["percentage"])]
    if orientation == "h":
        fig = go.Figure(go.Bar(x=df["transactions"], y=labels, orientation="h", marker=dict(color=color),
                                text=text, textposition="outside", cliponaxis=False,
                                hovertemplate="<b>%{y}</b><br>Jumlah: %{x:,.0f}<extra></extra>"))
        fig.update_xaxes(title="Jumlah transaksi")
        fig.update_yaxes(title=None)
    else:
        fig = go.Figure(go.Bar(x=labels, y=df["transactions"], marker=dict(color=color),
                                text=text, textposition="outside", cliponaxis=False,
                                hovertemplate="<b>%{x}</b><br>Jumlah: %{y:,.0f}<extra></extra>"))
        fig.update_yaxes(title="Jumlah transaksi")
        fig.update_xaxes(title=None)
    apply_theme(fig, legend=False, height=height)
    return fig


def fraud_by_score_chart(rows: list[dict]) -> go.Figure:
    if not rows:
        return _empty_figure()
    """Dual-axis: batang = jumlah transaksi, garis = tingkat fraud. Menonjolkan
    temuan 'Sedang (skor 2) justru fraud rate-nya lebih tinggi dari Kritis'."""
    df = pd.DataFrame(rows).sort_values("risk_score")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["risk_score"], y=df["transactions"], name="Jumlah transaksi",
        marker=dict(color=COLORS["brand_soft"], line=dict(color=COLORS["brand"], width=1)),
        yaxis="y1",
        hovertemplate="Skor risiko %{x}<br>Jumlah transaksi: %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["risk_score"], y=df["fraud_rate"] * 100, name="Tingkat fraud (%)", mode="lines+markers",
        line=dict(color=COLORS["danger"], width=3), marker=dict(size=9),
        yaxis="y2",
        hovertemplate="Skor risiko %{x}<br>Tingkat fraud: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(title="Skor risiko (0 = normal, 6 = paling banyak indikator)", dtick=1),
        yaxis=dict(title="Jumlah transaksi", type="log"),
        yaxis2=dict(title="Tingkat fraud (%)", overlaying="y", side="right", showgrid=False),
    )
    apply_theme(fig, legend=True, height=340)
    return fig


def method_overlap_heatmap(matrix_rows: list[dict]) -> go.Figure:
    if not matrix_rows:
        return _empty_figure()
    methods = ["flag_IQR", "flag_ZScore", "flag_IsoForest", "flag_HDBSCAN"]
    short_labels = {"flag_IQR": "IQR", "flag_ZScore": "Z-Score", "flag_IsoForest": "Isolation Forest", "flag_HDBSCAN": "HDBSCAN"}
    z = [[row[m2] for m2 in methods] for row in matrix_rows]
    labels = [short_labels[m] for m in methods]
    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=labels, colorscale=[[0, COLORS["surface_sunken"]], [1, COLORS["brand"]]],
        text=[[cfg.format_int(v) for v in row] for row in z], texttemplate="%{text}",
        hovertemplate="%{y} ∩ %{x}<br>Jumlah transaksi: %{z:,.0f}<extra></extra>",
        showscale=False,
    ))
    apply_theme(fig, legend=False, height=320)
    fig.update_layout(margin=dict(l=110, r=20, t=20, b=90))
    return fig


def category_breakdown_bar(rows: list[dict], category_col: str, metric: str = "transactions") -> go.Figure:
    """Bar horizontal generik utk breakdown kategori 2 nilai (jenis tujuan,
    status kuras, dst) - menggantikan wilayah_bar setelah dimensi spasial
    buatan dihapus (dataset tidak punya atribut geografis asli)."""
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows).sort_values(metric, ascending=True)
    if metric == "transactions":
        x = df["transactions"]; text = [f"{cfg.format_int(v)}" for v in df["transactions"]]
        xaxis_title = "Jumlah transaksi"
    else:
        x = df["fraud_rate"] * 100; text = [f"{v:.3f}%".replace(".", ",") for v in x]
        xaxis_title = "Tingkat fraud (%)"
    fig = go.Figure(go.Bar(
        x=x, y=df[category_col], orientation="h", marker=dict(color=COLORS["seg_1"]),
        text=text, textposition="outside", cliponaxis=False,
        customdata=np.stack([df["share"] * 100, df["high_risk_rate"] * 100, df["avg_risk_score"]], axis=-1),
        hovertemplate=(
            "<b>%{y}</b><br>Jumlah transaksi: " + ("%{x:,.0f}" if metric == "transactions" else "%{customdata[0]:.2f}% dari total")
            + "<br>Tingkat high-risk: %{customdata[1]:.2f}%<br>Rata-rata skor risiko: %{customdata[2]:.2f}<extra></extra>"
        ),
    ))
    fig.update_xaxes(title=xaxis_title)
    fig.update_yaxes(title=None)
    apply_theme(fig, legend=False, height=220)
    return fig


def rules_lift_bar(rules_rows: list[dict], top_n: int = 10) -> go.Figure:
    if not rules_rows:
        return _empty_figure()
    df = pd.DataFrame(rules_rows).head(top_n).iloc[::-1]
    labels = [f"{w} → {t}" for w, t in zip(df["when_text"], df["then_text"])]
    labels = [l if len(l) <= 55 else l[:52] + "..." for l in labels]
    fig = go.Figure(go.Bar(
        x=df["lift"], y=labels, orientation="h", marker=dict(color=COLORS["accent"]),
        text=[cfg.format_multiplier(v) for v in df["lift"]], textposition="outside", cliponaxis=False,
        customdata=np.stack([df["confidence"] * 100, df["support"] * 100], axis=-1),
        hovertemplate="%{y}<br>Lift: %{x:.1f}x<br>Confidence: %{customdata[0]:.1f}%<br>Coverage: %{customdata[1]:.3f}%<extra></extra>",
    ))
    fig.update_xaxes(title="Lift (seberapa kuat pola dibanding kebetulan)")
    fig.update_yaxes(title=None, automargin=True)
    apply_theme(fig, legend=False, height=max(280, 34 * len(df)))
    fig.update_layout(margin=dict(l=10, r=80, t=20, b=45))
    return fig


def rule_group_donut(rules_rows: list[dict]) -> go.Figure:
    if not rules_rows:
        return _empty_figure()
    df = pd.DataFrame(rules_rows)
    counts = df["rule_group"].value_counts().reindex(cfg.RULE_GROUP_ORDER).fillna(0)
    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values, hole=0.55,
        marker=dict(colors=CATEGORICAL_SEQUENCE),
        hovertemplate="<b>%{label}</b><br>Jumlah pola: %{value}<br>%{percent}<extra></extra>",
        textinfo="value+percent",
    ))
    apply_theme(fig, legend=True, height=300)
    return fig


def fraud_funnel(kpi: dict) -> go.Figure:
    """Corong 3 tahap: seluruh transaksi -> antrean high-risk -> fraud tertangkap
    di antrean. Menceritakan tujuan utama dataset (fraud) dalam satu grafik:
    dari jutaan transaksi, model mempersempit ke antrean kecil yang jauh lebih
    pekat fraud-nya. Interaktif (hover menampilkan angka & persentase)."""
    total = kpi.get("total_transaksi", 0) or 0
    high_risk = kpi.get("total_high_risk", 0) or 0
    hr_rate = kpi.get("high_risk_fraud_rate", None)
    fraud_in_hr = int(round(high_risk * hr_rate)) if (high_risk and hr_rate) else 0
    if not total:
        return _empty_figure()

    stages = ["Seluruh transaksi", "Antrean high-risk", "Fraud di antrean high-risk"]
    values = [total, high_risk, fraud_in_hr]
    colors = [COLORS["brand"], COLORS["accent"], COLORS["danger"]]

    fig = go.Figure(go.Funnel(
        y=stages, x=values,
        marker=dict(color=colors),
        textposition="inside", textinfo="value",
        texttemplate="%{value:,.0f}",
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} transaksi<extra></extra>",
        connector=dict(line=dict(color=COLORS["border_strong"], width=1)),
    ))
    apply_theme(fig, legend=False, height=300)
    fig.update_layout(margin=dict(l=10, r=20, t=20, b=20))
    return fig


def fraud_enrichment_gauge(kpi: dict) -> go.Figure:
    """Indikator sederhana: seberapa jauh lebih pekat fraud di antrean high-risk
    dibanding rata-rata populasi (enrichment). Angka besar = model bekerja."""
    enrichment = kpi.get("fraud_enrichment", None)
    if not enrichment:
        return _empty_figure("Tidak ada transaksi high-risk pada filter ini.")
    hr_rate = (kpi.get("high_risk_fraud_rate") or 0) * 100
    base = 0.129
    fig = go.Figure(go.Bar(
        x=[base, hr_rate],
        y=["Rata-rata populasi", "Antrean high-risk"],
        orientation="h",
        marker=dict(color=[COLORS["ink_faint"], COLORS["danger"]]),
        text=[f"{base:.3f}%".replace(".", ","), f"{hr_rate:.2f}%".replace(".", ",")],
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Tingkat fraud: %{x:.3f}%<extra></extra>",
    ))
    fig.update_xaxes(title="Tingkat fraud (%)")
    fig.update_yaxes(title=None, autorange="reversed")
    apply_theme(fig, legend=False, height=200)
    fig.update_layout(margin=dict(l=10, r=70, t=10, b=40))
    return fig


def segment_projection_scatter(rows: list[dict], selected_segment: int | None = None,
                                method_name: str = "UMAP/t-SNE") -> go.Figure:
    """Scatter titik-titik transaksi hasil proyeksi UMAP/t-SNE, diwarnai per
    segmen. Otomatis 3D (bisa diputar/zoom/pan dengan drag) kalau data punya
    kolom proj_z, selain itu 2D. Membuat pemisahan segmen terlihat jelas secara
    visual. Hover = segmen + status fraud; segmen terpilih disorot, lainnya
    diredupkan. Kalau rows kosong (file proyeksi belum dibuat), tampilkan pesan."""
    if not rows:
        return _empty_figure(
            "Scatter segmen belum aktif. Jalankan tools/build_segment_projection.py "
            "untuk menghasilkan koordinat proyeksi, lalu jalankan ulang pipeline."
        )
    df = pd.DataFrame(rows)
    is_3d = "proj_z" in df.columns

    max_points = 3000
    if len(df) > max_points:
        frac = max_points / len(df)
        parts = []
        for _cid, g in df.groupby("cluster_kmeans"):
            parts.append(g.sample(n=max(1, int(len(g) * frac)), random_state=42))
        df = pd.concat(parts, ignore_index=True)

    fig = go.Figure()

    seg_ids = sorted(df["cluster_kmeans"].unique())
    for cid in seg_ids:
        sub = df[df["cluster_kmeans"] == cid]
        base_color = segment_color(cid)
        if selected_segment is not None and int(cid) != int(selected_segment):
            color = _fade(base_color, 0.18)
            size = 3 if is_3d else 4
        else:
            color = base_color
            size = 4 if is_3d else 5
        name = _segment_label(cid)
        fraud_txt = np.where(sub["isFraud"].to_numpy(), "Ya", "Tidak") if "isFraud" in sub.columns else np.array(["-"] * len(sub))
        if is_3d:
            fig.add_trace(go.Scatter3d(
                x=sub["proj_x"], y=sub["proj_y"], z=sub["proj_z"], mode="markers", name=name,
                marker=dict(color=color, size=size, line=dict(width=0), opacity=0.75),
                customdata=fraud_txt,
                hovertemplate=f"<b>{name}</b><br>Fraud: %{{customdata}}<extra></extra>",
            ))
        else:
            fig.add_trace(go.Scattergl(
                x=sub["proj_x"], y=sub["proj_y"], mode="markers", name=name,
                marker=dict(color=color, size=size, line=dict(width=0), opacity=0.75),
                customdata=fraud_txt,
                hovertemplate=f"<b>{name}</b><br>Fraud: %{{customdata}}<extra></extra>",
            ))

    apply_theme(fig, legend=True, height=540 if is_3d else 480)
    if is_3d:
        axis_style = dict(showticklabels=False, title="", showspikes=False,
                          backgroundcolor="rgba(0,0,0,0)", gridcolor=COLORS["border"])
        fig.update_layout(
            scene=dict(xaxis=axis_style, yaxis=axis_style, zaxis=axis_style,
                       aspectmode="cube", domain=dict(x=[0, 1], y=[0.16, 1])),
            margin=dict(l=0, r=0, t=30, b=10),
            legend=dict(orientation="h", yanchor="top", y=0.12, x=0.5, xanchor="center"),
        )
    else:
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=60),
            legend=dict(orientation="h", yanchor="top", y=-0.05, x=0.5, xanchor="center"),
        )
    return fig


def rules_scatter(rows: list[dict], highlight_fraud: bool = True) -> go.Figure:
    """Scatter confidence (x) vs lift (y), ukuran titik = coverage/support.
    Ini cara baku memvisualisasikan association rules: pojok kanan-atas =
    pola paling kuat & paling yakin. Titik menuju fraud diberi warna merah.
    Interaktif: hover menampilkan JIKA -> MAKA lengkap."""
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows)
    conf = df["confidence"].astype(float) * 100
    lift = df["lift"].astype(float)
    supp = df["support"].astype(float)
    sizes = 8 + (supp / supp.max() * 26 if supp.max() > 0 else 0)

    is_fraud = df["consequents_str"].str.contains("isFraud_yes", na=False) if "consequents_str" in df.columns else pd.Series([False] * len(df))
    colors = [COLORS["danger"] if fr else COLORS["brand"] for fr in is_fraud] if highlight_fraud else COLORS["brand"]

    when = df["when_text"] if "when_text" in df.columns else df.get("antecedents_str", "")
    then = df["then_text"] if "then_text" in df.columns else df.get("consequents_str", "")

    fig = go.Figure(go.Scatter(
        x=conf, y=lift, mode="markers",
        marker=dict(size=sizes, color=colors, opacity=0.7, line=dict(width=0.5, color="white")),
        customdata=np.stack([when, then, supp * 100], axis=-1),
        hovertemplate=("<b>JIKA</b> %{customdata[0]}<br><b>MAKA</b> %{customdata[1]}"
                       "<br>Confidence: %{x:.1f}%<br>Lift: %{y:.1f}x<br>Coverage: %{customdata[2]:.3f}%<extra></extra>"),
    ))
    fig.update_xaxes(title="Confidence (%): seberapa yakin pola ini")
    fig.update_yaxes(title="Lift (x): seberapa kuat vs kebetulan", type="log")
    apply_theme(fig, legend=False, height=420)
    fig.update_layout(margin=dict(l=10, r=20, t=20, b=45))
    return fig


def method_contribution_bar(overlap_matrix: list[dict]) -> go.Figure:
    """Berapa banyak transaksi yang ditandai TIAP metode deteksi (diambil dari
    diagonal matriks overlap). Menjawab 'metode mana yang paling banyak menemukan
    anomali' - justifikasi memakai banyak metode. Interaktif (hover = jumlah)."""
    if not overlap_matrix:
        return _empty_figure()
    method_labels = {
        "flag_IQR": "IQR", "flag_ZScore": "Z-Score",
        "flag_IsoForest": "Isolation Forest", "flag_HDBSCAN": "BIRCH+HDBSCAN",
    }
    names, counts = [], []
    for entry in overlap_matrix:
        m = entry["method"]
        names.append(method_labels.get(m, m))
        counts.append(entry.get(m, 0))
    df = pd.DataFrame({"method": names, "count": counts}).sort_values("count", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["count"], y=df["method"], orientation="h",
        marker=dict(color=COLORS["accent"]),
        text=[cfg.format_int(c) for c in df["count"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Menandai %{x:,.0f} transaksi<extra></extra>",
    ))
    fig.update_xaxes(title="Jumlah transaksi ditandai")
    fig.update_yaxes(title=None)
    apply_theme(fig, legend=False, height=240)
    fig.update_layout(margin=dict(l=10, r=70, t=10, b=40))
    return fig


def recommendation_map(recs: list[dict]) -> go.Figure:
    if not recs:
        return _empty_figure()
    prio_order = ["Tinggi", "Sedang", "Rendah"]
    categories = sorted({r["category"] for r in recs})
    cat_palette = [COLORS["brand"], COLORS["accent"], COLORS["warning"], COLORS["info"], COLORS["success"]]
    cat_color = {c: cat_palette[i % len(cat_palette)] for i, c in enumerate(categories)}

    from collections import defaultdict
    counts = defaultdict(lambda: defaultdict(int))
    titles_map = defaultdict(lambda: defaultdict(list))
    for r in recs:
        counts[r["priority"]][r["category"]] += 1
        titles_map[r["priority"]][r["category"]].append(r["title"])

    fig = go.Figure()
    for c in categories:
        xvals, hovertexts = [], []
        for p in prio_order:
            n = counts[p][c]
            xvals.append(n)
            titles = titles_map[p][c]
            ht = "<br>".join("• " + t for t in titles) if titles else "Tidak ada"
            hovertexts.append(f"<b>{c}: prioritas {p}</b><br>{ht}")
        fig.add_trace(go.Bar(
            name=c, y=prio_order, x=xvals, orientation="h",
            marker_color=cat_color[c],
            text=[str(v) if v else "" for v in xvals], textposition="inside",
            insidetextanchor="middle",
            customdata=hovertexts,
            hovertemplate="%{customdata}<extra></extra>",
        ))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Jumlah rekomendasi", dtick=1)
    fig.update_yaxes(title=None, categoryorder="array", categoryarray=prio_order[::-1])
    apply_theme(fig, legend=True, height=340)
    fig.update_layout(margin=dict(l=10, r=20, t=20, b=40),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=10)))
    return fig


def cluster_risk_chart(rows: list[dict], selected_segment: int | None = None) -> go.Figure:
    """Grouped bar tingkat FRAUD & HIGH-RISK per segmen. Dipisah dari porsi
    merchant karena skalanya sangat kecil (fraud ~0,1%, high-risk ~0,7%) - kalau
    digabung dengan merchant (puluhan %), batangnya tak terlihat. Sumbu Y
    otomatis menyesuaikan nilai kecil ini. Interaktif."""
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows)
    labels = [_segment_label_short(int(r["cluster_kmeans"])) for _, r in df.iterrows()]
    full = [_segment_label(int(r["cluster_kmeans"])) for _, r in df.iterrows()]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Tingkat fraud", x=labels, y=df["fraud_rate"] * 100,
        marker_color=COLORS["danger"], customdata=full,
        text=[f"{v*100:.3f}%".replace(".", ",") for v in df["fraud_rate"]],
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{customdata}</b><br>Fraud: %{y:.3f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="High-risk", x=labels, y=df["high_risk_rate"] * 100,
        marker_color=COLORS["warning"], customdata=full,
        text=[f"{v*100:.2f}%".replace(".", ",") for v in df["high_risk_rate"]],
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{customdata}</b><br>High-risk: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title=None, tickangle=0, automargin=True)
    fig.update_yaxes(title="Persentase (%)", rangemode="tozero")
    apply_theme(fig, legend=True, height=340)
    fig.update_layout(margin=dict(l=10, r=20, t=30, b=40))
    return fig


def cluster_merchant_chart(rows: list[dict], selected_segment: int | None = None) -> go.Figure:
    """Bar porsi transaksi ke MERCHANT per segmen (skala 0-100%). Dipisah dari
    fraud/high-risk supaya masing-masing terbaca jelas di skalanya sendiri."""
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows)
    labels = [_segment_label_short(int(r["cluster_kmeans"])) for _, r in df.iterrows()]
    full = [_segment_label(int(r["cluster_kmeans"])) for _, r in df.iterrows()]
    colors = [segment_color(int(r["cluster_kmeans"])) for _, r in df.iterrows()]

    fig = go.Figure(go.Bar(
        x=labels, y=df["merchant_share"] * 100,
        marker_color=colors, customdata=full,
        text=[f"{v*100:.0f}%".replace(".", ",") for v in df["merchant_share"]],
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{customdata}</b><br>Ke merchant: %{y:.1f}%<extra></extra>",
    ))
    fig.update_xaxes(title=None, tickangle=0, automargin=True)
    fig.update_yaxes(title="Porsi ke merchant (%)", range=[0, 105])
    apply_theme(fig, legend=False, height=340)
    fig.update_layout(margin=dict(l=10, r=20, t=30, b=40))
    return fig


def rules_network(rows: list[dict], max_rules: int = 25) -> go.Figure:
    """Network graph: node = atribut (item), edge = aturan JIKA->MAKA. Membuat
    hubungan antar-atribut terlihat sebagai jaringan - atribut yang sering jadi
    pemicu/akibat tampak sebagai hub. Node menuju fraud diberi warna merah.
    Layout lingkaran deterministik (tanpa perlu networkx). Interaktif: hover node
    = nama atribut; hover edge = confidence & lift.

    Dibatasi max_rules aturan terkuat supaya graph tetap terbaca (graph terlalu
    padat justru mengaburkan)."""
    if not rows:
        return _empty_figure()

    rules = sorted(rows, key=lambda r: r.get("lift", 0), reverse=True)[:max_rules]

    def _atoms(s):
        return [a.strip() for a in str(s).split(",") if a.strip()]

    nodes = {}
    edges = []
    for r in rules:
        antes = _atoms(r.get("antecedents_str", ""))
        cons = _atoms(r.get("consequents_str", ""))
        is_fraud = any("isFraud_yes" in c for c in cons)
        for a in antes + cons:
            if a not in nodes:
                nodes[a] = len(nodes)
        for a in antes:
            for c in cons:
                edges.append((a, c, r.get("confidence", 0), r.get("lift", 0), is_fraud))

    if not nodes:
        return _empty_figure()

    n = len(nodes)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    radius = 1.0
    pos = {atom: (radius * np.cos(angles[i]), radius * np.sin(angles[i]))
           for atom, i in nodes.items()}

    edge_x, edge_y = [], []
    fraud_edge_x, fraud_edge_y = [], []
    for src, dst, conf, lift, is_fraud in edges:
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        if is_fraud:
            fraud_edge_x += [x0, x1, None]
            fraud_edge_y += [y0, y1, None]
        else:
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=0.8, color=COLORS["border_strong"]),
        hoverinfo="none", showlegend=False,
    ))
    if fraud_edge_x:
        fig.add_trace(go.Scatter(
            x=fraud_edge_x, y=fraud_edge_y, mode="lines",
            line=dict(width=1.6, color=COLORS["danger"]),
            hoverinfo="none", showlegend=False,
        ))

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    degree = {atom: 0 for atom in nodes}
    for src, dst, *_ in edges:
        degree[src] += 1
        degree[dst] += 1

    for atom, i in nodes.items():
        x, y = pos[atom]
        node_x.append(x)
        node_y.append(y)
        full = cfg.humanize_item(atom)
        node_text.append(f"<b>{full}</b><br>Terhubung ke {degree[atom]} aturan")
        if "isFraud_yes" in atom:
            node_color.append(COLORS["danger"])
        elif atom.startswith("cluster_kmeans"):
            node_color.append(COLORS["accent"])
        else:
            node_color.append(COLORS["brand"])
        node_size.append(min(34, 14 + degree[atom] * 2))

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers",
        marker=dict(size=node_size, color=node_color, line=dict(width=1.5, color="white"), opacity=0.9),
        customdata=node_text,
        hovertemplate="%{customdata}<extra></extra>",
        showlegend=False,
    ))

    fig.update_xaxes(visible=False, range=[-1.25, 1.25])
    fig.update_yaxes(visible=False, range=[-1.25, 1.25], scaleanchor="x", scaleratio=1)
    apply_theme(fig, legend=False, height=440)
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    return fig


def segment_proportion_donut(rows: list[dict], selected_segment: int | None = None) -> go.Figure:
    """Donut proporsi jumlah transaksi tiap segmen. Melengkapi peta sebaran 3D:
    scatter menunjukkan SEBARAN, donut menunjukkan UKURAN relatif tiap segmen.
    Segmen terpilih ditarik keluar (pull) sebagai sorotan. Interaktif."""
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows)
    vals = df["transactions"] if "transactions" in df.columns else df.get("total", df.get("population_share"))
    ids = [int(c) for c in df["cluster_kmeans"]]
    labels = [_segment_label_short(c) for c in ids]
    full = [_segment_label(c) for c in ids]
    colors = [segment_color(c) for c in ids]
    pulls = [0.12 if (selected_segment is not None and c == int(selected_segment)) else 0 for c in ids]

    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=1.5)),
        pull=pulls, sort=False,
        textinfo="percent", textfont=dict(size=11),
        customdata=full,
        hovertemplate="<b>%{customdata}</b><br>%{value:,.0f} transaksi<br>%{percent}<extra></extra>",
    ))
    apply_theme(fig, legend=True, height=480)
    fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=50),
        legend=dict(orientation="h", yanchor="top", y=-0.02, x=0.5, xanchor="center", font=dict(size=10)),
    )
    return fig


def rules_strength_summary(rows: list[dict]) -> go.Figure:
    """Bar bertingkat: kelompokkan aturan berdasarkan kekuatan (lift) ke beberapa
    tier, tiap batang dipecah 'menuju fraud' (merah) vs 'pola umum' (biru).
    Menjawab pertanyaan gambaran besar: dari sekian aturan, berapa yang benar-benar
    kuat, dan berapa yang mengarah ke fraud? Melengkapi kartu/tabel di bawah yang
    sudah menampilkan detail per-aturan."""
    if not rows:
        return _empty_figure()
    df = pd.DataFrame(rows)

    def _tier(lift):
        if lift >= 100: return "Sangat kuat\n(lift ≥ 100)"
        if lift >= 10:  return "Kuat\n(lift 10-100)"
        if lift >= 2:   return "Sedang\n(lift 2-10)"
        return "Lemah\n(lift < 2)"
    df["tier"] = df["lift"].apply(_tier)
    df["is_fraud"] = df["consequents_str"].str.contains("isFraud_yes", na=False) if "consequents_str" in df.columns else False

    tier_order = ["Sangat kuat\n(lift ≥ 100)", "Kuat\n(lift 10-100)", "Sedang\n(lift 2-10)", "Lemah\n(lift < 2)"]
    fraud_counts, umum_counts = [], []
    for t in tier_order:
        sub = df[df["tier"] == t]
        fraud_counts.append(int(sub["is_fraud"].sum()))
        umum_counts.append(int((~sub["is_fraud"]).sum()))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Menuju fraud", y=tier_order, x=fraud_counts, orientation="h",
        marker_color=COLORS["danger"],
        text=[str(c) if c else "" for c in fraud_counts], textposition="auto",
        hovertemplate="<b>%{y}</b><br>Pola menuju fraud: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Pola umum", y=tier_order, x=umum_counts, orientation="h",
        marker_color=COLORS["brand"],
        text=[str(c) if c else "" for c in umum_counts], textposition="auto",
        hovertemplate="<b>%{y}</b><br>Pola umum: %{x}<extra></extra>",
    ))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Jumlah pola")
    fig.update_yaxes(title=None, autorange="reversed")
    apply_theme(fig, legend=True, height=420)
    fig.update_layout(margin=dict(l=10, r=20, t=20, b=40),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
    return fig
