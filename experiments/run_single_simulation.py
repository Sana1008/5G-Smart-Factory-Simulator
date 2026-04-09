from schedulers.qos_aware import QoSAwareScheduler
from schedulers.round_robin import RoundRobinScheduler
from simulator.engine import SimulationEngine


def print_summary(title: str, results: dict) -> None:
    print(f"\n=== {title} ===")
    print(f"Scheduler: {results['scheduler_name']}")
    print(f"Scenario: {results.get('scenario_name')}")
    print(f"Total served: {results['total_served']}")
    print(f"Total dropped: {results['total_dropped']}")
    print(f"Average latency overall: {results['avg_latency_overall']:.2f}")
    print(f"Deadline miss rate overall: {results['deadline_miss_rate_overall']:.2%}")
    print(f"Fairness index: {results['fairness_index']:.4f}")

    print("\nAverage latency by class:")
    for traffic_class, value in results["avg_latency_by_class"].items():
        print(f"  {traffic_class}: {value:.2f}")

    print("\nDeadline miss rate by class:")
    for traffic_class, value in results["deadline_miss_rate_by_class"].items():
        print(f"  {traffic_class}: {value:.2%}")

    print("\nThroughput by class:")
    for traffic_class, value in results["throughput_by_class"].items():
        print(f"  {traffic_class}: {value}")


def main() -> None:
    scenario_name = "industrial_congestion"

    rr_engine = SimulationEngine(
        scheduler=RoundRobinScheduler(),
        scenario_name=scenario_name,
    )
    rr_results = rr_engine.run()
    print_summary("Round Robin Results", rr_results)

    qos_engine = SimulationEngine(
        scheduler=QoSAwareScheduler(),
        scenario_name=scenario_name,
    )
    qos_results = qos_engine.run()
    print_summary("QoS-Aware Results", qos_results)


if __name__ == "__main__":
    main()