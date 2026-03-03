# dashboard.py
from __future__ import annotations

import numpy as np
import pandas as pd
import random

from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go

from sim_core import SimConfig, run_sim, novelty_metrics


# ----------------------------
# UI helpers
# ----------------------------

def card_style():
    return {
        "padding": "14px",
        "border": "1px solid #ddd",
        "borderRadius": "12px",
        "background": "white",
        "boxShadow": "0 1px 2px rgba(0,0,0,0.05)",
    }

def kpi_box(title: str, value: str, subtitle: str = ""):
    return html.Div(
        style={**card_style(), "flex": "1 1 240px"},
        children=[
            html.Div(title, style={"fontWeight": "bold", "marginBottom": "8px"}),
            html.Div(value, style={"fontSize": "26px", "fontWeight": "bold"}),
            html.Div(subtitle, style={"fontSize": "12px", "color": "#666", "marginTop": "6px"}),
        ],
    )

def badge(text: str):
    return html.Span(
        text,
        style={
            "display": "inline-block",
            "padding": "6px 10px",
            "borderRadius": "999px",
            "border": "1px solid #ddd",
            "background": "#f7f7f7",
            "fontSize": "12px",
        },
    )

def empty_fig(title: str):
    fig = go.Figure()
    fig.update_layout(title=title, margin=dict(l=25, r=25, t=50, b=25))
    return fig


# ----------------------------
# Human-friendly mappings
# ----------------------------

def camera_quality(min_scale: float) -> str:
    if min_scale >= 0.95:
        return "1080p (Good)"
    if min_scale >= 0.80:
        return "720p (Reduced)"
    if min_scale >= 0.60:
        return "480p (Throttled)"
    return "Stuttering (Heavily Throttled)"

def safety_label(viol_pct: float, p95: float, risk: float) -> str:
    if viol_pct > 0.0 or risk > 0.75 or p95 > 9.0:
        return "🔴 Critical"
    if risk > 0.35 or p95 > 7.5:
        return "🟡 Warning"
    return "🟢 Safe"


# ----------------------------
# Story visuals (simple + clear)
# ----------------------------

def risk_gauge(risk: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(risk * 100),
        number={"suffix": "%"},
        title={"text": "Predicted Congestion Risk"},
        gauge={"axis": {"range": [0, 100]}}
    ))
    fig.update_layout(margin=dict(l=25, r=25, t=50, b=10), height=220)
    return fig

def prb_donut(df: pd.DataFrame, title: str) -> go.Figure:
    c = df[df["event"] == "controller"]
    if c.empty:
        return empty_fig(title)
    last = c.iloc[-1]
    vals = [int(last["bud_url"]), int(last["bud_embb"]), int(last["bud_mmtc"])]
    labels = ["URLLC (Control)", "eMBB (Video)", "mMTC (Sensors)"]
    fig = go.Figure(data=[go.Pie(labels=labels, values=vals, hole=0.55)])
    fig.update_layout(title=title, margin=dict(l=25, r=25, t=50, b=25), height=320)
    return fig

def controller_timeline(df: pd.DataFrame, title: str) -> go.Figure:
    c = df[df["event"] == "controller"].copy()
    if c.empty:
        return empty_fig(title)

    # sample for readability
    c = c.iloc[::50].copy()
    c["code"] = c["controller_event"].map({
        "NORMAL": 0,
        "RISK_PREDICTED": 1,
        "BORROWING": 2,
        "EMBB_THROTTLE": 3,
        "RECOVERY": 4,
    }).fillna(0)

    order = ["NORMAL", "RISK_PREDICTED", "BORROWING", "EMBB_THROTTLE", "RECOVERY"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=c["tti"], y=c["code"],
        mode="lines+markers",
        text=c["controller_event"],
        hovertemplate="t=%{x} | %{text}<extra></extra>"
    ))
    fig.update_layout(
        title=title,
        xaxis_title="time (TTI ~ ms)",
        yaxis_title="state",
        yaxis=dict(tickmode="array", tickvals=list(range(len(order))), ticktext=order),
        margin=dict(l=25, r=25, t=50, b=25),
        height=320
    )
    return fig

