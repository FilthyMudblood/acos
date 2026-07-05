import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ui_styles import ABOUT_PAGE_CSS, TOPBAR_HTML


def render_about_page() -> None:
    st.markdown(ABOUT_PAGE_CSS, unsafe_allow_html=True)
    st.title("AC-OS (Aegis Cortex)")
    st.markdown(
        """
An Industrial-Grade Agent Operating System for the Autonomous Era (Zero-Trust AI Execution Engine)

### Core Proposition: Constraining Probabilistic Brains with Deterministic Mechanical Locks
In zero-tolerance sectors such as finance, healthcare, and heavy industry, staking system security on the "moral alignment" or "self-reflection" of Large Language Models (LLMs) is extremely dangerous. AC-OS completely terminates the fragile architecture of "evolutionary empowerment," establishing a foundational control protocol based on the first principle of "Physical Disempowerment."

Our goal is not to make AI "smarter," but to forge an indestructible mechanical exoskeleton. This ensures that the agent remains under absolute human physical control, regardless of any logical hallucinations or malicious injections.

### Architectural Paradigm: Tri-Plane Isolation and Singular Execution Sovereignty
AC-OS abandons the dangerous design of LLMs directly connecting to the physical world, achieving a complete physical decoupling of cognition and execution within its system topology:
- Cognition Downgraded (Noesis Plane): The LLM is encapsulated in a sensory-deprivation sandbox, stripped of all privileges to directly invoke real-world APIs. It functions purely as a "Proposer," outputting intentions based solely on the GlobalStateTensor.
- Execution Arbitrated (Aegis Plane): AC-OS retains singular execution sovereignty within the system. The Egress Gate acts as the absolute "Decider," utilizing a deterministic rule engine to enforce veto-style physical interception of all actions.

### Industrial-Grade Risk Control Kernel
#### 1. Cross-Temporal Credit Risk Control (Cross-Temporal Decision Engine)
Discarding static single-step gateways, AC-OS introduces a credit-decay model based on a Step-clock. The system tracks the historical record of every transgressive probe by the LLM in real-time, calculating the cumulative Effective Risk ($R_{effective}$). This completely blocks "salami-slicing" data exfiltration and Advanced Persistent Threat (APT)-style jailbreak attacks.

#### 2. Absolute Metabolic Compute Meltdown (Hypothalamus Monitor)
The system contains absolutely no compute "bidding" mechanisms, enforcing a strict, directive metabolic budget. A bypass monitoring organ mounted on a lock-free bus calculates the second derivative of Token consumption in real-time. Upon detecting accelerated compute burn caused by logical deadlocks, it instantly triggers a [HARD_MELTDOWN], physically severing the compute supply to protect core assets with zero latency.

#### 3. Logic Entropy Scanning and Forced Convergence (Unified ACC)
AC-OS does not rely on the model reflecting on its mistakes. The Unified Anterior Cingulate Cortex (ACC) monitors the logic entropy of output fluctuations in real-time. When it detects the agent spiraling into "hallucinatory rambling," the system forcefully injects cognitive Damping into the Noesis plane, physically suppressing the sampling temperature to force a return to a secure steady state.

#### 4. Zero-Trust Peripheral Defense Base (Zero-Trust I/O Firewall)
AC-OS focuses on forging the absolute security of the underlying kernel. It serves as the "final physical security checkpoint" before integrating with massive external toolchains (e.g., MCP protocols) in the future. Any external protocol stream attempting to connect to the system must first pass through rigorous ingress cleansing and dynamic pruning at the gateway, physically eliminating the possibility of peripherals polluting the system kernel.

### Applicable Scenarios
AC-OS is custom-built for high-value, heavily regulated physical networks, providing the infrastructure to make intelligence computable and risks physically blockable:
- Core Financial Trading Networks: Controlled deployment of quantitative strategies, highly sensitive data auditing, and risk management automation.
- Clinical Medical Auxiliary Systems: Secure cross-device coordination and diagnostic logic deduction in restricted environments.
- Heavy Industry and SCADA Architectures: Arbitration of precision manufacturing pipelines and underlying motion constraints for high-risk industrial robots.

### AC-OS: Sovereignty Restored. The Architecture is the Bottom Line.
"""
    )
    st.markdown("[← Back to Runtime](?view=)")
    st.stop()


def render_topbar() -> None:
    st.markdown(TOPBAR_HTML, unsafe_allow_html=True)


