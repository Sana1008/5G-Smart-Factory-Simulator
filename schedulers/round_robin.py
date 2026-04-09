from typing import List

from config.simulation_config import TRAFFIC_CLASSES
from schedulers.base_scheduler import BaseScheduler
from simulator.packet import Packet
from simulator.queue_manager import QueueManager


class RoundRobinScheduler(BaseScheduler):
    def __init__(self) -> None:
        super().__init__(name="Round Robin")
        self.last_served_index = -1

    def schedule(
        self,
        queue_manager: QueueManager,
        available_resources: int,
        current_time: int,
        congestion_state: bool,
    ) -> List[Packet]:
        selected_packets: List[Packet] = []
        remaining_resources = available_resources
        class_count = len(TRAFFIC_CLASSES)

        if class_count == 0 or remaining_resources <= 0:
            return selected_packets

        made_progress = True

        while remaining_resources > 0 and made_progress:
            made_progress = False

            for offset in range(class_count):
                class_index = (self.last_served_index + 1 + offset) % class_count
                traffic_class = TRAFFIC_CLASSES[class_index]

                packet = queue_manager.peek_packet(traffic_class)
                if packet is None:
                    continue

                if not self._can_transmit(packet, remaining_resources):
                    continue

                packet = queue_manager.dequeue_packet(traffic_class)
                if packet is None:
                    continue

                packet.mark_served(current_time)
                selected_packets.append(packet)
                remaining_resources -= packet.size
                self.last_served_index = class_index
                made_progress = True

                if remaining_resources <= 0:
                    break

        return selected_packets