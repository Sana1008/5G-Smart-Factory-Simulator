from typing import Dict, Optional

from config.scenarios import get_arrival_rates_for_time, get_scenario
from config.simulation_config import RANDOM_SEED, SIMULATION_TIME, TOTAL_RESOURCES
from simulator.congestion_monitor import CongestionMonitor
from simulator.metrics import MetricsCollector
from simulator.queue_manager import QueueManager
from simulator.traffic_generator import TrafficGenerator


class SimulationEngine:
    def __init__(
        self,
        scheduler,
        simulation_time: int = SIMULATION_TIME,
        total_resources: int = TOTAL_RESOURCES,
        random_seed: int = RANDOM_SEED,
        arrival_rates: Optional[Dict[str, int]] = None,
        scenario_name: Optional[str] = None,
    ) -> None:
        self.scheduler = scheduler
        self.simulation_time = simulation_time
        self.total_resources = total_resources
        self.arrival_rates = arrival_rates
        self.scenario_name = scenario_name
        self.scenario = get_scenario(scenario_name) if scenario_name else None

        self.traffic_generator = TrafficGenerator(random_seed=random_seed)
        self.queue_manager = QueueManager()
        self.congestion_monitor = CongestionMonitor()
        self.metrics = MetricsCollector()

        self.current_time = 0
        self._last_recorded_drop_count = 0

    def run(self) -> Dict[str, object]:
        for current_time in range(self.simulation_time):
            self.current_time = current_time

            active_arrival_rates = self._get_active_arrival_rates(current_time)

            new_packets = self.traffic_generator.generate_packets(
                current_time=current_time,
                arrival_rates=active_arrival_rates,
            )
            self.queue_manager.enqueue_packets(new_packets)

            self._record_new_drops()

            congestion_details = self.congestion_monitor.get_congestion_details(
                self.queue_manager
            )
            congestion_state = bool(congestion_details["is_congested"])

            served_packets = self.scheduler.schedule(
                queue_manager=self.queue_manager,
                available_resources=self.total_resources,
                current_time=current_time,
                congestion_state=congestion_state,
            )

            used_resources = sum(packet.size for packet in served_packets)

            self.metrics.record_served_packets(served_packets)
            self.metrics.record_queue_lengths(
                current_time=current_time,
                queue_lengths=self.queue_manager.get_queue_lengths(),
            )
            self.metrics.record_congestion_state(
                current_time=current_time,
                congestion_details=congestion_details,
            )
            self.metrics.record_resource_usage(
                current_time=current_time,
                scheduler_name=self.scheduler.get_display_name(),
                total_resources=self.total_resources,
                used_resources=used_resources,
                served_packets=served_packets,
            )

        self._finalize_remaining_packets()

        results = self.metrics.get_summary()
        results["scheduler_name"] = self.scheduler.get_display_name()
        results["simulation_time"] = self.simulation_time
        results["total_resources"] = self.total_resources
        results["scenario_name"] = self.scenario_name

        if self.scenario:
            results["scenario"] = self.scenario

        return results

    def _get_active_arrival_rates(self, current_time: int) -> Dict[str, int]:
        if self.arrival_rates is not None:
            return self.arrival_rates

        if self.scenario is not None:
            return get_arrival_rates_for_time(self.scenario, current_time)

        return None

    def _record_new_drops(self) -> None:
        current_drop_count = len(self.queue_manager.dropped_packets)

        if current_drop_count > self._last_recorded_drop_count:
            new_drops = self.queue_manager.dropped_packets[
                self._last_recorded_drop_count:current_drop_count
            ]
            self.metrics.record_dropped_packets(new_drops)
            self._last_recorded_drop_count = current_drop_count

    def _finalize_remaining_packets(self) -> None:
        return