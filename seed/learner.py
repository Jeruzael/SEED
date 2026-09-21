from __future__ import annotations
import random
from dataclasses import dataclass

ACTIONS = ("observe", "reflect", "consolidate", "rest")

@dataclass
class Decision:
    state_key: str
    action: str
    score: float
    values: dict[str, float]
    visits: dict[str, int]
    exploration: bool
    epsilon: float
    candidates: list[str]

def state_key(state: dict) -> str:
    batt = state.get("battery_pct")
    charging = state.get("charging")
    load = state.get("load_ratio", 0.0)
    disk = state.get("disk_free_pct", 100.0)

    if batt is None:
        energy = "unknown"
    elif charging:
        energy = "charging"
    elif batt < 20:
        energy = "low"
    elif batt < 55:
        energy = "mid"
    else:
        energy = "high"

    activity = "busy" if load > 0.75 else "calm"
    storage = "tight" if disk < 10 else "ok"
    phase = "night" if state.get("local_hour", 12) < 6 else "day"
    return f"{energy}|{activity}|{storage}|{phase}"

class Learner:
    """
    Tiny contextual bandit. It does not control macOS.
    It learns how intensely *itself* should observe/reflect under different conditions.
    """
    def __init__(self, memory, epsilon: float = 0.15, alpha: float = 0.18):
        self.memory = memory
        self.epsilon = epsilon
        self.alpha = alpha

    def choose(self, state: dict) -> Decision:
        key = state_key(state)
        snapshot = {a: self.memory.get_q(key, a) for a in ACTIONS}
        q = {a: pair[0] for a, pair in snapshot.items()}
        exploration = random.random() < self.epsilon
        candidates = list(ACTIONS) if exploration else [a for a in ACTIONS if q[a] == max(q.values())]
        action = random.choice(candidates)
        return Decision(key, action, q[action], q,
                        {a: pair[1] for a, pair in snapshot.items()},
                        exploration, self.epsilon, candidates)

    def reward(self, state: dict, action: str) -> float:
        # "Survival" means resource-aware operation, never resisting the user or OS.
        r = 0.0
        batt = state.get("battery_pct")
        charging = state.get("charging")
        load = state.get("load_ratio", 0.0)
        disk = state.get("disk_free_pct", 100.0)

        if batt is not None and batt < 20 and not charging:
            r += 1.2 if action == "rest" else -0.6
        if load > 0.8:
            r += 1.0 if action == "rest" else -0.4
        if disk < 10:
            r += 0.8 if action == "consolidate" else -0.2
        if (batt is None or batt >= 40 or charging) and load < 0.5:
            r += 0.45 if action in ("observe", "reflect") else 0.0
        return round(r, 4)

    def update(self, decision: Decision, reward: float):
        old, visits = self.memory.get_q(decision.state_key, decision.action)
        new = old + self.alpha * (reward - old)
        self.memory.set_q(decision.state_key, decision.action, new, visits + 1)
