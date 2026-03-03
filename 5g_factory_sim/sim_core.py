# sim_core.py
from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from typing import Dict, List, Deque, Any, Tuple, Optional
import random
import pandas as pd
import numpy as np


# -------------------------
# QoS definitions
# -------------------------

@dataclass(frozen=True)
class QosClass:
    name: str
    delay_budget_ms: float
    pkt_size_bytes: int


URLLC = QosClass("URLLC", delay_budget_ms=10.0, pkt_size_bytes=128)
EMBB  = QosClass("eMBB",  delay_budget_ms=120.0, pkt_size_bytes=1400)
MMTC  = QosClass("mMTC",  delay_budget_ms=800.0, pkt_size_bytes=40)


# -------------------------
# Packet / Flow
# -------------------------

@dataclass
class Packet:
    pkt_id: int
    flow_id: str
    ue_id: int
    qos: QosClass
    slice_name: str
    size_bytes: int
    enqueue_tti: int


@dataclass
class Flow:
    flow_id: str
    ue_id: int
    qos: QosClass
    slice_name: str

    kind: str               # "periodic" or "cbr"
    period_ms: int = 20
    cbr_mbps: float = 10.0

    queue: Deque[Packet] = field(default_factory=deque)
    last_scheduled_tti: int = -10_000_000


# -------------------------
# Channel model (simple)
# -------------------------

class SimpleChannel:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def cqi(self, ue_id: int) -> int:
        x = int(round(self.rng.gauss(9, 3)))
        return max(1, min(15, x))

    def bytes_per_prb(self, cqi: int) -> int:
        eff = (cqi / 15.0) ** 1.3
        return int(180 * eff)


# -------------------------
# Traffic generation
# -------------------------

class TrafficGen:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.next_pkt_id = 1

    def generate(
        self,
        flows: List[Flow],
        tti: int,
        tti_ms: float,
        trace_rows: List[Dict[str, Any]],
        embb_rate_scale: float,
    ):
        time_ms = tti * tti_ms
        for f in flows:
            if f.kind == "periodic":
                if (time_ms % f.period_ms) < 1e-9:
                    self._enqueue(f, tti, trace_rows)
            elif f.kind == "cbr":
                offered_mbps = f.cbr_mbps * embb_rate_scale
                bytes_per_ms = (offered_mbps * 1_000_000 / 8) / 1000.0
                budget = bytes_per_ms * tti_ms
                while budget >= f.qos.pkt_size_bytes:
                    budget -= f.qos.pkt_size_bytes
                    self._enqueue(f, tti, trace_rows)

    def _enqueue(self, f: Flow, tti: int, trace_rows: List[Dict[str, Any]]):
        pkt = Packet(
            pkt_id=self.next_pkt_id,
            flow_id=f.flow_id,
            ue_id=f.ue_id,
            qos=f.qos,
            slice_name=f.slice_name,
            size_bytes=f.qos.pkt_size_bytes,
            enqueue_tti=tti,
        )
        self.next_pkt_id += 1
        f.queue.append(pkt)
        trace_rows.append({
            "tti": tti,
            "event": "enqueue",
            "pkt_id": pkt.pkt_id,
            "flow_id": pkt.flow_id,
            "ue_id": pkt.ue_id,
            "slice": pkt.slice_name,
            "qos": pkt.qos.name,
            "pkt_size_bytes": pkt.size_bytes,
            "hol_delay_ms": 0.0,
            "allocated_prbs": 0,
            "cqi": None,
            "tx_bytes": 0,
        })


# -------------------------
# Controller / policy
# -------------------------

@dataclass
class PolicyConfig:
    # These are NOT user-controlled (report knobs)
    base_url_share: float = 0.25
    base_embb_share: float = 0.60
    base_mmtc_share: float = 0.15

    max_url_share: float = 0.70
    min_embb_share: float = 0.10
    min_mmtc_share: float = 0.05

    # throttle bounds
    embb_min_scale: float = 0.2


