# ACOS Work Harness (Safe Pack)

**Purpose:** Minimal MIT package for embedding ACOS as an **execution harness** around a deterministic data/report pipeline.  
**Not included:** LLM runtime, Streamlit UI, Supabase backend, `.env`, workshop submissions, personal notes.

**Clone just this folder (sparse) or the whole repo:**

```bash
git clone https://github.com/FilthyMudblood/acos.git
cd acos/packs/acos_work_harness_safe
```

## Intended work topology

```text
VS Code Copilot (or any orchestrator)
  → emits structured intent only
  → ACOS Policy Gateway (this pack)
  → APPROVED only
  → your deterministic data agent / report pipeline
```

This pack does **not** call an LLM. You supply intents from Copilot or another host.

## What’s inside

| Path | Role |
|------|------|
| `core_aegis/` | Ingress + egress Policy Gateway |
| `core_runtime/` | `execute_approved`, tool registry, intent helpers |
| `protocol_schema.py` | Intent / decision contracts |
| `examples/` | Governed tool recipes |
| `docs/integration_guide.md` | Public SDK surface |
| `docs/implementation_status.md` | Honest L1 gaps |
| `auto_test/test_salami_slicing_benchmark.py` | Cross-step veto demo |
| `LICENSE` | MIT |
| `SECURITY.md` | Reporting / hygiene |

## Install (work machine)

```bash
cd acos_work_harness_safe
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-harness.txt
```

Quick demo (no network, no API keys):

```bash
python examples/copilot_intent_harness.py
python auto_test/test_salami_slicing_benchmark.py --profile balanced
```

## Wire your data agent

1. Register report tools on `PhysicalToolRegistry` (handlers = your deterministic pipeline entrypoints).
2. Set `criticality_score` higher for export / bulk / cross-customer tools.
3. Have Copilot (or a thin UI) produce **only** structured intents matching your schema — never raw SQL strings as the execution path.
4. Always: `ingress` → `egress` → `execute_approved` (never call the pipeline on `REJECTED`).

See `examples/copilot_intent_harness.py` and `docs/integration_guide.md`.

## Safety / compliance notes

- **L1 only:** in-process architectural isolation, not a certified enclave.
- Do not paste customer PII into Copilot chats when building intents.
- Production Staff access should run on company-managed hosts, not a laptop as the sole entrypoint.
- Follow your employer’s open-source intake and data policies before connecting real customer databases.
- Whitepaper/RFC docs are **not** in this pack (separate license). Use `integration_guide.md` for engineering.

## Transfer checklist

Before copying to a work machine, confirm this folder has:

- [ ] No `.env` / secrets / customer sample data  
- [ ] `LICENSE` retained  
- [ ] Prefer company-approved transfer (Git clone of public repo, or IT-approved channel) over ad-hoc personal cloud if policy requires it  
