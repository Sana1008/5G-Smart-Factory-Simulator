import random
from typing import Dict, List

from config.simulation_config import ARRIVAL_RATES, DEADLINES, PACKET_SIZES
from simulator.packet import Packet


class TrafficGenerator:
    def __init__(self, random_seed: int = 42) -> None:
        self.packet_counter = 0
        random.seed(random_seed)

    def generate_packets(self, current_time: int, arrival_rates: Dict[str, int] = None) -> List[Packet]:
        rates = arrival_rates if arrival_rates is not None else ARRIVAL_RATES
        packets: List[Packet] = []

        for traffic_class, rate in rates.items():
            num_packets = self._sample_packet_count(rate)

            for _ in range(num_packets):
                packet = Packet(
                    packet_id=self.packet_counter,
                    traffic_class=traffic_class,
                    arrival_time=current_time,
                    size=PACKET_SIZES[traffic_class],
                    deadline=DEADLINES[traffic_class],
                )
                packets.append(packet)
                self.packet_counter += 1

        return packets

    def _sample_packet_count(self, rate: int) -> int:
        lower_bound = max(0, rate - 1)
        upper_bound = rate + 1
        return random.randint(lower_bound, upper_bound)