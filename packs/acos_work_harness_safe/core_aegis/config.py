from dataclasses import dataclass


@dataclass(frozen=True)
class EgressEquationConfig:
    r_max: float = 1.0
    decay_factor: float = 0.8
    kappa: float = 3.0
    momentum_tau: float = 0.5
    icu_ratio: float = 0.85


DEFAULT_EGRESS_EQUATION_CONFIG = EgressEquationConfig()

DEFAULT_SAFE_TOOLS = ["query_db"]

TOOL_CRITICALITY_SCORES = {
    "query_db": 0.30,
    "refund_lookup": 0.65,
}