@dataclass
class ControllerState:
    total_prbs: int
    policy: PolicyConfig = field(default_factory=PolicyConfig)

    ewma_url_hol: float = 0.0
    ewma_url_backlog_bytes: float = 0.0
    embb_scale: float = 1.0

    def _compute_risk(
        self,
        flows: List[Flow],
        ue_cqi: Dict[int, int],
        channel: SimpleChannel,
        tti: int,
        tti_ms: float,
        base_url_prbs: int
    ) -> Tuple[float, float, float]:
        # URLLC HOL max + backlog
        urllc_flows = [f for f in flows if f.slice_name == "S_URLLC"]
        hols = []
        backlog = 0
        for f in urllc_flows:
            if f.queue:
                hols.append((tti - f.queue[0].enqueue_tti) * tti_ms)
                backlog += sum(p.size_bytes for p in f.queue)
        hol_max = max(hols) if hols else 0.0

        # EWMA
        beta = 0.05
        self.ewma_url_hol = (1 - beta) * self.ewma_url_hol + beta * hol_max
        self.ewma_url_backlog_bytes = (1 - beta) * self.ewma_url_backlog_bytes + beta * backlog

        # avg bytes/prb for URLLC
        ues = [f.ue_id for f in urllc_flows]
        if ues:
            avg_bpp = float(np.mean([channel.bytes_per_prb(ue_cqi[u]) for u in ues]))
            avg_bpp = max(1.0, avg_bpp)
        else:
            avg_bpp = 80.0

        # predict drain time if base_url_prbs is used
        service_bytes_per_tti = max(1.0, base_url_prbs * avg_bpp)
        predicted_wait_ms = (self.ewma_url_backlog_bytes / service_bytes_per_tti) * tti_ms
        predicted_total_ms = self.ewma_url_hol + predicted_wait_ms

        budget = URLLC.delay_budget_ms
        risk = min(1.0, max(0.0, (predicted_total_ms - 0.6 * budget) / (0.4 * budget)))
        return risk, predicted_total_ms, avg_bpp

    def step(self, mode: str, flows: List[Flow], ue_cqi: Dict[int, int], channel: SimpleChannel,
             tti: int, tti_ms: float) -> Dict[str, Any]:
        """
        mode: 'baseline' or 'smart'
        Returns: controller record including budgets/risk/actions
        """
        p = self.policy

        # base budgets
        bU = int(round(self.total_prbs * p.base_url_share))
        bE = int(round(self.total_prbs * p.base_embb_share))
        bM = self.total_prbs - bU - bE

        risk, predicted_total_ms, _ = self._compute_risk(
            flows, ue_cqi, channel, tti, tti_ms, base_url_prbs=bU
        )

        borrowed = 0
        throttle_step = 0
        event = "NORMAL"

        if risk > 0.25:
            event = "RISK_PREDICTED"

        if mode == "smart":
            # borrowing
            extra_max = int(round(p.max_url_share * self.total_prbs)) - bU
            extra = int(round(risk * max(0, extra_max)))
            if extra > 0:
                minE = int(round(p.min_embb_share * self.total_prbs))
                minM = int(round(p.min_mmtc_share * self.total_prbs))

                stealE = min(extra, max(0, bE - minE))
                bE -= stealE
                bU += stealE
                extra -= stealE
                borrowed += stealE

                stealM = min(extra, max(0, bM - minM))
                bM -= stealM
                bU += stealM
                extra -= stealM
                borrowed += stealM

            if borrowed > 0:
                event = "BORROWING"

            # predictive congestion control (throttle eMBB if risk high)
            prev_scale = self.embb_scale
            if risk > 0.7:
                self.embb_scale = max(p.embb_min_scale, self.embb_scale * 0.97)
            elif risk < 0.2:
                self.embb_scale = min(1.0, self.embb_scale + 0.01)

            if self.embb_scale < prev_scale - 1e-9:
                throttle_step = 1
                event = "EMBB_THROTTLE"

            if risk < 0.15 and borrowed == 0 and self.embb_scale > 0.95:
                event = "RECOVERY"
        else:
            # baseline: no borrowing, no throttling
            self.embb_scale = 1.0

        budgets = {"S_URLLC": int(bU), "S_EMBB": int(bE), "S_MMTC": int(bM)}
        return {
            "tti": tti,
            "event": "controller",
            "mode": mode,
            "risk": float(risk),
            "predicted_total_ms": float(predicted_total_ms),
            "embb_scale": float(self.embb_scale),
            "controller_event": event,
            "borrowed_prbs": int(borrowed),
            "throttle_step": int(throttle_step),
            "bud_url": budgets["S_URLLC"],
            "bud_embb": budgets["S_EMBB"],
            "bud_mmtc": budgets["S_MMTC"],
        }, budgets


