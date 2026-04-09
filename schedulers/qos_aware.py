from typing import Dict, List, Optional

from config.simulation_config import CONGESTION_BOOST, PRIORITY_WEIGHTS, TRAFFIC_CLASSES
from schedulers.base_scheduler import BaseScheduler
from simulator.packet import Packet
from simulator.queue_manager import QueueManager


class QoSAwareScheduler(BaseScheduler):
    def __init__(self) -> None:
        super().__init__(name="Adaptive QoS-Aware")
        self.last_scores: Dict[str, float] = {traffic_class: 0.0 for traffic_class in TRAFFIC_CLASSES}

    def schedule(
        self,
        queue_manager: QueueManager,
        available_resources: int,
        current_time: int,
        congestion_state: bool,
    ) -> List[Packet]:
        selected_packets: List[Packet] = []
        remaining_resources = available_resources

        if remaining_resources <= 0:
            return selected_packets

        while remaining_resources > 0:
            traffic_class = self._select_best_queue(
                queue_manager=queue_manager,
                current_time=current_time,
                congestion_state=congestion_state,
                remaining_resources=remaining_resources,
            )

            if traffic_class is None:
                break

            packet = queue_manager.dequeue_packet(traffic_class)
            if packet is None:
                break

            packet.mark_served(current_time)
            selected_packets.append(packet)
            remaining_resources -= packet.size

        return selected_packets

    def _select_best_queue(
        self,
        queue_manager: QueueManager,
        current_time: int,
        congestion_state: bool,
        remaining_resources: int,
    ) -> Optional[str]:
        best_class: Optional[str] = None
        best_score = float("-inf")

        for traffic_class in TRAFFIC_CLASSES:
            packet = queue_manager.peek_packet(traffic_class)

            if packet is None:
                self.last_scores[traffic_class] = 0.0
                continue

            if not self._can_transmit(packet, remaining_resources):
                self.last_scores[traffic_class] = 0.0
                continue

            score = self._compute_score(
                packet=packet,
                traffic_class=traffic_class,
                current_time=current_time,
                queue_manager=queue_manager,
                congestion_state=congestion_state,
            )
            self.last_scores[traffic_class] = score

            if score > best_score:
                best_score = score
                best_class = traffic_class

        return best_class

    def _compute_score(
        self,
        packet: Packet,
        traffic_class: str,
        current_time: int,
        queue_manager: QueueManager,
        congestion_state: bool,
    ) -> float:
        base_priority = float(PRIORITY_WEIGHTS[traffic_class])

        queue_lengths = queue_manager.get_queue_lengths()
        queue_pressure = queue_lengths[traffic_class] * 0.15

        waiting_time = current_time - packet.arrival_time
        waiting_bonus = waiting_time * 0.4

        urgency_ratio = waiting_time / max(packet.deadline, 1)
        urgency_bonus = urgency_ratio * 3.0

        congestion_multiplier = 1.0
        if congestion_state:
            congestion_multiplier = CONGESTION_BOOST[traffic_class]

        score = (base_priority + queue_pressure + waiting_bonus + urgency_bonus) * congestion_multiplier

        if traffic_class == "URLLC":
            if urgency_ratio >= 0.8:
                score += 8.0
            elif urgency_ratio >= 0.5:
                score += 4.0

        return score

    def get_scheduler_stats(self) -> Dict[str, object]:
        return {
            "scheduler_name": self.name,
            "last_scores": self.last_scores.copy(),
        }