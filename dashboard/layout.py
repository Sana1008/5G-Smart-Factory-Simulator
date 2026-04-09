from dash import dcc, html


def build_metric_card(card_id: str, title: str) -> html.Div:
    return html.Div(
        className="metric-card",
        children=[
            html.Div(title, className="metric-card-title"),
            html.Div(id=card_id, className="metric-card-value"),
        ],
    )


def create_layout() -> html.Div:
    return html.Div(
        className="app-shell",
        children=[
            html.Div(
                className="app-header",
                children=[
                    html.H1("FactoryNet 5G Simulator", className="app-title"),
                    html.P(
                        "QoS-Driven Resource Management for Industrial 5G Networks",
                        className="app-subtitle",
                    ),
                ],
            ),
            html.Div(
                className="control-panel",
                children=[
                    html.Div(
                        className="control-group",
                        children=[
                            html.Label("Scenario", className="control-label"),
                            dcc.Dropdown(
                                id="scenario-dropdown",
                                options=[
                                    {"label": "Balanced Load", "value": "balanced"},
                                    {
                                        "label": "Industrial Congestion",
                                        "value": "industrial_congestion",
                                    },
                                    {
                                        "label": "Extreme Congestion",
                                        "value": "extreme_congestion",
                                    },
                                ],
                                value="industrial_congestion",
                                clearable=False,
                            ),
                        ],
                    ),
                    html.Div(
                        className="control-group",
                        children=[
                            html.Label("Run Comparison", className="control-label"),
                            html.Button(
                                "Simulate",
                                id="run-button",
                                n_clicks=0,
                                className="run-button",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="kpi-grid",
                children=[
                    build_metric_card("rr-latency-card", "RR Avg Latency"),
                    build_metric_card("qos-latency-card", "QoS Avg Latency"),
                    build_metric_card("rr-urllc-latency-card", "RR URLLC Latency"),
                    build_metric_card("qos-urllc-latency-card", "QoS URLLC Latency"),
                    build_metric_card("rr-miss-card", "RR Deadline Miss"),
                    build_metric_card("qos-miss-card", "QoS Deadline Miss"),
                    build_metric_card("rr-drop-card", "RR Drops"),
                    build_metric_card("qos-drop-card", "QoS Drops"),
                ],
            ),
            html.Div(
                className="chart-grid",
                children=[
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="latency-comparison-chart")],
                    ),
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="urllc-latency-chart")],
                    ),
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="deadline-miss-chart")],
                    ),
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="urllc-deadline-miss-chart")],
                    ),
                    html.Div(
                        className="chart-card chart-card-wide",
                        children=[dcc.Graph(id="throughput-chart")],
                    ),
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="rr-queue-chart")],
                    ),
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="qos-queue-chart")],
                    ),
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="rr-heatmap-chart")],
                    ),
                    html.Div(
                        className="chart-card",
                        children=[dcc.Graph(id="qos-heatmap-chart")],
                    ),
                ],
            ),
            dcc.Store(id="comparison-results-store"),
        ],
    )