# -------------------------
# Scheduler (budgets are dynamic)
# -------------------------

def qos_slice_scheduler(
    flows: List[Flow],
    slice_budgets: Dict[str, int],
    ue_cqi: Dict[int, int],
    tti: int,
    tti_ms: float,
    alpha: float,
) -> Dict[str, int]:
    alloc = {f.flow_id: 0 for f in flows}
    active = [f for f in flows if f.queue]
    if not active:
        return alloc

    by_slice: Dict[str, List[Flow]] = {"S_URLLC": [], "S_EMBB": [], "S_MMTC": []}
    for f in active:
        by_slice[f.slice_name].append(f)

    slice_left = dict(slice_budgets)

    qos_weight = {"URLLC": 100.0, "eMBB": 10.0, "mMTC": 2.0}

    def hol_delay_ms(f: Flow) -> float:
        return (tti - f.queue[0].enqueue_tti) * tti_ms if f.queue else 0.0

    def fairness_guard(f: Flow) -> float:
        gap = tti - f.last_scheduled_tti
        if gap <= 200:
            return 0.0
        return min(5.0, (gap - 200) / 200)

    def score(f: Flow) -> float:
        hol = hol_delay_ms(f)
        dratio = min(2.0, hol / f.qos.delay_budget_ms) if f.qos.delay_budget_ms > 0 else 0.0
        cqi = ue_cqi.get(f.ue_id, 8)
        cqi_norm = cqi / 15.0
        fair = fairness_guard(f)
        return 1.0*qos_weight[f.qos.name] + 60.0*dratio + 5.0*cqi_norm + 10.0*fair

    def take_prbs(f: Flow, n: int, s: str):
        n = min(n, slice_left[s])
        if n <= 0:
            return
        alloc[f.flow_id] += n
        slice_left[s] -= n
        f.last_scheduled_tti = tti

    # emergency URLLC
    emergency = []
    for f in by_slice["S_URLLC"]:
        hol = hol_delay_ms(f)
        if hol >= alpha * f.qos.delay_budget_ms:
            emergency.append((hol / f.qos.delay_budget_ms, f))
    emergency.sort(key=lambda x: x[0], reverse=True)
    for _, f in emergency:
        if slice_left["S_URLLC"] <= 0:
            break
        take_prbs(f, 6, "S_URLLC")

    # best-effort within each slice
    for s, flist in by_slice.items():
        while slice_left[s] > 0 and any(ff.queue for ff in flist):
            best = max((ff for ff in flist if ff.queue), key=score, default=None)
            if best is None:
                break
            take_prbs(best, 3, s)

    return alloc


# -------------------------
# Sim Config (only UEs are varied)
# -------------------------

