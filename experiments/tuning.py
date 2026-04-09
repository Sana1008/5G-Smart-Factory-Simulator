from schedulers.qos_aware import QoSAwareScheduler
from schedulers.round_robin import RoundRobinScheduler
from simulator.engine import SimulationEngine


def run_comparison_for_scenario(scenario_name: str) -> None:
    rr_results = SimulationEngine(
        scheduler=RoundRobinScheduler(),
        scenario_name=scenario_name,
    ).run()

    qos_results = SimulationEngine(
        scheduler=QoSAwareScheduler(),
        scenario_name=scenario_name,
    ).run()

    print(f"\n=== Scenario: {scenario_name} ===")
    print(f"RR  URLLC Latency: {rr_results['avg_latency_by_class'].get('URLLC', 0):.2f}")
    print(f"QoS URLLC Latency: {qos_results['avg_latency_by_class'].get('URLLC', 0):.2f}")
    print(f"RR  URLLC Miss: {rr_results['deadline_miss_rate_by_class'].get('URLLC', 0):.2%}")
    print(f"QoS URLLC Miss: {qos_results['deadline_miss_rate_by_class'].get('URLLC', 0):.2%}")
    print(f"RR  Overall Latency: {rr_results['avg_latency_overall']:.2f}")
    print(f"QoS Overall Latency: {qos_results['avg_latency_overall']:.2f}")


def main() -> None:
    for scenario_name in [
        "balanced",
        "industrial_congestion",
        "extreme_congestion",
    ]:
        run_comparison_for_scenario(scenario_name)


if __name__ == "__main__":
    main()