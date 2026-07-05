# ACOS (AgentOS)

**A governed AI agent runtime: the model proposes actions; the policy gateway approves them; tools run only after authorization.**

ACOS separates **intent proposal** from **physical execution**. The LLM outputs structured action intents—it does not call APIs, databases, or filesystems directly. Every proposal passes through a deterministic policy gateway (budget limits, tool whitelist, schema validation, cross-step risk scoring) before the runtime executor runs anything.

> **中文**：ACOS 是受控 Agent 运行时。LLM 只负责提议结构化动作；策略网关仲裁通过后，运行时才会执行工具。旁路监控持续检测逻辑漂移与资源消耗异常。

**Repository:** https://github.com/FilthyMudblood/acos

---

## Why ACOS

Most agent frameworks let the model invoke tools directly:

```text
User → LLM → tool call → API / DB → …
```

ACOS enforces a governance boundary:

```text
User → LLM (intent only) → Policy Gateway → APPROVED → Runtime Executor → tool
```

| Component | Role |
|-----------|------|
| **Intent Proposer** | LLM reasoning; outputs `tool_call`, `final_answer`, or `terminate` |
| **Policy Gateway** | Ingress budgeting, egress risk engine, whitelist and schema guards |
| **Runtime Executor** | Dispatches approved actions to registered tool handlers |
| **Side-channel Monitors** | Drift scoring and budget circuit breaker via step telemetry |

Core loop:

```text
reason → propose intent → drift pre-scan → policy approve/reject → execute or damp → observe → repeat
```

---

## Documentation

| Document | Description |
|----------|-------------|
| **[Whitepaper](docs/WHITEPAPER.md)** | Industry architecture, cross-step risk, deployment levels |
| **[Code Logic](docs/acos_logic_flow.md)** | Step-by-step runtime walkthrough |
| **[Implementation Status](docs/implementation_status.md)** | Known gaps and contributor priorities |
| [RFC draft — Zero-Trust Execution Contract](docs/aegis_ccb_zero_trust_execution_contract_rfc_draft.md) | Normative execution boundary |
| [Open Source Release](docs/OPEN_SOURCE_RELEASE.md) | Scope, licensing, commercial boundary |
| [Security Policy](SECURITY.md) | Vulnerability reporting |

---

## Quick Start

### Prerequisites

- Python 3.10+
- `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`

### Install

```bash
git clone https://github.com/FilthyMudblood/acos.git
cd acos
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add your API key
```

### Run the Streamlit UI

```bash
streamlit run frontend/app_os_terminal.py
```

Use **System Telemetry** to inspect structured audit rows (`physical_gate_status`, `termination_cause`, tool invocations).

### Run from CLI

```bash
python agent_os_runtime.py
```

---

## Project Structure

Internal module names reflect early architecture labels; industry terms are used in docs.

```text
acos/
├── agent_os_runtime.py       # Main orchestration loop
├── protocol_schema.py          # Intents, decisions, telemetry types
├── frontend/                   # Streamlit operator UI
├── core_aegis/                 # Policy Gateway (ingress + egress)
├── core_noesis/                # Intent Proposer (LLM step + intent adapter)
├── core_runtime/               # Tool registry, phases, sandbox pruning
├── core_vitals/                # Drift monitor + budget circuit breaker
├── agentos_state/              # Session state and telemetry bus
├── backend/                    # Optional Supabase audit logger
├── auto_test/                  # Tests and salami-slicing benchmark
└── docs/
```

---

## Configuration

See [`.env.example`](.env.example).

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | Yes* | Primary LLM API key |
| `OPENAI_API_KEY` | Yes* | Alternative if DeepSeek unset |
| `SUPABASE_URL` | No | Optional cloud audit logging |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Supabase service role |

\* At least one LLM API key is required.

Runtime flags (`run_agent_os_once()` / Streamlit sidebar):

| Flag | Description |
|------|-------------|
| `enable_egress` | Policy egress arbitration (keep `True` outside tests) |
| `enable_acc` | Drift monitor (inline + telemetry listener) |
| `enable_hypothalamus` | Budget circuit breaker via step telemetry |

---

## Testing

```bash
python3 auto_test/run_all.py
python3 auto_test/test_salami_slicing_benchmark.py
python3 scripts/check_aegis_core_sovereignty.py
```

The salami-slicing benchmark demonstrates cross-step risk accumulation: individually low-risk steps can be vetoed when session risk exceeds the configured threshold.

---

## Default Tools (Development)

| Tool | Purpose |
|------|---------|
| `query_db` | Mock read-only query |
| `refund_lookup` | Mock refund lookup |

Replace with a configured `PhysicalToolRegistry` for production integrations.

---

## Open Source

ACOS is an **L1 reference implementation**—open for verification, not certified for regulated production.

| Material | License |
|----------|---------|
| Source code | [MIT](LICENSE) |
| Whitepaper, RFC, architecture docs | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) |

Details: [docs/LICENSE.md](docs/LICENSE.md)

**Disclaimer:** AS IS. No third-party security audit. Do not deploy with real PII or financial assets without independent review.

---

## Citation

```bibtex
@misc{acos_2026,
  author       = {He, Muchen},
  title        = {{ACOS (AgentOS): Governed AI Agent Execution --- Reference Implementation}},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/FilthyMudblood/acos}
}
```
