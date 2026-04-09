from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Packet:
    packet_id: int
    traffic_class: str
    arrival_time: int
    size: int
    deadline: int

    served_time: Optional[int] = None
    dropped: bool = False

    @property
    def waiting_time(self) -> Optional[int]:
        if self.served_time is None:
            return None
        return self.served_time - self.arrival_time

    @property
    def deadline_missed(self) -> bool:
        if self.served_time is None:
            return False
        return (self.served_time - self.arrival_time) > self.deadline

    def mark_served(self, current_time: int) -> None:
        self.served_time = current_time

    def mark_dropped(self) -> None:
        self.dropped = True

    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id,
            "traffic_class": self.traffic_class,
            "arrival_time": self.arrival_time,
            "size": self.size,
            "deadline": self.deadline,
            "served_time": self.served_time,
            "dropped": self.dropped,
            "waiting_time": self.waiting_time,
            "deadline_missed": self.deadline_missed,
        }