# config/simulation_config.py

# ===============================
# Simulation Settings
# ===============================
SIMULATION_TIME = 60          # total time (seconds)
TIME_SLOT = 1                 # each step (ms or abstract unit)
RANDOM_SEED = 42

# ===============================
# Network Capacity
# ===============================
TOTAL_RESOURCES = 40         # total resource units per time slot

# ===============================
# Traffic Classes
# ===============================
TRAFFIC_CLASSES = ["URLLC", "eMBB", "mMTC", "NON_GBR"]

# ===============================
# Arrival Rates (packets per time slot)
# (base rates - will change in scenarios)
# ===============================
ARRIVAL_RATES = {
    "URLLC": 2,
    "eMBB": 5,
    "mMTC": 8,
    "NON_GBR": 3
}

# ===============================
# Packet Sizes (resource units)
# ===============================
PACKET_SIZES = {
    "URLLC": 2,
    "eMBB": 8,
    "mMTC": 1,
    "NON_GBR": 4
}

# ===============================
# Latency Deadlines (time units)
# ===============================
DEADLINES = {
    "URLLC": 3,
    "eMBB": 20,
    "mMTC": 50,
    "NON_GBR": 100
}

# ===============================
# Queue Limits (to simulate drops)
# ===============================
QUEUE_LIMITS = {
    "URLLC": 50,
    "eMBB": 100,
    "mMTC": 200,
    "NON_GBR": 100
}

# ===============================
# Scheduler Priorities (QoS-aware)
# Higher = more priority
# ===============================
PRIORITY_WEIGHTS = {
    "URLLC": 4,
    "eMBB": 3,
    "mMTC": 2,
    "NON_GBR": 1
}

# ===============================
# Congestion Detection
# ===============================
CONGESTION_THRESHOLD = 80   # total packets in system

# ===============================
# Adaptive Behavior (QoS Scheduler)
# ===============================
CONGESTION_BOOST = {
    "URLLC": 2.0,
    "eMBB": 0.7,
    "mMTC": 1.2,
    "NON_GBR": 0.5
}