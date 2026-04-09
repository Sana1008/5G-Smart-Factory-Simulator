from copy import deepcopy
from typing import Dict

from config.simulation_config import ARRIVAL_RATES


SCENARIO_NAMES = [
    "balanced",
    "industrial_congestion",
    "extreme_congestion",
]


SCENARIOS = {
    "balanced": {
        "name": "Balanced Load",
        "description": "Stable traffic with moderate load across all classes.",
        "phases": [
            {
                "start": 0,
                "end": 60,
                "arrival_rates": deepcopy(ARRIVAL_RATES),
            }
        ],
    },
    "industrial_congestion": {
        "name": "Industrial Congestion Spike",
        "description": "Normal operation, congestion spike from cameras and sensors, then recovery.",
        "phases": [
            {
                "start": 0,
                "end": 20,
                "arrival_rates": {
                    "URLLC": 2,
                    "eMBB": 5,
                    "mMTC": 8,
                    "NON_GBR": 3,
                },
            },
            {
                 "start": 20,
                "end": 40,
                "arrival_rates": {
                    "URLLC": 4,
                    "eMBB": 25,
                    "mMTC": 35,
                    "NON_GBR": 12,
                },
            },
            {
                "start": 40,
                "end": 60,
                "arrival_rates": {
                    "URLLC": 2,
                    "eMBB": 6,
                    "mMTC": 10,
                    "NON_GBR": 3,
                },
            },
        ],
    },
    "extreme_congestion": {
        "name": "Extreme Congestion Stress Test",
        "description": "Aggressive overload to produce a dramatic contrast between schedulers.",
        "phases": [
            {
                "start": 0,
                "end": 15,
                "arrival_rates": {
                    "URLLC": 2,
                    "eMBB": 6,
                    "mMTC": 10,
                    "NON_GBR": 4,
                },
            },
            {
                "start": 15,
                "end": 45,
                "arrival_rates": {
                    "URLLC": 4,
                    "eMBB": 20,
                    "mMTC": 30,
                    "NON_GBR": 10,
                },
            },
            {
                "start": 45,
                "end": 60,
                "arrival_rates": {
                    "URLLC": 10,
                    "eMBB": 10,
                    "mMTC": 10,
                    "NON_GBR": 10,
                },
            },
        ],
    },
}


def get_scenario(name: str) -> Dict:
    if name not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{name}'. Available scenarios: {list(SCENARIOS.keys())}"
        )
    return deepcopy(SCENARIOS[name])


def get_arrival_rates_for_time(scenario: Dict, current_time: int) -> Dict[str, int]:
    for phase in scenario["phases"]:
        if phase["start"] <= current_time < phase["end"]:
            return deepcopy(phase["arrival_rates"])

    last_phase = scenario["phases"][-1]
    return deepcopy(last_phase["arrival_rates"])