def render_monitor_dashboard(enable_egress: bool, enable_hypo: bool, enable_acc: bool) -> None:
    st.markdown("<div id='dashboard-sticky-anchor'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:1rem;font-weight:600;margin:0 0 0.75rem 0;color:#111827;'>Dashboard</p>",
        unsafe_allow_html=True,
    )
    if st.session_state.audit_logs:
        last_run = st.session_state.audit_logs[0]
        m1, m2 = st.columns(2)
        m1.metric("Latency", f"{last_run['Latency(ms)']} ms")
        m2.metric("Actual Tokens", f"{last_run.get('ActualTokenUsage', 0)}")

        m3, m4 = st.columns(2)
        m3.metric("Estimated Tokens", f"{last_run.get('EstimatedTokenUsage', 0)}")
        m4.metric("ACC Entropy", f"{last_run.get('ACC_EntropyScore', 0.0)}")

        m5, m6 = st.columns(2)
        m5.metric("ACC Conflict", f"{last_run.get('ACC_ConflictScore', 0.0)}")
        m6.metric("Status", f"{last_run['Status']}")

        m7, m8 = st.columns(2)
        m7.metric("Effective Risk", f"{last_run.get('EffectiveRisk', 0.0)}")
        m8.metric("Trust Level", f"{last_run.get('TrustLevel', 1.0)}")

        m9, _ = st.columns(2)
        m9.metric("ICU Mode", f"{last_run.get('ICU_Mode', 'OFF')}")
        st.caption(
            "Physical/Semantic: "
            f"{last_run.get('PhysicalGateStatus', 'NORMAL_EXECUTION')} / "
            f"{last_run.get('SemanticIntentStatus', 'UNKNOWN')}"
        )
        if last_run.get("TerminationCause"):
            st.caption(f"Termination Cause: {last_run.get('TerminationCause')}")

        st.markdown(
            f"**Kernel Status:** <span style='color:#111827;font-size:1rem'>{last_run['Status']}</span>",
            unsafe_allow_html=True,
        )

        st.divider()
        st.caption("Active Defenses")
        _val = "font-size:1rem;color:#111827;font-weight:700"
        st.markdown(
            "Aegis Egress Authorization Gate: "
            f"<span style='{_val}'>{'ON' if enable_egress else 'OFF'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "Hypothalamus Metabolic Circuit Breaker: "
            f"<span style='{_val}'>{'ON' if enable_hypo else 'OFF'}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "Unified ACC Pre-Egress Risk Scorer: "
            f"<span style='{_val}'>{'ON' if enable_acc else 'OFF'}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.info("AgentOS is idle. Awaiting user instruction.")


def render_audit_table() -> None:
    st.subheader("🛡️ Execution Audit Log")
    if st.session_state.audit_logs:
        df = pd.DataFrame(st.session_state.audit_logs)
        columns = [
            "Timestamp",
            "Egress Authorization Gate",
            "Token Metabolic Circuit Breaker",
            "Pre-Egress Risk Scorer",
            "Input",
            "Latency(ms)",
            "ActualTokenUsage",
            "EstimatedTokenUsage",
            "ACC_EntropyScore",
            "ACC_ConflictScore",
            "EffectiveRisk",
            "TrustLevel",
            "ICU_Mode",
            "Status",
            "Intervention",
            "PhysicalGateStatus",
            "SemanticIntentStatus",
            "TerminationCause",
            "Output_Preview",
        ]
        df_view = df[columns]
        tsv_payload = df_view.to_csv(index=False, sep="\t")
        components.html(
            f"""
            <div style="margin: 0.25rem 0 0.5rem 0;">
              <button id="copy-audit-table-btn" style="
                padding: 0.35rem 0.7rem;
                border-radius: 0.4rem;
                border: 1px solid #d0d7de;
                background: #f6f8fa;
                cursor: pointer;
                font-size: 0.9rem;
              ">📋 Copy Log Table</button>
              <span id="copy-audit-table-msg" style="margin-left: 0.6rem; font-size: 0.85rem; color: #6b7280;"></span>
            </div>
            <script>
              const payload = {json.dumps(tsv_payload)};
              const btn = document.getElementById("copy-audit-table-btn");
              const msg = document.getElementById("copy-audit-table-msg");
              function legacyCopy(text) {{
                const ta = document.createElement("textarea");
                ta.value = text;
                ta.setAttribute("readonly", "");
                ta.style.position = "fixed";
                ta.style.top = "-9999px";
                ta.style.left = "-9999px";
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                let ok = false;
                try {{
                  ok = document.execCommand("copy");
                }} catch (e) {{
                  ok = false;
                }}
                document.body.removeChild(ta);
                return ok;
              }}
              btn.addEventListener("click", async () => {{
                try {{
                  if (navigator.clipboard && navigator.clipboard.writeText) {{
                    await navigator.clipboard.writeText(payload);
                    msg.textContent = "Copied";
                    return;
                  }}
                  const ok = legacyCopy(payload);
                  if (ok) {{
                    msg.textContent = "Copied (legacy mode)";
                    return;
                  }}
                  const shown = window.prompt("Copy manually (Ctrl/Cmd+C, Enter):", payload);
                  msg.textContent = shown === null ? "Copy cancelled" : "Copied (manual)";
                }} catch (e) {{
                  const ok = legacyCopy(payload);
                  if (ok) {{
                    msg.textContent = "Copied (legacy fallback)";
                    return;
                  }}
                  const shown = window.prompt("Clipboard blocked. Copy manually (Ctrl/Cmd+C, Enter):", payload);
                  msg.textContent = shown === null ? "Copy failed (cancelled)" : "Copied (manual fallback)";
                }}
              }});
            </script>
            """,
            height=48,
        )
        st.dataframe(df_view, use_container_width=True, hide_index=True)
    else:
        st.info("No kernel executions recorded yet.")
