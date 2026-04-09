from typing import Dict

from config.simulation_config import CONGESTION_THRESHOLD
from simulator.queue_manager import QueueManager


class CongestionMonitor:
    def __init__(self, threshold: int = CONGESTION_THRESHOLD) -> None:
        self.threshold = threshold

    def is_congested(self, queue_manager: QueueManager) -> bool:
        total_queue_length = queue_manager.get_total_queue_length()
        return total_queue_length >= self.threshold

    def get_congestion_details(self, queue_manager: QueueManager) -> Dict[str, object]:
        queue_lengths = queue_manager.get_queue_lengths()
        total_queue_length = queue_manager.get_total_queue_length()
        congestion_state = total_queue_length >= self.threshold

        return {
            "is_congested": congestion_state,
            "threshold": self.threshold,
            "total_queue_length": total_queue_length,
            "queue_lengths": queue_lengths,
            "utilization_ratio": total_queue_length / self.threshold if self.threshold > 0 else 0.0,
        }

    def update_threshold(self, new_threshold: int) -> None:
        self.threshold = new_threshold