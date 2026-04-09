from abc import ABC, abstractmethod
from typing import Dict, List

from simulator.packet import Packet
from simulator.queue_manager import QueueManager


class BaseScheduler(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def schedule(
        self,
        queue_manager: QueueManager,
        available_resources: int,
        current_time: int,
        congestion_state: bool,
    ) -> List[Packet]:
        """
        Select packets to transmit in the current time slot.

        Returns:
            List[Packet]: packets chosen for transmission
        """
        raise NotImplementedError

    def _can_transmit(self, packet: Packet, remaining_resources: int) -> bool:
        return packet.size <= remaining_resources

    def _build_result(self, selected_packets: List[Packet], current_time: int) -> List[Packet]:
        for packet in selected_packets:
            packet.mark_served(current_time)
        return selected_packets

    def get_display_name(self) -> str:
        return self.name

    def get_scheduler_stats(self) -> Dict[str, str]:
        return {"scheduler_name": self.name}