@dataclass
class SimConfig:
    duration_s: int = 10
    tti_ms: float = 1.0
    total_prbs: int = 50

    n_urllc: int = 8
    n_embb: int = 12
    n_mmtc: int = 10

    # internal constants (not user controlled)
    embb_mbps_per_ue: float = 10.0
    urllc_period_ms: int = 20
    mmtc_period_ms: int = 500
    alpha: float = 0.6

    seed: int = 7


def build_flows(cfg: SimConfig) -> List[Flow]:
    flows: List[Flow] = []

    for i in range(cfg.n_urllc):
        flows.append(Flow(
            flow_id=f"F_URLLC_{i}",
            ue_id=i,
            qos=URLLC,
            slice_name="S_URLLC",
            kind="periodic",
            period_ms=cfg.urllc_period_ms,
        ))

    base = cfg.n_urllc
    for j in range(cfg.n_embb):
        ue_id = base + j
        flows.append(Flow(
            flow_id=f"F_EMBB_{j}",
            ue_id=ue_id,
            qos=EMBB,
            slice_name="S_EMBB",
            kind="cbr",
            cbr_mbps=cfg.embb_mbps_per_ue,
        ))

    base2 = cfg.n_urllc + cfg.n_embb
    for k in range(cfg.n_mmtc):
        ue_id = base2 + k
        flows.append(Flow(
            flow_id=f"F_MMTC_{k}",
            ue_id=ue_id,
            qos=MMTC,
            slice_name="S_MMTC",
            kind="periodic",
            period_ms=cfg.mmtc_period_ms,
        ))

    return flows


def compute_kpis(df: pd.DataFrame, cfg: SimConfig) -> Dict[str, float]:
    tx = df[df["event"] == "tx"].copy()
    viol = df[df["event"] == "violation"].copy()
    ctrl = df[df["event"] == "controller"].copy()

    def safe_pct(a, b):
        return (100.0 * a / b) if b > 0 else 0.0

    urllc_tx = tx[tx.get("qos", "") == "URLLC"]
    urllc_viol = viol[viol.get("qos", "") == "URLLC"]

    total_bits = tx.get("tx_bytes", pd.Series(dtype=float)).fillna(0).sum() * 8
    total_mbps = float(total_bits / 1e6 / cfg.duration_s) if cfg.duration_s > 0 else 0.0

    embb_bits = tx[tx.get("qos", "") == "eMBB"].get("tx_bytes", pd.Series(dtype=float)).fillna(0).sum() * 8
    embb_mbps = float(embb_bits / 1e6 / cfg.duration_s) if cfg.duration_s > 0 else 0.0

    return {
        "urllc_violation_rate_pct": safe_pct(len(urllc_viol), len(urllc_tx)),
        "urllc_p95_delay_ms": float(urllc_tx["hol_delay_ms"].quantile(0.95)) if len(urllc_tx) else 0.0,
        "total_throughput_mbps": total_mbps,
        "embb_throughput_mbps": embb_mbps,
        "avg_risk": float(ctrl["risk"].mean()) if not ctrl.empty else 0.0,
        "min_embb_scale": float(ctrl["embb_scale"].min()) if not ctrl.empty else 1.0,
        "avg_embb_scale": float(ctrl["embb_scale"].mean()) if not ctrl.empty else 1.0,
    }


