from dash import Input, Output, State, no_update

from dashboard.components import format_integer, format_latency, format_percentage
from dashboard.plots import (
    build_kpi_data,
    make_deadline_miss_chart,
    make_latency_comparison_chart,
    make_queue_length_timeseries,
    make_resource_allocation_heatmap,
    make_throughput_chart,
    make_urllc_deadline_miss_chart,
    make_urllc_latency_chart,
)
from schedulers.qos_aware import QoSAwareScheduler
from schedulers.round_robin import RoundRobinScheduler
from simulator.engine import SimulationEngine


def register_callbacks(app) -> None:
    @app.callback(
        Output("comparison-results-store", "data"),
        Input("run-button", "n_clicks"),
        State("scenario-dropdown", "value"),
        prevent_initial_call=True,
    )
    def run_simulation_comparison(n_clicks: int, scenario_name: str):
        if not n_clicks:
            return no_update

        rr_results = SimulationEngine(
            scheduler=RoundRobinScheduler(),
            scenario_name=scenario_name,
        ).run()

        qos_results = SimulationEngine(
            scheduler=QoSAwareScheduler(),
            scenario_name=scenario_name,
        ).run()

        return {
            "rr_results": rr_results,
            "qos_results": qos_results,
        }

    @app.callback(
        Output("rr-latency-card", "children"),
        Output("qos-latency-card", "children"),
        Output("rr-urllc-latency-card", "children"),
        Output("qos-urllc-latency-card", "children"),
        Output("rr-miss-card", "children"),
        Output("qos-miss-card", "children"),
        Output("rr-drop-card", "children"),
        Output("qos-drop-card", "children"),
        Output("latency-comparison-chart", "figure"),
        Output("urllc-latency-chart", "figure"),
        Output("deadline-miss-chart", "figure"),
        Output("urllc-deadline-miss-chart", "figure"),
        Output("throughput-chart", "figure"),
        Output("rr-queue-chart", "figure"),
        Output("qos-queue-chart", "figure"),
        Output("rr-heatmap-chart", "figure"),
        Output("qos-heatmap-chart", "figure"),
        Input("comparison-results-store", "data"),
        prevent_initial_call=False,
    )
    def update_dashboard(comparison_data):
        if not comparison_data:
            return (
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                {},
                {},
                {},
                {},
                {},
                {},
                {},
                {},
                {},
            )

        rr_results = comparison_data["rr_results"]
        qos_results = comparison_data["qos_results"]

        kpi = build_kpi_data(rr_results, qos_results)

        rr_latency = format_latency(kpi["rr_latency"])
        qos_latency = format_latency(kpi["qos_latency"])

        rr_urllc_latency = format_latency(
            rr_results["avg_latency_by_class"].get("URLLC", 0.0)
        )
        qos_urllc_latency = format_latency(
            qos_results["avg_latency_by_class"].get("URLLC", 0.0)
        )

        rr_miss = format_percentage(kpi["rr_deadline_miss"])
        qos_miss = format_percentage(kpi["qos_deadline_miss"])

        rr_drop = format_integer(kpi["rr_dropped"])
        qos_drop = format_integer(kpi["qos_dropped"])

        latency_fig = make_latency_comparison_chart(rr_results, qos_results)
        urllc_latency_fig = make_urllc_latency_chart(rr_results, qos_results)
        miss_fig = make_deadline_miss_chart(rr_results, qos_results)
        urllc_miss_fig = make_urllc_deadline_miss_chart(rr_results, qos_results)
        throughput_fig = make_throughput_chart(rr_results, qos_results)

        rr_queue_fig = make_queue_length_timeseries(
            rr_results,
            "Round Robin Queue Length Over Time",
        )
        qos_queue_fig = make_queue_length_timeseries(
            qos_results,
            "QoS-Aware Queue Length Over Time",
        )

        rr_heatmap_fig = make_resource_allocation_heatmap(
            rr_results,
            "Round Robin Resource Allocation Heatmap",
        )
        qos_heatmap_fig = make_resource_allocation_heatmap(
            qos_results,
            "QoS-Aware Resource Allocation Heatmap",
        )

        return (
            rr_latency,
            qos_latency,
            rr_urllc_latency,
            qos_urllc_latency,
            rr_miss,
            qos_miss,
            rr_drop,
            qos_drop,
            latency_fig,
            urllc_latency_fig,
            miss_fig,
            urllc_miss_fig,
            throughput_fig,
            rr_queue_fig,
            qos_queue_fig,
            rr_heatmap_fig,
            qos_heatmap_fig,
        )