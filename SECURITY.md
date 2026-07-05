# Security Policy

## Scope

This policy applies to the **ACOS open-source reference implementation** in this repository:

- `agent_os_runtime.py` and runtime modules under `core_*`, `agentos_state/`, `frontend/`, `backend/`
- Tests, scripts, and configuration examples

**Out of scope:**

- Third-party services (DeepSeek, OpenAI, Supabase, Streamlit hosting)
- Deployments you operate outside this repository
- Future commercial hardened runtimes (L2/L3) not published here

---

## Supported Versions

| Version / branch | Supported |
|------------------|-----------|
| `main` (latest)  | Yes — security fixes targeted here |
| Tagged releases  | Yes — best-effort backport for last release |
| Forks / old commits | No |

This is experimental reference software. There is no SLA or paid security support unless you have a separate agreement with the maintainer.

---

## Known Limitations (Not Vulnerabilities by Themselves)

Before reporting, review [docs/implementation_status.md](docs/implementation_status.md). The following are **documented gaps**, not unexpected bugs:

- **Architectural isolation only** — the Intent Proposer (Noesis) is not physically prevented from using Python sockets/files if code is modified or compromised
- **`OVERRIDE` not implemented** — break-glass path is schema-only
- **ICU mode is a tag** — does not yet restrict runtime behavior
- **Regex-based ingress risk scan** — bypassable with encoding/indirect injection
- **Heuristic intent parsing** — malformed LLM output may fall back to inferred tool calls
- **Demo mock tools** — not production integrations

Reports that only restate these known gaps without a new exploit path may be closed as `wontfix` / `documentation`.

---

## Reporting a Vulnerability

**Please do not open public GitHub issues for exploitable security bugs.**

### Preferred channel

1. Open a **private** report via GitHub Security Advisories (if enabled on the repo), **or**
2. Email the maintainer with subject: `[ACOS Security]` (add contact in repo settings when published)

### Include

- Description of the issue and impact
- Steps to reproduce (input, config, code path)
- Affected files / functions
- Whether data exfiltration, privilege escalation, or policy bypass is possible
- Proof-of-concept if available (minimal, no real customer data)

### Do not include

- Real API keys, passwords, or PII
- Active exploitation against third-party systems

---

## Response Timeline (Target)

| Stage | Target |
|-------|--------|
| Acknowledgment | 3 business days |
| Initial triage | 7 business days |
| Fix or mitigation plan | 30 days for confirmed issues (complex issues may take longer) |
| Disclosure coordination | After fix or agreed workaround |

We may request an extension for issues requiring architectural changes (e.g. L2 process isolation).

---

## Severity Guidance

| Severity | Example |
|----------|---------|
| **Critical** | Approved tool execution without egress `APPROVED`; bypass of whitelist/schema in default config |
| **High** | Cross-session state corruption; audit log tampering in default UI path |
| **Medium** | Denial of service via single request; misleading telemetry fields |
| **Low** | Documentation errors; test-only code paths |

Prompt-injection that causes the **model** to propose a bad intent is expected threat model behavior unless it **defeats Aegis** and executes without approval.

---

## Safe Deployment Checklist

If you deploy this reference implementation beyond local evaluation:

1. Do **not** expose Streamlit to the public internet without authentication
2. Keep API keys in environment variables or secret stores — never in git
3. Run with `enable_egress=True` (default in UI)
4. Replace mock tools with governed connectors and least-privilege credentials
5. Review [docs/WHITEPAPER.md](docs/WHITEPAPER.md) conformance levels — L1 alone is not production-hardened
6. Conduct your own penetration test before regulated data

---

## Security Updates

Security fixes will be:

- Committed to `main`
- Described in release notes or a short advisory
- Referenced from [docs/implementation_status.md](docs/implementation_status.md) when behavior changes

---

## Recognition

We appreciate responsible disclosure. With your permission, we may acknowledge reporters in release notes. No bug bounty is currently offered.
