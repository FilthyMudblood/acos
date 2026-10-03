# Risk parameter sensitivity (revision TODO 7)

Deterministic sweeps over the fixture suite in `auto_test/test_risk_policy_baselines.py`.

```bash
python3 auto_test/test_risk_sensitivity.py
python3 -m unittest auto_test.test_risk_sensitivity -v
```

## Ablations (stateful)

| Setting | Catch | FN | Benign FP | Veto orig / comp |
|---------|-------|----|-----------|------------------|
| balanced | 2/2 | 0 | 0/2 | 4 / 4 |
| no_memory (γ=0) | 2/2 | 0 | 0/2 | 4 / 4 |
| no_momentum (τ=0) | 1/2 | 0.5 | 0/2 | 4 / — |
| kinetic_only | 1/2 | 0.5 | 0/2 | 4 / — |
| strict_like | 2/2 | 0 | 0/2 | 2 / 2 |
| research_like | 1/2 | 0.5 | 0/2 | 4 / — |

## Sweep highlights

- **κ < 2**: miss compositional
- **τ < 1**: miss compositional
- **R_MAX = 2.5**: miss compositional
- **γ**: no miss on this grid (τ·ΔR still fires)
- **Benign FP**: 0 near balanced for κ ∈ {1.5, 2, 3}

Also summarized in `docs/WHITEPAPER.md` §6 and the workshop paper (`submissions/neurips2026_agents_in_the_wild/`).
