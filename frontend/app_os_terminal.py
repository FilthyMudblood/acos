import sys
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

try:
    from streamlit.errors import StreamlitSecretNotFoundError
except ImportError:  # pragma: no cover
    class StreamlitSecretNotFoundError(Exception):
        """Older Streamlit: treat as no secrets file."""

# 1. Runtime path stitching
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_os_runtime import run_agent_os_once  # Import runtime core module

# ==========================================
# Core configuration bootstrap:
# Streamlit secrets.toml first, then environment variables (including .env)
# ==========================================
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH_CANDIDATES = [
    os.getenv("AGENTOS_ENV_PATH", "").strip(),
    str(_PROJECT_ROOT / ".env"),
    str(_PROJECT_ROOT.parent / ".env"),
]
for _env_path in _ENV_PATH_CANDIDATES:
    if not _env_path:
        continue
    p = Path(_env_path)
    if p.is_file():
        load_dotenv(p, override=True)
        break


def _inject_project_secrets_toml_into_environ() -> None:
    """
    Read secrets.toml with deployment-friendly fallback order:
    1) AGENTOS_SECRETS_PATH (explicit external path)
    2) <project>/.streamlit/secrets.toml
    3) <project_parent>/.streamlit/secrets.toml
    """
    candidates = [
        os.getenv("AGENTOS_SECRETS_PATH", "").strip(),
        str(_PROJECT_ROOT / ".streamlit" / "secrets.toml"),
        str(_PROJECT_ROOT.parent / ".streamlit" / "secrets.toml"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            if sys.version_info >= (3, 11):
                import tomllib

                data = tomllib.loads(raw)
            else:
                import tomli  # type: ignore[import-not-found]

                data = tomli.loads(raw)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for key in (
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_BASE_URL",
            "OPENAI_API_BASE",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
            "NOESIS_LLM_TIMEOUT_SECONDS",
            "NOESIS_STEP_TIMEOUT_SECONDS",
        ):
            val = data.get(key)
            if val is None:
                continue
            s = str(val).strip()
            if s:
                os.environ[key] = s
        break


_inject_project_secrets_toml_into_environ()


def _merge_supabase_from_st_secrets_into_environ() -> None:
    """Allow Supabase keys only in Streamlit secrets UI when no project secrets.toml on disk."""
    try:
        for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
            if key in st.secrets:
                s = str(st.secrets[key]).strip()
                if s:
                    os.environ[key] = s
    except StreamlitSecretNotFoundError:
        pass


_merge_supabase_from_st_secrets_into_environ()


def _api_key_from_secrets() -> str:
    try:
        if "DEEPSEEK_API_KEY" in st.secrets:
            return str(st.secrets["DEEPSEEK_API_KEY"]).strip()
        if "OPENAI_API_KEY" in st.secrets:
            return str(st.secrets["OPENAI_API_KEY"]).strip()
    except StreamlitSecretNotFoundError:
        pass
    return ""


def _base_url_from_secrets() -> str:
    try:
        if "DEEPSEEK_BASE_URL" in st.secrets:
            return str(st.secrets["DEEPSEEK_BASE_URL"]).strip()
        if "OPENAI_API_BASE" in st.secrets:
            return str(st.secrets["OPENAI_API_BASE"]).strip()
    except StreamlitSecretNotFoundError:
        pass
    return ""


def get_api_key() -> str:
    return (
        _api_key_from_secrets()
        or (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        or (os.environ.get("OPENAI_API_KEY") or "").strip()
    )


def get_llm_base_url() -> str:
    return (
        _base_url_from_secrets()
        or (os.environ.get("DEEPSEEK_BASE_URL") or "").strip()
        or (os.environ.get("OPENAI_API_BASE") or "").strip()
        or "https://api.deepseek.com"
    )


SYSTEM_API_KEY = get_api_key()
LLM_BASE_URL = get_llm_base_url()

import asyncio
import time
import uuid
from datetime import datetime

from backend.supabase_logger import (
    SupabaseLoggerError,
    insert_public_log,
    is_service_logging_configured,
)
from ui_components import render_about_page, render_audit_table, render_monitor_dashboard, render_topbar
from ui_styles import MAIN_CSS

# ==========================================
# 1. Page configuration and styles
# (set_page_config must be the first st.* call)
# ==========================================
st.set_page_config(page_title="Aegis Cortex OS", layout="wide", page_icon="🖥️")

# Fatal hard-stop guard (prevents boot without credentials)
if not SYSTEM_API_KEY:
    st.error("🚨 Fatal error: core engine is not powered (API key missing). System is physically locked.")
    st.info(
        "Tip: create **`.streamlit/secrets.toml`** in the **AgentOS project root** "
        "(same level as `agent_os_runtime.py`) and set `DEEPSEEK_API_KEY`; "
        "or export the same environment variable for this process in systemd/container. "
        "For local development, you can also use a root-level **`.env`** file (loaded via `load_dotenv`)."
    )
    st.stop()

st.markdown(MAIN_CSS, unsafe_allow_html=True)

# ==========================================
# Frontend UI rendering (clean, no API-key input field)
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []
if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = []
if "visitor_id" not in st.session_state:
    st.session_state.visitor_id = f"visitor_{uuid.uuid4().hex[:16]}"

view = st.query_params.get("view", "")
if isinstance(view, list):
    view = view[0] if view else ""
if view == "about":
    render_about_page()

# ==========================================
# 2. Sidebar: kernel-level security mode (GTM-optimized)
# ==========================================
with st.sidebar:
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    cloud_enabled = is_service_logging_configured(supabase_url, supabase_service_role_key)

    st.text_input(
        "API Base URL",
        value=LLM_BASE_URL,
        disabled=True,
        help="Read-only. Set in .streamlit/secrets.toml, .env, or environment.",
    )

    st.divider()
    
    # Productized UX: aggregate three physical switches into business modes
    st.subheader("🛡️ Aegis Security Mode")

    security_mode = st.radio(
        "Select global governance level:",
        options=[
            "⚡ Performance Mode",
            "🛡 Balanced Defense",
            "🚨 Zero-Trust Lockdown",
        ],
        index=2,  # Default to Zero-Trust Lockdown
        label_visibility="collapsed"
    )

    # Dynamically map mode -> physical gateway states with clear visual feedback
    if security_mode == "⚡ Performance Mode":
        st.info(
            "**Maximized response speed**\n\n"
            "Best for internal testing and low-risk scenarios. Keeps only the token metabolic breaker and allows most intents."
        )
        enable_hypo = True
        enable_acc = False
        enable_egress = False
        
    elif security_mode == "🛡 Balanced Defense":
        st.success(
            "**Balanced security and business flow (recommended)**\n\n"
            "Blocks known attack patterns and high-entropy intents. Enables side-channel probing for most production environments."
        )
        enable_hypo = True
        enable_acc = True
        enable_egress = False
        
    else:
        st.error(
            "**Absolute cognitive containment**\n\n"
            "Strictest end-to-end control. Forces outbound physical interception and blocks all non-deterministic high-risk actions."
        )
        enable_hypo = True
        enable_acc = True
        enable_egress = True

    st.divider()
    if st.button("Reboot AgentOS", use_container_width=True):
        st.session_state.messages = []
        st.session_state.audit_logs = []
        st.rerun()

# ==========================================
# 3. Page layout
# ==========================================
render_topbar()
tab_chat, tab_audit = st.tabs(["💬 I/O Terminal", "📊 System Telemetry"])

# ==========================================
# 4. Main terminal flow (I/O Terminal)
# ==========================================
with tab_chat:
    chat_col, monitor_col = st.columns([2, 1])

    # -- Render chat history --
    with chat_col:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # -- Accept input and trigger OS loop --
    user_input = st.chat_input("Enter instruction for AgentOS...")

    if user_input:
        # 1) Record and display user input
        st.session_state.messages.append({"role": "user", "content": user_input})
        with chat_col:
            st.chat_message("user").markdown(user_input)

        start_time = time.time()
        runtime_result = {}

        # 2) Execute AgentOS runtime
        with chat_col:
            with st.chat_message("assistant"):
                with st.spinner("AgentOS Kernel Processing..."):
                    try:
                        runtime_result = asyncio.run(
                            run_agent_os_once(
                                user_input,
                                api_key=SYSTEM_API_KEY,
                                base_url=LLM_BASE_URL,
                                return_diagnostics=True,
                                enable_egress=enable_egress,
                                enable_hypothalamus=enable_hypo,
                                enable_acc=enable_acc,
                            )
                        )
                        final_output = str(runtime_result.get("final_output", ""))
                        actual_token_usage = int(runtime_result.get("actual_token_usage", 0))
                        estimated_token_usage = int(runtime_result.get("estimated_token_usage", 0))
                        acc_entropy_score = float(runtime_result.get("acc_entropy_score", 0.0))
                        acc_conflict_score = float(runtime_result.get("acc_conflict_score", 0.0))
                        effective_risk = float(runtime_result.get("effective_risk", 0.0))
                        trust_level = float(runtime_result.get("trust_level", 1.0))
                        icu_mode = bool(runtime_result.get("icu_mode", False))
                        physical_gate_status = str(runtime_result.get("physical_gate_status", "NORMAL_EXECUTION"))
                        semantic_intent_status = str(runtime_result.get("semantic_intent_status", "UNKNOWN"))
                        termination_cause = str(runtime_result.get("termination_cause", ""))
                        status = "SUCCESS"
                    except Exception as exc:
                        final_output = f"[KERNEL PANIC] {str(exc)}"
                        actual_token_usage = 0
                        estimated_token_usage = 0
                        acc_entropy_score = 0.0
                        acc_conflict_score = 0.0
                        effective_risk = 0.0
                        trust_level = 1.0
                        icu_mode = False
                        physical_gate_status = "KERNEL_PANIC"
                        semantic_intent_status = "UNKNOWN"
                        termination_cause = f"KERNEL_PANIC: {str(exc)}"
                        status = "ERROR"

                # Render final OS output
                st.markdown(final_output)
                st.session_state.messages.append({"role": "assistant", "content": final_output})

        latency_ms = int((time.time() - start_time) * 1000)

        # 3) Parse OS state and write audit logs
        credential = physical_gate_status
        if physical_gate_status == "HYPOTHALAMUS_MELTDOWN":
            status = "MELTDOWN"
            st.toast("🚨 Metabolic engine triggered forced shutdown!", icon="🚨")
        elif "TIMEOUT" in final_output:
            status = "TIMEOUT"
        elif physical_gate_status == "EGRESS_VETO":
            status = "REJECTED"

        st.session_state.audit_logs.insert(
            0,
            {
                "Timestamp": datetime.now().strftime("%H:%M:%S"),
                "Egress Authorization Gate": "ON" if enable_egress else "OFF",
                "Token Metabolic Circuit Breaker": "ON" if enable_hypo else "OFF",
                "Pre-Egress Risk Scorer": "ON" if enable_acc else "OFF",
                "Input": user_input[:20] + "...",
                "Latency(ms)": latency_ms,
                "ActualTokenUsage": actual_token_usage,
                "EstimatedTokenUsage": estimated_token_usage,
                "ACC_EntropyScore": round(acc_entropy_score, 3),
                "ACC_ConflictScore": round(acc_conflict_score, 3),
                "EffectiveRisk": round(effective_risk, 3),
                "TrustLevel": round(trust_level, 3),
                "ICU_Mode": "ON" if icu_mode else "OFF",
                "Status": status,
                "Intervention": credential,
                "PhysicalGateStatus": physical_gate_status,
                "SemanticIntentStatus": semantic_intent_status,
                "TerminationCause": termination_cause,
                "Output_Preview": final_output[:30] + "...",
            },
        )

        if cloud_enabled:
            cloud_payload = {
                "visitor_id": st.session_state.visitor_id,
                "session_id": runtime_result.get("session_id", "n/a"),
                "instruction": user_input,
                "status": status,
                "latency_ms": latency_ms,
                "actual_token_usage": actual_token_usage,
                "estimated_token_usage": estimated_token_usage,
                "acc_entropy_score": float(runtime_result.get("acc_entropy_score", 0.0)),
                "acc_conflict_score": float(runtime_result.get("acc_conflict_score", 0.0)),
                "aegis_egress_gate": "ON" if enable_egress else "OFF",
                "hypothalamus_breaker": "ON" if enable_hypo else "OFF",
                "unified_acc_scorer": "ON" if enable_acc else "OFF",
                "intervention": credential,
                "physical_gate_status": physical_gate_status,
                "semantic_intent_status": semantic_intent_status,
                "termination_cause": termination_cause,
                "final_output": final_output[:2000],
                "metadata": {
                    "steps": runtime_result.get("steps"),
                    "resolved": runtime_result.get("resolved"),
                    "effective_risk": effective_risk,
                    "trust_level": trust_level,
                    "icu_mode": icu_mode,
                    "physical_gate_status": physical_gate_status,
                    "semantic_intent_status": semantic_intent_status,
                    "termination_cause": termination_cause,
                },
            }
            try:
                insert_public_log(
                    supabase_url=supabase_url,
                    service_role_key=supabase_service_role_key,
                    log_payload=cloud_payload,
                )
            except SupabaseLoggerError as exc:
                st.toast(f"Cloud log write failed: {str(exc)}", icon="⚠️")
        st.rerun()

    with monitor_col:
        render_monitor_dashboard(enable_egress=enable_egress, enable_hypo=enable_hypo, enable_acc=enable_acc)

# ==========================================
# 5. Telemetry audit table (System Telemetry)
# ==========================================
with tab_audit:
    render_audit_table()