def factory_map(df: pd.DataFrame, cfg: SimConfig, title: str) -> go.Figure:
    flows = df[df["event"].isin(["enqueue", "tx"])][["ue_id", "qos"]].drop_duplicates()
    viol_ues = set(df[(df["event"] == "violation") & (df.get("qos","") == "URLLC")]["ue_id"].dropna().astype(int).tolist())

    x_gnb, y_gnb = 0.0, 0.0

    xs, ys, colors, sizes, labels, symbols = [], [], [], [], [], []
    for _, row in flows.iterrows():
        ue = int(row["ue_id"])
        qos = str(row["qos"])

        r = random.Random(cfg.seed * 10_000 + ue)
        rad = r.uniform(0.25, 1.0)
        theta = r.uniform(0, 2*np.pi)
        x = rad * np.cos(theta)
        y = rad * np.sin(theta)

        if qos == "URLLC":
            colors.append("#e74c3c"); symbols.append("square")
        elif qos == "eMBB":
            colors.append("#3498db"); symbols.append("circle")
        else:
            colors.append("#2ecc71"); symbols.append("triangle-up")

        is_viol = (ue in viol_ues and qos == "URLLC")
        sizes.append(20 if is_viol else 14)
        labels.append(f"UE {ue} | {qos}" + (" | VIOLATION" if is_viol else ""))
        xs.append(x); ys.append(y)

    fig = go.Figure()

    # links
    for x, y in zip(xs, ys):
        fig.add_trace(go.Scatter(
            x=[x_gnb, x], y=[y_gnb, y],
            mode="lines",
            line=dict(width=1, color="rgba(0,0,0,0.12)"),
            hoverinfo="skip",
            showlegend=False
        ))

    # gNB
    fig.add_trace(go.Scatter(
        x=[x_gnb], y=[y_gnb],
        mode="markers+text",
        marker=dict(size=28, color="#f39c12", line=dict(width=2, color="black")),
        text=["gNB"], textposition="bottom center",
        hovertemplate="gNB (Base Station)<extra></extra>",
        showlegend=False
    ))

    def add_group(sym, name):
        idx = [i for i, s in enumerate(symbols) if s == sym]
        if not idx:
            return
        fig.add_trace(go.Scatter(
            x=[xs[i] for i in idx],
            y=[ys[i] for i in idx],
            mode="markers",
            marker=dict(size=[sizes[i] for i in idx], color=[colors[i] for i in idx], symbol=sym,
                        line=dict(width=1, color="black")),
            text=[labels[i] for i in idx],
            hovertemplate="%{text}<extra></extra>",
            name=name
        ))

    add_group("square", "Machines (URLLC)")
    add_group("circle", "Cameras (eMBB)")
    add_group("triangle-up", "Sensors (mMTC)")

    fig.update_layout(
        title=title,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(orientation="h"),
        margin=dict(l=15, r=15, t=50, b=15),
        height=520
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


# ----------------------------
# Dash layout
# ----------------------------

app = Dash(__name__)
app.title = "5G Smart Factory — Baseline vs Smart"

app.layout = html.Div(
    style={"display": "flex", "height": "100vh", "fontFamily": "Arial"},
    children=[
        # Sidebar (ONLY 3 variables)
        html.Div(
            style={
                "width": "340px",
                "padding": "16px",
                "borderRight": "1px solid #ddd",
                "background": "#fafafa",
                "overflowY": "auto",
            },
            children=[
                html.H2("Scenario Controls", style={"marginTop": 0}),
                html.Div("Only these 3 values change. Everything else is automatic.",
                         style={"fontSize": "12px", "color": "#666"}),

                html.Br(),
                html.Label("# Machines (URLLC UEs)"),
                dcc.Slider(id="n_urllc", min=1, max=30, step=1, value=8,
                           marks={1: "1", 8: "8", 15: "15", 30: "30"}),

                html.Br(),
                html.Label("# Cameras (eMBB UEs)"),
                dcc.Slider(id="n_embb", min=0, max=30, step=1, value=12,
                           marks={0: "0", 12: "12", 20: "20", 30: "30"}),

                html.Br(),
                html.Label("# Sensors (mMTC UEs)"),
                dcc.Slider(id="n_mmtc", min=0, max=50, step=1, value=10,
                           marks={0: "0", 10: "10", 25: "25", 50: "50"}),

                html.Br(),
                html.Label("Random seed"),
                dcc.Input(id="seed", type="number", value=7, min=0, step=1, style={"width": "100%"}),

                html.Br(), html.Br(),
                html.Button("Run Comparison (Baseline vs Smart)", id="run_btn", n_clicks=0,
                            style={"width": "100%", "padding": "10px", "fontWeight": "bold"}),

                html.Br(), html.Br(),
                html.Div([badge("Baseline"), html.Span(" "), badge("Smart Controller"), html.Span(" "), badge("Cost of Safety")]),
            ],
        ),

        # Main view
        html.Div(
            style={"flex": 1, "padding": "16px", "overflowY": "auto"},
            children=[
                html.H2("Baseline vs Smart — Proof of Value"),

                # Row 1: side-by-side KPIs
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                    children=[
                        html.Div(style=card_style(), children=[
                            html.H3("Baseline (no borrowing, no prediction)", style={"marginTop": 0}),
                            html.Div(id="baseline_kpis", style={"display":"flex", "gap":"12px", "flexWrap":"wrap"}),
                        ]),
                        html.Div(style=card_style(), children=[
                            html.H3("Smart (predict + borrow + throttle)", style={"marginTop": 0}),
                            html.Div(id="smart_kpis", style={"display":"flex", "gap":"12px", "flexWrap":"wrap"}),
                        ]),
                    ],
                ),

                html.Br(),

                # Row 2: cost of safety + novelty meter
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                    children=[
                        html.Div(style=card_style(), children=[
                            html.H3("Cost of Safety (Tradeoff)", style={"marginTop": 0}),
                            html.Div(id="cost_box")
                        ]),
                        html.Div(style=card_style(), children=[
                            html.H3("Novelty Meter (What the controller actually did)", style={"marginTop": 0}),
                            html.Div(id="novelty_box", style={"display":"flex", "gap":"12px", "flexWrap":"wrap"})
                        ]),
                    ],
                ),

                html.Br(),

                # Row 3: visuals (factory + gauge) side-by-side baseline vs smart
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                    children=[
                        dcc.Graph(id="fig_factory_base", figure=empty_fig("Baseline Factory View")),
                        dcc.Graph(id="fig_factory_smart", figure=empty_fig("Smart Factory View")),
                    ],
                ),

                html.Br(),

                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                    children=[
                        dcc.Graph(id="fig_risk_base", figure=empty_fig("Baseline Risk Gauge")),
                        dcc.Graph(id="fig_risk_smart", figure=empty_fig("Smart Risk Gauge")),
                    ],
                ),

                html.Br(),

                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                    children=[
                        dcc.Graph(id="fig_donut_base", figure=empty_fig("Baseline PRB Donut")),
                        dcc.Graph(id="fig_donut_smart", figure=empty_fig("Smart PRB Donut")),
                    ],
                ),

                html.Br(),

                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                    children=[
                        dcc.Graph(id="fig_timeline_base", figure=empty_fig("Baseline Timeline")),
                        dcc.Graph(id="fig_timeline_smart", figure=empty_fig("Smart Timeline")),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("baseline_kpis", "children"),
    Output("smart_kpis", "children"),
    Output("cost_box", "children"),
    Output("novelty_box", "children"),
    Output("fig_factory_base", "figure"),
    Output("fig_factory_smart", "figure"),
    Output("fig_risk_base", "figure"),
    Output("fig_risk_smart", "figure"),
    Output("fig_donut_base", "figure"),
    Output("fig_donut_smart", "figure"),
    Output("fig_timeline_base", "figure"),
    Output("fig_timeline_smart", "figure"),
    Input("run_btn", "n_clicks"),
    State("n_urllc", "value"),
    State("n_embb", "value"),
    State("n_mmtc", "value"),
    State("seed", "value"),
    prevent_initial_call=True
)
def run_comparison(n_clicks, n_urllc, n_embb, n_mmtc, seed):
    cfg = SimConfig(
        n_urllc=int(n_urllc),
        n_embb=int(n_embb),
        n_mmtc=int(n_mmtc),
        seed=int(seed) if seed is not None else 7,
    )

    df_base, k_base = run_sim(cfg, mode="baseline")
    df_smart, k_smart = run_sim(cfg, mode="smart")
    nov = novelty_metrics(df_smart, cfg)

    # Side-by-side KPI cards
    base_cards = [
        kpi_box("URLLC Safety", safety_label(k_base["urllc_violation_rate_pct"], k_base["urllc_p95_delay_ms"], k_base["avg_risk"]),
                f"viol={k_base['urllc_violation_rate_pct']:.2f}% | p95={k_base['urllc_p95_delay_ms']:.1f}ms | risk={k_base['avg_risk']:.2f}"),
        kpi_box("Camera Quality", camera_quality(k_base["min_embb_scale"]),
                f"min scale={k_base['min_embb_scale']:.2f}×"),
        kpi_box("Throughput", f"{k_base['total_throughput_mbps']:.1f} Mbps",
                f"eMBB={k_base['embb_throughput_mbps']:.1f} Mbps"),
    ]
    smart_cards = [
        kpi_box("URLLC Safety", safety_label(k_smart["urllc_violation_rate_pct"], k_smart["urllc_p95_delay_ms"], k_smart["avg_risk"]),
                f"viol={k_smart['urllc_violation_rate_pct']:.2f}% | p95={k_smart['urllc_p95_delay_ms']:.1f}ms | risk={k_smart['avg_risk']:.2f}"),
        kpi_box("Camera Quality", camera_quality(k_smart["min_embb_scale"]),
                f"min scale={k_smart['min_embb_scale']:.2f}×"),
        kpi_box("Throughput", f"{k_smart['total_throughput_mbps']:.1f} Mbps",
                f"eMBB={k_smart['embb_throughput_mbps']:.1f} Mbps"),
    ]

    # Cost of Safety (tradeoff)
    # (Smart likely lowers eMBB throughput but improves URLLC safety)
    viol_drop = k_base["urllc_violation_rate_pct"] - k_smart["urllc_violation_rate_pct"]
    embb_drop = k_base["embb_throughput_mbps"] - k_smart["embb_throughput_mbps"]

    cost = html.Div([
        html.Div(f"Safety gain: URLLC violations reduced by {viol_drop:.2f}% points", style={"fontSize":"14px", "marginBottom":"6px"}),
        html.Div(f"Cost: eMBB throughput changed by {(-embb_drop):.2f} Mbps (negative means reduced)", style={"fontSize":"14px", "marginBottom":"6px"}),
        html.Hr(),
        html.Div(
            "Interpretation: Smart mode protects industrial control first. "
            "If needed, it borrows bandwidth and may throttle video to keep machines safe.",
            style={"fontSize":"13px", "color":"#555"}
        )
    ])

    # Novelty Meter (controller actions)
    novelty_cards = [
        kpi_box("Borrowed PRBs", str(int(nov["borrowed_total"])), "Total PRBs borrowed to protect URLLC"),
        kpi_box("Throttle Steps", str(int(nov["throttle_steps"])), "How often congestion control reduced eMBB rate"),
        kpi_box("Time Critical", f"{nov['critical_pct']:.1f}%", "Percent of time risk>0.75"),
        kpi_box("Recovery Time", ("—" if np.isnan(nov["recovery_ms"]) else f"{nov['recovery_ms']:.0f} ms"),
                "Time from first critical risk → recovered"),
    ]

    # Visuals
    fig_factory_base = factory_map(df_base, cfg, "Baseline Factory Floor (no help)")
    fig_factory_smart = factory_map(df_smart, cfg, "Smart Factory Floor (controller active)")

    fig_risk_base = risk_gauge(k_base["avg_risk"])
    fig_risk_smart = risk_gauge(k_smart["avg_risk"])

    fig_donut_base = prb_donut(df_base, "Baseline Bandwidth Allocation (PRBs)")
    fig_donut_smart = prb_donut(df_smart, "Smart Bandwidth Allocation (PRBs)")

    fig_timeline_base = controller_timeline(df_base, "Baseline Control Timeline")
    fig_timeline_smart = controller_timeline(df_smart, "Smart Control Timeline")

    return (
        base_cards,
        smart_cards,
        cost,
        novelty_cards,
        fig_factory_base,
        fig_factory_smart,
        fig_risk_base,
        fig_risk_smart,
        fig_donut_base,
        fig_donut_smart,
        fig_timeline_base,
        fig_timeline_smart,
    )


if __name__ == "__main__":
    app.run(debug=True)