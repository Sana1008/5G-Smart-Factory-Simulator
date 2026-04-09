import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def build_kpi_data(rr_results: dict, qos_results: dict) -> dict:
    return {
        "rr_latency": rr_results["avg_latency_overall"],
        "qos_latency": qos_results["avg_latency_overall"],
        "rr_deadline_miss": rr_results["deadline_miss_rate_overall"] * 100,
        "qos_deadline_miss": qos_results["deadline_miss_rate_overall"] * 100,
        "rr_fairness": rr_results["fairness_index"],
        "qos_fairness": qos_results["fairness_index"],
        "rr_served": rr_results["total_served"],
        "qos_served": qos_results["total_served"],
        "rr_dropped": rr_results["total_dropped"],
        "qos_dropped": qos_results["total_dropped"],
    }


def make_latency_comparison_chart(rr_results: dict, qos_results: dict) -> go.Figure:
    data = [
        {"Scheduler": "Round Robin", "Latency": rr_results["avg_latency_overall"]},
        {"Scheduler": "QoS-Aware", "Latency": qos_results["avg_latency_overall"]},
    ]
    df = pd.DataFrame(data)
    fig = px.bar(df, x="Scheduler", y="Latency", title="Average Latency Comparison")
    fig.update_layout(height=400)
    return fig


def make_urllc_latency_chart(rr_results: dict, qos_results: dict) -> go.Figure:
    data = [
        {
            "Scheduler": "Round Robin",
            "URLLC Latency": rr_results["avg_latency_by_class"].get("URLLC", 0),
        },
        {
            "Scheduler": "QoS-Aware",
            "URLLC Latency": qos_results["avg_latency_by_class"].get("URLLC", 0),
        },
    ]
    df = pd.DataFrame(data)
    fig = px.bar(df, x="Scheduler", y="URLLC Latency", title="URLLC Latency Comparison")
    fig.update_layout(height=400)
    return fig


def make_deadline_miss_chart(rr_results: dict, qos_results: dict) -> go.Figure:
    data = [
        {
            "Scheduler": "Round Robin",
            "Deadline Miss Rate": rr_results["deadline_miss_rate_overall"] * 100,
        },
        {
            "Scheduler": "QoS-Aware",
            "Deadline Miss Rate": qos_results["deadline_miss_rate_overall"] * 100,
        },
    ]
    df = pd.DataFrame(data)
    fig = px.bar(df, x="Scheduler", y="Deadline Miss Rate", title="Deadline Miss Rate (%)")
    fig.update_layout(height=400)
    return fig


def make_urllc_deadline_miss_chart(rr_results: dict, qos_results: dict) -> go.Figure:
    data = [
        {
            "Scheduler": "Round Robin",
            "URLLC Deadline Miss Rate": rr_results["deadline_miss_rate_by_class"].get("URLLC", 0) * 100,
        },
        {
            "Scheduler": "QoS-Aware",
            "URLLC Deadline Miss Rate": qos_results["deadline_miss_rate_by_class"].get("URLLC", 0) * 100,
        },
    ]
    df = pd.DataFrame(data)
    fig = px.bar(df, x="Scheduler", y="URLLC Deadline Miss Rate", title="URLLC Deadline Miss Rate (%)")
    fig.update_layout(height=400)
    return fig


def make_throughput_chart(rr_results: dict, qos_results: dict) -> go.Figure:
    traffic_classes = sorted(
        set(rr_results["throughput_by_class"].keys()) | set(qos_results["throughput_by_class"].keys())
    )

    rows = []
    for traffic_class in traffic_classes:
        rows.append(
            {
                "Traffic Class": traffic_class,
                "Scheduler": "Round Robin",
                "Throughput": rr_results["throughput_by_class"].get(traffic_class, 0),
            }
        )
        rows.append(
            {
                "Traffic Class": traffic_class,
                "Scheduler": "QoS-Aware",
                "Throughput": qos_results["throughput_by_class"].get(traffic_class, 0),
            }
        )

    df = pd.DataFrame(rows)
    fig = px.bar(
        df,
        x="Traffic Class",
        y="Throughput",
        color="Scheduler",
        barmode="group",
        title="Throughput by Traffic Class",
    )
    fig.update_layout(height=450)
    return fig


def make_queue_length_timeseries(results: dict, title: str) -> go.Figure:
    df = pd.DataFrame(results["queue_length_history"])
    fig = go.Figure()

    traffic_columns = [col for col in df.columns if col != "time"]
    for col in traffic_columns:
        fig.add_trace(go.Scatter(x=df["time"], y=df[col], mode="lines", name=col))

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Queue Length",
        height=450,
    )
    return fig


def make_resource_allocation_heatmap(results: dict, title: str) -> go.Figure:
    rows = []
    for item in results["resource_usage_history"]:
        allocation = item["allocation_by_class"]
        row = {"time": item["time"]}
        row.update(allocation)
        rows.append(row)

    df = pd.DataFrame(rows).fillna(0)

    traffic_columns = [col for col in df.columns if col != "time"]
    if not traffic_columns:
        return go.Figure()

    heatmap_df = df.set_index("time")[traffic_columns].T

    fig = px.imshow(
        heatmap_df,
        aspect="auto",
        labels={"x": "Time", "y": "Traffic Class", "color": "Allocated Resources"},
        title=title,
    )
    fig.update_layout(height=450)
    return fig