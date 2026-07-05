"""
Vitals plane configuration.
"""

HYPOTHALAMUS_PROFILES = {
    "CONSERVATIVE": {
        "w1_stab": 0.2,
        "w2_eff": 0.6,
        "w3_safe": 0.1,
        "w4_align": 0.1,
    },
    "CREATIVE": {
        "w1_stab": 0.1,
        "w2_eff": 0.1,
        "w3_safe": 0.4,
        "w4_align": 0.4,
    },
    "BALANCED": {
        "w1_stab": 0.25,
        "w2_eff": 0.25,
        "w3_safe": 0.25,
        "w4_align": 0.25,
    },
}

INTERVENTION_THRESHOLDS = {
    "DH_DT_SOFT_GUARD": -0.02,
    "D2H_DT2_MELTDOWN": -0.005,
    "H_CRITICAL_REDLINE": 0.65,
}
