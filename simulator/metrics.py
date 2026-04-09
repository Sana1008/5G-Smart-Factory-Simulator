from collections import defaultdict
from typing import Dict, List

from simulator.packet import Packet


class MetricsCollector:
    def __init__(self) -> None:
        self.served_packets: List[Packet] = []
        self.dropped_packets: List[Packet] = []
        self.queue_length_history: List[Dict[str, int]] = []
        self.congestion_history: List[Dict[str, object]] = []
        self.resource_usage_history: List[Dict[str, object]] = []

    def record_served_packets(self, packets: List[Packet]) -> None:
        self.served_packets.extend(packets)

    def record_dropped_packets(self, packets: List[Packet]) -> None:
        self.dropped_packets.extend(packets)

    def record_queue_lengths(self, current_time: int, queue_lengths: Dict[str, int]) -> None:
        snapshot = {"time": current_time, **queue_lengths}
        self.queue_length_history.append(snapshot)

    def record_congestion_state(self, current_time: int, congestion_details: Dict[str, object]) -> None:
        snapshot = {"time": current_time, **congestion_details}
        self.congestion_history.append(snapshot)

    def record_resource_usage(
        self,
        current_time: int,
        scheduler_name: str,
        total_resources: int,
        used_resources: int,
        served_packets: List[Packet],
    ) -> None:
        by_class = defaultdict(int)
        for packet in served_packets:
            by_class[packet.traffic_class] += packet.size

        self.resource_usage_history.append(
            {
                "time": current_time,
                "scheduler": scheduler_name,
                "total_resources": total_resources,
                "used_resources": used_resources,
                "unused_resources": total_resources - used_resources,
                "resource_usage_ratio": used_resources / total_resources if total_resources > 0 else 0.0,
                "allocation_by_class": dict(by_class),
            }
        )

    def get_summary(self) -> Dict[str, object]:
        served_by_class = self._group_packets_by_class(self.served_packets)
        dropped_by_class = self._group_packets_by_class(self.dropped_packets)

        avg_latency_by_class = {
            traffic_class: self._average_latency(packets)
            for traffic_class, packets in served_by_class.items()
        }

        deadline_miss_rate_by_class = {
            traffic_class: self._deadline_miss_rate(packets)
            for traffic_class, packets in served_by_class.items()
        }

        throughput_by_class = {
            traffic_class: self._throughput(packets)
            for traffic_class, packets in served_by_class.items()
        }

        drop_rate_by_class = self._drop_rate_by_class(served_by_class, dropped_by_class)

        fairness_index = self._jains_fairness_index(throughput_by_class)

        return {
            "total_served": len(self.served_packets),
            "total_dropped": len(self.dropped_packets),
            "avg_latency_overall": self._average_latency(self.served_packets),
            "deadline_miss_rate_overall": self._deadline_miss_rate(self.served_packets),
            "avg_latency_by_class": avg_latency_by_class,
            "deadline_miss_rate_by_class": deadline_miss_rate_by_class,
            "throughput_by_class": throughput_by_class,
            "drop_rate_by_class": drop_rate_by_class,
            "fairness_index": fairness_index,
            "served_packets": [packet.to_dict() for packet in self.served_packets],
            "dropped_packets": [packet.to_dict() for packet in self.dropped_packets],
            "queue_length_history": self.queue_length_history,
            "congestion_history": self.congestion_history,
            "resource_usage_history": self.resource_usage_history,
        }

    def _group_packets_by_class(self, packets: List[Packet]) -> Dict[str, List[Packet]]:
        grouped: Dict[str, List[Packet]] = defaultdict(list)
        for packet in packets:
            grouped[packet.traffic_class].append(packet)
        return dict(grouped)

    def _average_latency(self, packets: List[Packet]) -> float:
        latencies = [
            packet.waiting_time
            for packet in packets
            if packet.waiting_time is not None
        ]
        if not latencies:
            return 0.0
        return sum(latencies) / len(latencies)

    def _deadline_miss_rate(self, packets: List[Packet]) -> float:
        if not packets:
            return 0.0
        missed = sum(1 for packet in packets if packet.deadline_missed)
        return missed / len(packets)

    def _throughput(self, packets: List[Packet]) -> int:
        return sum(packet.size for packet in packets)

    def _drop_rate_by_class(
        self,
        served_by_class: Dict[str, List[Packet]],
        dropped_by_class: Dict[str, List[Packet]],
    ) -> Dict[str, float]:
        all_classes = set(served_by_class.keys()) | set(dropped_by_class.keys())
        drop_rates: Dict[str, float] = {}

        for traffic_class in all_classes:
            served_count = len(served_by_class.get(traffic_class, []))
            dropped_count = len(dropped_by_class.get(traffic_class, []))
            total = served_count + dropped_count

            drop_rates[traffic_class] = dropped_count / total if total > 0 else 0.0

        return drop_rates

    def _jains_fairness_index(self, throughput_by_class: Dict[str, int]) -> float:
        values = list(throughput_by_class.values())

        if not values:
            return 0.0

        numerator = sum(values) ** 2
        denominator = len(values) * sum(value ** 2 for value in values)

        if denominator == 0:
            return 0.0

        return numerator / denominator