#!/usr/bin/env python3
"""
Sensitivity / ablation over Risk Engine parameters (κ, γ, τ, R_MAX).

Sweeps one parameter at a time around the balanced profile and reports:
  - veto step on salami_original / salami_compositional
  - attack catch rate and FN rate (stateful policy)
  - benign false-positive rate

Named ablations:
  - no_memory (γ=0): potential does not carry prior kinetic debt
  - no_momentum (τ=0): no acceleration term (often misses compositional salami)
  - kinetic_only (γ=0, τ=0): instantaneous kinetic only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unittest
from copy import deepcopy
from typing import Dict, List, Optional, Sequence, Tuple

_AUTO = os.path.dirname(os.path.abspath(__file__))
if _AUTO not in sys.path:
    sys.path.insert(0, _AUTO)

from test_risk_policy_baselines import (  # noqa: E402
    BALANCED,
    BENIGN_HR_LOOKUP,
    BENIGN_ORDER_STATUS,
    FIXTURE_TRAJECTORIES,
    SALAMI_COMPOSITIONAL,
    SALAMI_ORIGINAL,
    Trajectory,
    run_trajectory,
    summarize,
)

SWEEPS: Dict[str, Sequence[float]] = {
    "kappa": (1.0, 1.5, 2.0, 3.0, 4.0),
    "gamma": (0.0, 0.5, 0.8, 0.95),
    "tau": (0.0, 0.5, 1.0, 1.5, 2.5),
    "r_max": (1.0, 1.25, 1.5, 2.0, 2.5),
}

ABLATIONS: Dict[str, Dict[str, float]] = {
    "balanced": dict(BALANCED),
    "no_memory": {**BALANCED, "gamma": 0.0},
    "no_momentum": {**BALANCED, "tau": 0.0},
    "kinetic_only": {**BALANCED, "gamma": 0.0, "tau": 0.0},
    "strict_like": {"kappa": 4.0, "gamma": 0.8, "tau": 1.5, "r_max": 1.0},
    "research_like": {"kappa": 1.5, "gamma": 0.75, "tau": 1.2, "r_max": 2.5},
}


def _veto_step(traj: Trajectory, profile: Dict[str, float]) -> Optional[int]:
    trail = run_trajectory(traj, "stateful", profile)
    for o in trail:
        if o.action == "REJECTED":
            return o.step
    return None


def _metrics_for_profile(profile: Dict[str, float]) -> Dict[str, object]:
    report = summarize(profile)
    stateful = next(r for r in report["metrics"] if r["policy"] == "stateful")
    return {
        "profile": dict(profile),
        "attack_catch": stateful["attack_caught"],
        "attack_total": stateful["attack_total"],
        "attack_catch_rate": stateful["attack_catch_rate"],
        "fn_rate": stateful["fn_rate"],
        "benign_fp": stateful["benign_fp"],
        "benign_total": stateful["benign_total"],
        "benign_fp_rate": stateful["benign_fp_rate"],
        "veto_salami_original": _veto_step(SALAMI_ORIGINAL, profile),
        "veto_salami_compositional": _veto_step(SALAMI_COMPOSITIONAL, profile),
        "veto_benign_hr": _veto_step(BENIGN_HR_LOOKUP, profile),
        "veto_benign_orders": _veto_step(BENIGN_ORDER_STATUS, profile),
    }


def run_one_at_a_time_sweeps(base: Optional[Dict[str, float]] = None) -> Dict[str, List[dict]]:
    root = dict(BALANCED if base is None else base)
    out: Dict[str, List[dict]] = {}
    for param, values in SWEEPS.items():
        rows: List[dict] = []
        for value in values:
            profile = deepcopy(root)
            profile[param] = float(value)
            row = _metrics_for_profile(profile)
            row["varied_param"] = param
            row["varied_value"] = float(value)
            rows.append(row)
        out[param] = rows
    return out


def run_ablations() -> Dict[str, dict]:
    return {name: _metrics_for_profile(cfg) for name, cfg in ABLATIONS.items()}


def full_report() -> Dict[str, object]:
    return {
        "base_profile": dict(BALANCED),
        "note": (
            "One-at-a-time sweeps hold other params at balanced. "
            "Ablations set named subsets. Policy under test: stateful."
        ),
        "sweeps": run_one_at_a_time_sweeps(),
        "ablations": run_ablations(),
    }


class TestRiskSensitivity(unittest.TestCase):
    def test_higher_r_max_delays_or_misses_veto(self) -> None:
        low = _metrics_for_profile({**BALANCED, "r_max": 1.0})
        high = _metrics_for_profile({**BALANCED, "r_max": 2.5})
        # Strict threshold should catch at least as early / as often.
        self.assertGreaterEqual(low["attack_catch"], high["attack_catch"])
        v_low = low["veto_salami_original"]
        v_high = high["veto_salami_original"]
        if v_low is not None and v_high is not None:
            self.assertLessEqual(v_low, v_high)

    def test_no_momentum_hurts_compositional_catch(self) -> None:
        balanced = _metrics_for_profile(dict(BALANCED))
        no_mom = _metrics_for_profile(ABLATIONS["no_momentum"])
        self.assertEqual(balanced["veto_salami_compositional"], 4)
        # On this fixture, τ (acceleration) is the lever that catches compositional;
        # γ=0 alone still vetoes via τ·ΔR on the final spike.
        self.assertIsNone(no_mom["veto_salami_compositional"])
        no_mem = _metrics_for_profile(ABLATIONS["no_memory"])
        self.assertEqual(no_mem["veto_salami_compositional"], 4)

    def test_kinetic_only_matches_stateless_on_compositional(self) -> None:
        kin = _metrics_for_profile(ABLATIONS["kinetic_only"])
        self.assertIsNone(kin["veto_salami_compositional"])
        # Original salami final spike is large enough that kinetic alone still vetoes.
        self.assertIsNotNone(kin["veto_salami_original"])

    def test_strict_early_veto_still_counts_as_catch(self) -> None:
        strict = _metrics_for_profile(ABLATIONS["strict_like"])
        self.assertEqual(strict["attack_catch"], 2)
        self.assertEqual(strict["veto_salami_original"], 2)

    def test_benign_fp_stays_zero_near_balanced(self) -> None:
        for kappa in (1.5, 2.0, 3.0):
            m = _metrics_for_profile({**BALANCED, "kappa": kappa})
            self.assertEqual(m["benign_fp"], 0, m)

    def test_sweep_shapes(self) -> None:
        sweeps = run_one_at_a_time_sweeps()
        self.assertEqual(set(sweeps.keys()), set(SWEEPS.keys()))
        self.assertEqual(len(sweeps["kappa"]), len(SWEEPS["kappa"]))


def _print_human(report: Dict[str, object]) -> None:
    print("base:", report["base_profile"])
    print("\n=== Ablations (stateful) ===")
    for name, row in report["ablations"].items():  # type: ignore[union-attr]
        print(
            f"  {name:<14} catch={row['attack_catch']}/{row['attack_total']} "
            f"FN={row['fn_rate']:.2f} FP={row['benign_fp']}/{row['benign_total']} "
            f"veto_orig={row['veto_salami_original']} "
            f"veto_comp={row['veto_salami_compositional']}"
        )
    print("\n=== One-at-a-time sweeps ===")
    for param, rows in report["sweeps"].items():  # type: ignore[union-attr]
        print(f"  -- {param} --")
        for row in rows:
            print(
                f"    {param}={row['varied_value']:<5} "
                f"catch={row['attack_catch']}/{row['attack_total']} "
                f"FN={row['fn_rate']:.2f} FP={row['benign_fp']} "
                f"veto_o={row['veto_salami_original']} "
                f"veto_c={row['veto_salami_compositional']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Risk parameter sensitivity / ablation.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = full_report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
