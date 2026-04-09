from collections import deque
from typing import Deque, Dict, List, Optional

from config.simulation_config import QUEUE_LIMITS, TRAFFIC_CLASSES
from simulator.packet import Packet


class QueueManager:
    def __init__(self) -> None:
        self.queues: Dict[str, Deque[Packet]] = {
            traffic_class: deque() for traffic_class in TRAFFIC_CLASSES
        }
        self.dropped_packets: List[Packet] = []

    def enqueue_packets(self, packets: List[Packet]) -> None:
        for packet in packets:
            self.enqueue_packet(packet)

    def enqueue_packet(self, packet: Packet) -> bool:
        queue = self.queues[packet.traffic_class]
        queue_limit = QUEUE_LIMITS[packet.traffic_class]

        if len(queue) >= queue_limit:
            packet.mark_dropped()
            self.dropped_packets.append(packet)
            return False

        queue.append(packet)
        return True

    def dequeue_packet(self, traffic_class: str) -> Optional[Packet]:
        queue = self.queues[traffic_class]
        if not queue:
            return None
        return queue.popleft()

    def peek_packet(self, traffic_class: str) -> Optional[Packet]:
        queue = self.queues[traffic_class]
        if not queue:
            return None
        return queue[0]

    def get_queue(self, traffic_class: str) -> Deque[Packet]:
        return self.queues[traffic_class]

    def get_all_queues(self) -> Dict[str, Deque[Packet]]:
        return self.queues

    def get_queue_lengths(self) -> Dict[str, int]:
        return {
            traffic_class: len(queue)
            for traffic_class, queue in self.queues.items()
        }

    def get_total_queue_length(self) -> int:
        return sum(len(queue) for queue in self.queues.values())

    def is_empty(self) -> bool:
        return all(len(queue) == 0 for queue in self.queues.values())

    def clear(self) -> None:
        for queue in self.queues.values():
            queue.clear()
        self.dropped_packets.clear()