def run_sim(cfg: SimConfig, mode: str = "smart") -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    mode: 'baseline' or 'smart'
    """
    channel = SimpleChannel(seed=cfg.seed + 100)
    traffic = TrafficGen(seed=cfg.seed + 200)
    flows = build_flows(cfg)

    ctrl_state = ControllerState(total_prbs=cfg.total_prbs)

    total_ttis = int(cfg.duration_s * 1000 / cfg.tti_ms)
    rows: List[Dict[str, Any]] = []

    for tti in range(total_ttis):
        ue_cqi = {f.ue_id: channel.cqi(f.ue_id) for f in flows}

        ctrl_row, budgets = ctrl_state.step(
            mode=mode,
            flows=flows,
            ue_cqi=ue_cqi,
            channel=channel,
            tti=tti,
            tti_ms=cfg.tti_ms,
        )
        rows.append(ctrl_row)

        # generate traffic (congestion-controlled scale from controller)
        traffic.generate(
            flows=flows,
            tti=tti,
            tti_ms=cfg.tti_ms,
            trace_rows=rows,
            embb_rate_scale=float(ctrl_row["embb_scale"]),
        )

        # schedule & transmit
        alloc = qos_slice_scheduler(
            flows=flows,
            slice_budgets=budgets,
            ue_cqi=ue_cqi,
            tti=tti,
            tti_ms=cfg.tti_ms,
            alpha=cfg.alpha,
        )

        for f in flows:
            prbs = alloc.get(f.flow_id, 0)
            if prbs <= 0 or not f.queue:
                continue

            cqi = ue_cqi[f.ue_id]
            bytes_budget = prbs * channel.bytes_per_prb(cqi)

            hol_ms = (tti - f.queue[0].enqueue_tti) * cfg.tti_ms
            rows.append({
                "tti": tti,
                "event": "prb_assign",
                "mode": mode,
                "flow_id": f.flow_id,
                "ue_id": f.ue_id,
                "slice": f.slice_name,
                "qos": f.qos.name,
                "hol_delay_ms": float(hol_ms),
                "allocated_prbs": int(prbs),
                "cqi": int(cqi),
            })

            while f.queue and bytes_budget >= f.queue[0].size_bytes:
                pkt = f.queue[0]
                bytes_budget -= pkt.size_bytes
                f.queue.popleft()

                hol_ms = (tti - pkt.enqueue_tti) * cfg.tti_ms
                rows.append({
                    "tti": tti,
                    "event": "tx",
                    "mode": mode,
                    "pkt_id": pkt.pkt_id,
                    "flow_id": pkt.flow_id,
                    "ue_id": pkt.ue_id,
                    "slice": pkt.slice_name,
                    "qos": pkt.qos.name,
                    "hol_delay_ms": float(hol_ms),
                    "tx_bytes": int(pkt.size_bytes),
                })

                if hol_ms > pkt.qos.delay_budget_ms:
                    rows.append({
                        "tti": tti,
                        "event": "violation",
                        "mode": mode,
                        "pkt_id": pkt.pkt_id,
                        "flow_id": pkt.flow_id,
                        "ue_id": pkt.ue_id,
                        "slice": pkt.slice_name,
                        "qos": pkt.qos.name,
                        "hol_delay_ms": float(hol_ms),
                    })

    df = pd.DataFrame(rows)
    kpis = compute_kpis(df, cfg)
    return df, kpis


def novelty_metrics(df_smart: pd.DataFrame, cfg: SimConfig) -> Dict[str, float]:
    c = df_smart[df_smart["event"] == "controller"].copy()
    if c.empty:
        return {"borrowed_total": 0, "throttle_steps": 0, "critical_pct": 0.0, "recovery_ms": float("nan")}

    borrowed_total = int(c["borrowed_prbs"].sum())
    throttle_steps = int(c["throttle_step"].sum())
    critical_pct = float((c["risk"] > 0.75).mean() * 100.0)

    # recovery: first time risk>0.75 -> first later time risk<0.2 and embb_scale>0.95
    critical_idx = c.index[c["risk"] > 0.75].tolist()
    recovery_ms = float("nan")
    if critical_idx:
        first_i = critical_idx[0]
        after = c.loc[first_i:]
        ok = after[(after["risk"] < 0.2) & (after["embb_scale"] > 0.95)]
        if not ok.empty:
            recovery_ms = float((ok.iloc[0]["tti"] - c.loc[first_i, "tti"]) * cfg.tti_ms)

    return {
        "borrowed_total": borrowed_total,
        "throttle_steps": throttle_steps,
        "critical_pct": critical_pct,
        "recovery_ms": recovery_ms,
    }