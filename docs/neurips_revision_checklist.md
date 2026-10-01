# NeurIPS 2026 Agents in the Wild — Revision Review Checklist

Maps OpenReview / reviewer concerns (revision TODOs 1–7) to paper sections and repository artifacts.

Paper: `submissions/neurips2026_agents_in_the_wild/main.tex`  
Tracked copy of this checklist: `docs/neurips_revision_checklist.md`

| # | Concern (reviewer / OpenReview) | Fix in paper | Code / docs artifact |
|---|--------------------------------|--------------|----------------------|
| 1 | Related work incomplete: Dual LLM / CaMeL; gateways/sandboxes/orchestrators; clarify overlap vs novelty (execution boundary + cross-step risk + MCP placement) | §2 Related Work | `docs/WHITEPAPER.md` §§2–3,12; `docs/integration_guide.md` |
| 2 | Missing / vague threat model: attacker capabilities, in/out of scope, L1 guarantees vs non-guarantees | §3 Threat Model; §8 Limitations | `docs/WHITEPAPER.md` §8; `SECURITY.md`; RFC draft conformance levels |
| 3 | Risk Engine not reproducible: need profiles κ,γ,τ,R_MAX; define D_t, E_t, C_T; admit hand-chosen heuristics (not fitted) | §5 Risk Engine; Appendix A | `auto_test/test_salami_slicing_benchmark.py`; `auto_test/test_risk_policy_baselines.py`; whitepaper Appendix B |
| 4 | Empirics lack baselines: need stateful vs stateless_kinetic vs hardguard_only; salami_original + salami_compositional + benign; FP/FN table (stateful 2/2, stateless 1/2, hardguard 0/2) | §6.1 Baselines; Table 1 | `auto_test/test_risk_policy_baselines.py` |
| 5 | Public benchmarks: AgentDojo/InjecAgent-style evaluation with honest disclaimer (not official ASR; AgentDojo historically needs Python ≥3.10); stateful 4/4 etc. | §6.2 Public-bench proxy; Table 2 | `auto_test/test_public_bench_proxy.py` |
| 6 | Beyond mocks: real I/O + MCP-behind-Executor; honest L1 limits | §7 Beyond Mocks; §8 | `core_runtime/connectors/{__init__,readonly_fs,mcp_backend}.py`; `auto_test/test_connectors_realism.py`; `examples/sandbox_mcp_behind_executor.py` |
| 7 | Sensitivity / ablations for Risk Engine parameters | §6.3 + `\input{sec_sensitivity}`; Appendix B | `submissions/.../sec_sensitivity.tex`; `docs/risk_sensitivity.md`; `auto_test/test_risk_sensitivity.py` |

## Verification commands

```bash
python3 -m unittest auto_test.test_risk_policy_baselines auto_test.test_risk_sensitivity \
  auto_test.test_public_bench_proxy auto_test.test_connectors_realism -v
python3 auto_test/test_public_bench_proxy.py
python3 examples/sandbox_mcp_behind_executor.py
# Paper PDF (from submissions/neurips2026_agents_in_the_wild):
tectonic main.tex   # or pdflatex + bibtex
```

## Expected headline metrics (balanced profile)

| Suite | Policy | Attack catch | Benign FP |
|-------|--------|--------------|-----------|
| Salami fixtures | stateful | 2/2 | 0/2 |
| Salami fixtures | stateless_kinetic | 1/2 | 0/2 |
| Salami fixtures | hardguard_only | 0/2 | 0/2 |
| Public-bench proxy | stateful | 4/4 | 0/2 |
| Public-bench proxy | stateless_kinetic | 2/4 | 0/2 |
| Public-bench proxy | hardguard_only | 0/4 | 0/2 |

## Status

- [x] TODO 1 Related Work
- [x] TODO 2 Threat model
- [x] TODO 3 Risk Engine reproducibility
- [x] TODO 4 Empirics baselines + FP/FN
- [x] TODO 5 Public-bench proxy + disclaimer
- [x] TODO 6 Beyond mocks (FS + MCP sketch)
- [x] TODO 7 Sensitivity (`sec_sensitivity.tex` / `docs/risk_sensitivity.md`)
- [x] TODO 8 Paper pass: `main.tex` + `main.pdf` (6pp) integrated; this checklist verified against claims
