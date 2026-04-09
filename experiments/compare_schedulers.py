from schedulers.qos_aware import QoSAwareScheduler
from schedulers.round_robin import RoundRobinScheduler
from simulator.engine import SimulationEngine


def compare_results(rr: dict, qos: dict) -> None:
    print("\n========= COMPARISON =========")

    print("\n--- Overall Metrics ---")
    print(f"Latency (RR):  {rr['avg_latency_overall']:.2f}")
    print(f"Latency (QoS): {qos['avg_latency_overall']:.2f}")

    print(f"Deadline Miss (RR):  {rr['deadline_miss_rate_overall']:.2%}")
    print(f"Deadline Miss (QoS): {qos['deadline_miss_rate_overall']:.2%}")

    print(f"Throughput (RR):  {sum(rr['throughput_by_class'].values())}")
    print(f"Throughput (QoS): {sum(qos['throughput_by_class'].values())}")

    print(f"Fairness (RR):  {rr['fairness_index']:.4f}")
    print(f"Fairness (QoS): {qos['fairness_index']:.4f}")

    print("\n--- URLLC Focus (MOST IMPORTANT) ---")
    print(f"URLLC Latency (RR):  {rr['avg_latency_by_class'].get('URLLC', 0):.2f}")
    print(f"URLLC Latency (QoS): {qos['avg_latency_by_class'].get('URLLC', 0):.2f}")

    print(f"URLLC Deadline Miss (RR):  {rr['deadline_miss_rate_by_class'].get('URLLC', 0):.2%}")
    print(f"URLLC Deadline Miss (QoS): {qos['deadline_miss_rate_by_class'].get('URLLC', 0):.2%}")


def main() -> None:
    scenario_name = "industrial_congestion"

    print(f"\nRunning scenario: {scenario_name}")

    rr_engine = SimulationEngine(
        scheduler=RoundRobinScheduler(),
        scenario_name=scenario_name,
    )
    rr_results = rr_engine.run()

    qos_engine = SimulationEngine(
        scheduler=QoSAwareScheduler(),
        scenario_name=scenario_name,
    )
    qos_results = qos_engine.run()

    compare_results(rr_results, qos_results)


if __name__ == "__main__":
    main()