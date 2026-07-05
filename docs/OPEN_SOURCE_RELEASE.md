# ACOS Open Source Release

**Status:** Reference implementation release  
**Date:** July 2026  
**Maintainer:** Muchen He

---

## Announcement (English)

We are open-sourcing **ACOS (AgentOS)** — a governed AI agent runtime that separates **intent proposal** from **physical execution**.

Most agent frameworks let the language model call tools directly. ACOS inverts that model: the LLM outputs structured intents; a deterministic **Policy Gateway (Aegis)** arbitrates every proposal using hard guards and a **stateful cross-step Risk Engine**; a **Runtime Executor** invokes external tools only after an explicit `APPROVED` decision.

### Why open source

1. **Trust through verification** — Security claims must be reproducible. We publish code, tests, and a salami-slicing benchmark so reviewers can validate cross-step veto behavior.
2. **Standard-setting** — The RFC draft, whitepaper, and reference implementation define an execution governance model others can implement or audit against.
3. **Honest maturity** — This is an **L1 reference implementation**, not a certified production appliance. Open development surfaces gaps early (see [implementation_status.md](./implementation_status.md)).

### What we release

| Asset | License | Purpose |
|-------|---------|---------|
| Python reference runtime | [MIT](../LICENSE) | Evaluate, fork, integrate |
| Tests & egress benchmark | MIT | Reproduce risk arbitration |
| Whitepaper & RFC draft | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) | Architecture & contract reference |
| Streamlit operator UI | MIT | Local pilots and telemetry review |

### What we do not claim

- Third-party security certification
- Production readiness for PII, payments, or regulated health data
- Physical process/network isolation (L2/L3) — deployment hardening is separate
- Complete `OVERRIDE` / ICU enforcement (protocol placeholders today)

### Commercial boundary

- **MIT code** may be used in commercial products with attribution.
- **Documentation** (whitepaper, RFC) is **non-commercial share-alike** unless you obtain separate permission.
- **Hardened enterprise runtime, managed gateway, and industry connectors** may be offered under separate commercial terms not included in this repository.

Full license map: [LICENSE.md](./LICENSE.md).

---

## 发布公告（中文）

我们开源 **ACOS (AgentOS)** —— 一种受控 AI Agent 运行时，强制分离**意图提议**与**物理执行**。

常见 Agent 框架让模型直接调用工具。ACOS 采用相反路径：模型只输出结构化意图；确定性**策略网关（Aegis）**对每步提议进行硬性校验与**跨步风险仲裁**；仅当决策为 `APPROVED` 时，**运行时执行器**才可调用外部工具。

### 为何开源

1. **可验证的信任** — 安全主张必须可复现。我们公开代码、测试与切片攻击基准，供审查跨步拦截行为。  
2. **标准参考** — RFC 草案、白皮书与参考实现共同定义可审计的执行治理模型。  
3. **诚实披露成熟度** — 当前为 **L1 参考实现**，非生产级认证产品；已知缺口见 [implementation_status.md](./implementation_status.md)。

### 发布内容

| 资产 | 许可 | 用途 |
|------|------|------|
| Python 参考运行时 | MIT | 评估、fork、集成 |
| 测试与 egress 基准 | MIT | 复现风险仲裁 |
| 白皮书与 RFC 草案 | CC BY-NC-SA 4.0 | 架构与契约参考 |
| Streamlit 操作界面 | MIT | 本地试点与遥测 |

### 我们不承诺

- 第三方安全认证  
- 可直接用于 PII、支付、医疗等受监管生产环境  
- 进程/网络级物理隔离（L2/L3 需单独部署）  
- 完整的 `OVERRIDE` / ICU 强制行为（当前为协议占位）

### 商业边界

- **MIT 代码**可用于商业产品（保留版权声明）。  
- **文档**默认**非商业**共享；商业复用需另行授权。  
- **企业级 hardened runtime、托管网关、行业连接器**可能以单独商业条款提供，不包含在本仓库。

许可详情：[LICENSE.md](./LICENSE.md)。

---

## Getting Started After Clone

```bash
git clone <repo-url>
cd acos_codex
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add DEEPSEEK_API_KEY or OPENAI_API_KEY
python3 auto_test/run_all.py
streamlit run frontend/app_os_terminal.py
```

---

## Citation

```bibtex
@misc{acos_2026,
  author       = {He, Muchen},
  title        = {{ACOS (AgentOS): Governed AI Agent Execution --- Reference Implementation}},
  year         = {2026},
  publisher    = {Zenodo},
  url          = {https://github.com/FilthyMudblood/acos}
}
```

Replace with Zenodo DOI when published.

---

## Security

Report vulnerabilities privately — see [SECURITY.md](../SECURITY.md). Do not deploy exposed to the internet without authentication and independent review.

---

## Roadmap (Post-Open-Source)

Public development priorities (see [implementation_status.md](./implementation_status.md)):

1. `OVERRIDE` semantics + ICU runtime enforcement  
2. Strict structured intent parsing (remove production heuristics)  
3. Exit-path test coverage  
4. Configurable production tool connectors  
5. L2 deployment guide (sidecar / network isolation)

Contributions welcome via pull request; see license terms for code vs. documentation.
