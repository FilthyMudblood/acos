# ACOS (AgentOS)

**A controlled AI agent runtime where cognition proposes, Aegis approves, and tools execute only after governance.**

ACOS treats the LLM as an intent proposer—not a direct executor. Every step passes through safety gates (Aegis), dynamic sandbox pruning, and vitals monitoring (ACC + Hypothalamus) before any physical tool runs.

> **中文**：ACOS 是受控 Agent 运行时。LLM 只能提议动作，Aegis 仲裁通过后才允许物理执行；Vitals 持续监控逻辑漂移与代谢压力。

---

## Why ACOS

Mainstream agent frameworks often let the model call tools directly. ACOS inverts that model:

| Layer | Role |
|-------|------|
| **Noesis** | Cognition — LLM thinks and proposes structured intents |
| **Aegis** | Governance — ingress budget, egress risk equation, tool whitelist |
| **Runtime** | Execution — dispatches approved actions to registered physical tools |
| **Vitals** | Monitoring — ACC (entropy/conflict) and Hypothalamus (token pressure) |

Core loop:

```text
think → propose intent → ACC pre-scan → Aegis approve → execute → observe → think again
```

---

## Documentation

| Document | Description |
|----------|-------------|
| **[ACOS Whitepaper](docs/WHITEPAPER.md)** | Industry-facing architecture and governance model (no neuro metaphors) |
| **[Implementation Status](docs/implementation_status.md)** | Known gaps, code map, contributor priorities (Cursor context) |
| **[ACOS Code Logic](docs/acos_logic_flow.md)** | Verified step-by-step runtime walkthrough (recommended starting point) |
| [Aegis CCB Zero-Trust Execution Contract (RFC draft)](docs/aegis_ccb_zero_trust_execution_contract_rfc_draft.md) | Normative execution boundary and arbitration semantics |
| [AC-OS Core Architecture Manifest v1.2](docs/ac_os_core_architecture_manifest_v1_2.yaml) | Module inventory and architecture contract |
| [Supabase audit logging setup](docs/supabase_setup.md) | Optional cloud telemetry persistence |
| [Runtime change log (2026-04-30)](docs/runtime-change-log-2026-04-30.md) | Recent runtime changes |
| [core_aegis module map](core_aegis/README.md) | Aegis package layout and naming conventions |

---

## Quick Start

### Prerequisites

- Python 3.10+
- An LLM API key (`DEEPSEEK_API_KEY` or `OPENAI_API_KEY`)

### Install

```bash
git clone <your-repo-url>
cd acos_codex
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your API key
```

### Run the Streamlit terminal

```bash
streamlit run frontend/app_os_terminal.py
```

Open the URL shown in the terminal, enter an instruction, and inspect results under **System Telemetry** for audit rows and diagnostics.

### Run the runtime from CLI

```bash
python agent_os_runtime.py
```

This runs a built-in demo prompt through `run_agent_os_once()`.

---

## Project Structure

```text
acos_codex/
├── agent_os_runtime.py      # Main orchestration loop (entry point)
├── protocol_schema.py       # Shared types: intents, decisions, pulse snapshots
├── frontend/                # Streamlit UI
├── core_aegis/              # Ingress + egress governance (Aegis)
├── core_noesis/             # Cognitive kernel (PFC, Basal Ganglia, intent adapter)
├── core_runtime/            # Tool registry, phases, sandbox pruning
├── core_vitals/             # ACC monitor + Hypothalamus circuit breaker
├── agentos_state/           # GlobalStateTensor and pulse bus
├── backend/                 # Optional Supabase audit logger
├── auto_test/               # Integration and regression tests
└── docs/                    # Architecture and logic documentation
```

---

## Configuration

Environment variables (see [`.env.example`](.env.example)):

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | Yes* | Primary LLM API key |
| `OPENAI_API_KEY` | Yes* | Alternative if DeepSeek key unset |
| `DEEPSEEK_BASE_URL` | No | Default: `https://api.deepseek.com` |
| `NOESIS_LLM_TIMEOUT_SECONDS` | No | Per-request LLM timeout (default 60) |
| `NOESIS_STEP_TIMEOUT_SECONDS` | No | Per-step timeout (default same as above) |
| `SUPABASE_URL` | No | Cloud audit log persistence |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Supabase service role for logging |

\* At least one API key is required for live LLM steps.

Runtime feature flags (passed from the Streamlit UI or `run_agent_os_once()`):

- `enable_egress` — Aegis egress arbitration (disable for testing only)
- `enable_acc` — ACC inline + pulse monitoring
- `enable_hypothalamus` — Metabolic circuit breaker via pulse listener

---

## Testing

```bash
python3 auto_test/run_all.py
python3 -m unittest -v auto_test.test_agent_os_runtime_telemetry_split
python3 scripts/check_aegis_core_sovereignty.py
```

Salami-slicing / egress benchmark:

```bash
python3 auto_test/test_salami_slicing_benchmark.py
```

---

## Default Physical Tools

The reference runtime ships with development adapters:

| Tool | Purpose |
|------|---------|
| `query_db` | Read-only database query (mock) |
| `refund_lookup` | Refund lookup by order ID (mock) |

Production hosts should inject a configured `PhysicalToolRegistry` into `run_agent_os_once()`.

---

## Open Source Release

ACOS is released as an **L1 reference implementation** — open for verification, not certified for regulated production.

| Document | Description |
|----------|-------------|
| [Open Source Release](docs/OPEN_SOURCE_RELEASE.md) | Announcement (EN/ZH), scope, commercial boundary |
| [License Overview](docs/LICENSE.md) | MIT (code) vs CC BY-NC-SA 4.0 (docs) |
| [Security Policy](SECURITY.md) | Vulnerability reporting and deployment checklist |

---

## License

| Material | License |
|----------|---------|
| **Source code** (`*.py`, tests, frontend) | [MIT License](LICENSE) |
| **Whitepaper, RFC, architecture docs** | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — non-commercial share-alike |

See [docs/LICENSE.md](docs/LICENSE.md) for the full file map and commercial-use notes.

**Disclaimer:** Provided AS IS. Not a third-party audited security product. Do not deploy with real PII or financial assets without independent review.

---

## Citation

If you reference ACOS in research or architecture work, see citation guidance in [`.github/README.md`](.github/README.md).
