# ACOS License Overview

This repository uses **split licensing**: executable reference code and technical documentation are licensed differently.

---

## 1. Reference Code — MIT License

All **software source code** in this repository is licensed under the [MIT License](../LICENSE), unless a file header states otherwise.

**Includes (non-exhaustive):**

```text
*.py
requirements.txt
auto_test/
scripts/
frontend/          (application code)
backend/           (application code)
core_aegis/
core_noesis/
core_runtime/
core_vitals/
agentos_state/
protocol_schema.py
agent_os_runtime.py
```

**You may:** use, modify, distribute, and sublicense the code, including in commercial products, subject to the MIT notice requirement.

**You may not:** imply that this reference implementation is a certified security product or has undergone third-party audit (see disclaimer below).

---

## 2. Technical Documents — CC BY-NC-SA 4.0

The following **documentation and specification materials** are licensed under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/):

```text
docs/WHITEPAPER.md
docs/aegis_ccb_zero_trust_execution_contract_rfc_draft.md
docs/ac_os_core_architecture_manifest_v1_2.yaml
docs/acos_logic_flow.md
docs/implementation_status.md
docs/OPEN_SOURCE_RELEASE.md
docs/LICENSE.md
docs/runtime-change-log-*.md
.github/README.md
```

**You may:** share and adapt these documents with attribution, for **non-commercial** purposes, under the same license.

**Commercial use** of the whitepaper, RFC, or architecture specifications (e.g. republishing as a paid product, white-label documentation, or closed-source certification pack derived primarily from these docs) requires **separate permission** from the copyright holder.

**Citation:** When referencing ACOS architecture in academic or industry reports, cite the Zenodo record when available (see [README](../README.md#citation)).

---

## 3. What Is Not Licensed for Redistribution

| Asset | Status |
|-------|--------|
| **The Aegis Equation** (mathematical model) | Described in open docs; commercial embedding in competing governance products may require separate agreement |
| **Trademarks** (`ACOS`, `Aegis Cortex`, `AgentOS`) | Not granted by OSS licenses; do not imply endorsement |
| **Production hardened runtime (L2/L3)** | Not included in this repository; may be offered under separate commercial terms |
| **Your `.env`, API keys, Supabase credentials** | Never commit; not part of any license grant |

---

## 4. Contributor License

By submitting a pull request to this repository, you agree that:

1. Your **code contributions** are licensed under the MIT License.
2. Your **documentation contributions** to files listed in Section 2 are licensed under CC BY-NC-SA 4.0.
3. You have the right to submit the work under these terms.

---

## 5. Disclaimer (All Materials)

This project is a **reference implementation** for architecture evaluation and research.

- Provided **AS IS**, without warranty of any kind.
- **Not** a certified production security appliance.
- **Not** audited by a third-party security firm.
- Do **not** deploy with real PII, payment systems, or regulated health data without independent risk assessment.

The MIT License disclaimer applies to code. Document users assume their own compliance obligations when applying the architecture to regulated environments.

---

## 6. Quick Decision Table

| Use case | Code (MIT) | Docs (CC BY-NC-SA) |
|----------|------------|---------------------|
| Internal pilot / research | Yes | Yes |
| Fork and modify runtime | Yes | Yes (share alike if you redistribute adapted docs) |
| Academic paper citing architecture | N/A | Yes with attribution |
| Sell documentation derived from whitepaper/RFC | N/A | Requires permission |
| Ship modified code in commercial product | Yes (with MIT notice) | N/A |
| Imply official certification or endorsement | No | No |

For licensing questions: open a GitHub issue labeled `legal` or contact the repository maintainer before commercial document reuse.
