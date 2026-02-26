import json
import os
import time
from datetime import datetime

import streamlit as st

from graph import PIPELINE_STEPS, build_srs_graph
from models import SRSState
from nodes import PROVIDER_LABELS, PROVIDER_KEY_HELP, PROVIDER_MODELS, configure_llm

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SRS Generator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap');

  /* ── Root tokens ── */
  :root {
    --bg:        #0a0e1a;
    --surface:   #111827;
    --border:    #1e2d45;
    --accent:    #3b82f6;
    --accent2:   #06b6d4;
    --success:   #10b981;
    --warning:   #f59e0b;
    --danger:    #ef4444;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --radius:    12px;
  }

  /* ── Base ── */
  html, body, .stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
  }

  /* ── Hide Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 2rem 2.5rem !important; max-width: 1400px !important; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
  }
  [data-testid="stSidebar"] .stMarkdown p { color: var(--muted) !important; font-size: 0.85rem; }

  /* ── Typography ── */
  h1, h2, h3 {
    font-family: 'DM Serif Display', Georgia, serif !important;
    letter-spacing: -0.02em;
  }

  /* ── Cards ── */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin-bottom: 1rem;
  }
  .card-accent {
    border-left: 3px solid var(--accent);
  }

  /* ── Hero header ── */
  .hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 2.5rem 3rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
    pointer-events: none;
  }
  .hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.6rem;
    line-height: 1.15;
    margin: 0 0 0.5rem;
    background: linear-gradient(135deg, #e2e8f0, #93c5fd);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .hero-sub {
    font-size: 1.05rem;
    color: var(--muted);
    margin: 0;
    font-weight: 300;
  }
  .hero-badge {
    display: inline-block;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.4);
    color: #93c5fd;
    padding: 0.2rem 0.75rem;
    border-radius: 100px;
    font-size: 0.75rem;
    font-family: 'DM Mono', monospace;
    margin-bottom: 1rem;
    letter-spacing: 0.05em;
  }

  /* ── Pipeline steps ── */
  .pipeline-step {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.65rem 0.75rem;
    border-radius: 8px;
    margin-bottom: 0.35rem;
    transition: background 0.2s;
  }
  .step-idle    { opacity: 0.4; }
  .step-active  { background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.3); }
  .step-done    { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); }
  .step-error   { background: rgba(239,68,68,0.08);  border: 1px solid rgba(239,68,68,0.2);  }
  .step-icon    { font-size: 1.1rem; line-height: 1.4; }
  .step-label   { font-weight: 500; font-size: 0.88rem; color: var(--text); }
  .step-desc    { font-size: 0.76rem; color: var(--muted); margin-top: 0.1rem; }

  /* ── Metric tiles ── */
  .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }
  .metric-tile {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
  }
  .metric-value { font-size: 2rem; font-weight: 700; font-family: 'DM Mono', monospace; }
  .metric-label { font-size: 0.75rem; color: var(--muted); margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.08em; }
  .metric-blue  { color: var(--accent); }
  .metric-cyan  { color: var(--accent2); }
  .metric-green { color: var(--success); }
  .metric-amber { color: var(--warning); }

  /* ── Risk badges ── */
  .badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: 'DM Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .badge-critical { background: rgba(239,68,68,0.15);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.3);  }
  .badge-high     { background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.3); }
  .badge-medium   { background: rgba(59,130,246,0.15); color: #93c5fd; border: 1px solid rgba(59,130,246,0.3); }
  .badge-low      { background: rgba(16,185,129,0.15); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.3); }
  .badge-musthave { background: rgba(239,68,68,0.12);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.25); }
  .badge-should   { background: rgba(245,158,11,0.12); color: #fde68a; border: 1px solid rgba(245,158,11,0.25); }
  .badge-could    { background: rgba(59,130,246,0.12); color: #bfdbfe; border: 1px solid rgba(59,130,246,0.25); }
  .badge-wont     { background: rgba(100,116,139,0.2); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }

  /* ── Textarea & inputs ── */
  .stTextArea textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 1rem !important;
  }
  .stTextArea textarea:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important; }

  /* ── Buttons ── */
  .stButton button {
    background: linear-gradient(135deg, #2563eb, #0891b2) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.6rem 1.5rem !important;
    transition: opacity 0.2s !important;
  }
  .stButton button:hover { opacity: 0.88 !important; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    border-radius: 7px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
  }
  .stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: #fff !important;
  }
  .stTabs [data-baseweb="tab-panel"] { padding-top: 1.25rem !important; }

  /* ── Progress bar ── */
  .stProgress > div > div { background: linear-gradient(90deg, var(--accent), var(--accent2)) !important; border-radius: 100px !important; }

  /* ── Expanders ── */
  .streamlit-expanderHeader {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-weight: 500 !important;
  }

  /* ── Info/success/error boxes ── */
  .stAlert { border-radius: var(--radius) !important; }

  /* ── Section divider ── */
  .section-label {
    font-size: 0.7rem;
    font-family: 'DM Mono', monospace;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin: 1.5rem 0 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  /* Selectbox dark */
  .stSelectbox [data-baseweb="select"] > div {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "srs_state":       None,
        "running":         False,
        "step_status":     {s["id"]: "idle" for s in PIPELINE_STEPS},
        "api_key_set":     False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ── Helper: render pipeline sidebar ──────────────────────────────────────────
def render_pipeline_sidebar():
    st.markdown('<div class="section-label">Causal Pipeline</div>', unsafe_allow_html=True)
    for step in PIPELINE_STEPS:
        sid   = step["id"]
        status = st.session_state.step_status.get(sid, "idle")
        css   = f"step-{status}"
        suffix = " ✓" if status == "done" else (" ⏳" if status == "active" else "")
        st.markdown(f"""
        <div class="pipeline-step {css}">
          <span class="step-icon">{step['icon']}</span>
          <div>
            <div class="step-label">{step['label']}{suffix}</div>
            <div class="step-desc">{step['description']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ── Helper: priority badge ────────────────────────────────────────────────────
def priority_badge(p: str) -> str:
    mapping = {
        "Must Have":   ("musthave", "Must Have"),
        "Should Have": ("should",   "Should"),
        "Could Have":  ("could",    "Could"),
        "Won't Have":  ("wont",     "Won't"),
        "Critical":    ("critical", "Critical"),
        "High":        ("high",     "High"),
        "Medium":      ("medium",   "Medium"),
        "Low":         ("low",      "Low"),
    }
    cls, label = mapping.get(p, ("low", p))
    return f'<span class="badge badge-{cls}">{label}</span>'





# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 0.5rem 0 1rem;">
      <div style="font-family:'DM Serif Display',serif; font-size:1.3rem; color:#e2e8f0;">⚙️ Configuration</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Provider selector ────────────────────────────────────────────────────
    st.markdown('<div class="section-label">LLM Provider</div>', unsafe_allow_html=True)

    provider_options = list(PROVIDER_LABELS.keys())
    provider_display = [PROVIDER_LABELS[p] for p in provider_options]

    selected_provider_label = st.selectbox(
        "Provider",
        provider_display,
        index=1,           # default → Groq (free tier)
        label_visibility="collapsed",
    )
    selected_provider = provider_options[provider_display.index(selected_provider_label)]

    # Free-tier callout
    if selected_provider in ("groq", "gemini"):
        st.markdown(
            f'<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);'
            f'border-radius:8px;padding:0.5rem 0.75rem;font-size:0.78rem;color:#6ee7b7;margin-bottom:0.5rem;">'
            f'✅ <b>Free tier available</b> — no billing needed</div>',
            unsafe_allow_html=True,
        )
    elif selected_provider == "ollama":
        st.markdown(
            '<div style="background:rgba(139,92,246,0.1);border:1px solid rgba(139,92,246,0.3);'
            'border-radius:8px;padding:0.5rem 0.75rem;font-size:0.78rem;color:#c4b5fd;margin-bottom:0.5rem;">'
            '🖥️ <b>Fully local</b> — requires Ollama running on your machine</div>',
            unsafe_allow_html=True,
        )
    elif selected_provider == "anthropic":
        st.markdown(
            '<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);'
            'border-radius:8px;padding:0.5rem 0.75rem;font-size:0.78rem;color:#fca5a5;margin-bottom:0.5rem;">'
            '💳 <b>Paid credits required</b> — add credits at console.anthropic.com/billing</div>',
            unsafe_allow_html=True,
        )

    # ── Model selector ───────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Model</div>', unsafe_allow_html=True)
    available_models = PROVIDER_MODELS[selected_provider]
    model_choice = st.selectbox(
        "Model",
        available_models,
        label_visibility="collapsed",
    )

    # ── API Key input ────────────────────────────────────────────────────────
    key_help = PROVIDER_KEY_HELP[selected_provider]
    placeholder_map = {
        "anthropic": "sk-ant-...",
        "groq":      "gsk_...",
        "gemini":    "AIza...",
        "ollama":    "(no key needed)",
    }

    if selected_provider != "ollama":
        st.markdown('<div class="section-label">API Key</div>', unsafe_allow_html=True)
        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder=placeholder_map[selected_provider],
            label_visibility="collapsed",
            help=key_help,
        )
        st.caption(key_help)
    else:
        api_key = ""
        st.markdown('<div class="section-label">Ollama Setup</div>', unsafe_allow_html=True)
        st.caption("Make sure Ollama is running:  `ollama serve`")
        st.caption(f"Model must be pulled first:  `ollama pull {model_choice}`")

    render_pipeline_sidebar()

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem; color:#475569; line-height:1.6;">
      <b style="color:#64748b;">Architecture</b><br>
      LangGraph causal pipeline → 7 sequential nodes → each node's output causally drives the next<br><br>
      <b style="color:#64748b;">Standard</b><br>
      IEEE 830 / ISO/IEC 29148 SRS
    </div>
    """, unsafe_allow_html=True)


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-badge">LangGraph · LangChain · Streamlit · Claude AI</div>
  <h1 class="hero-title">Causal SRS Generator</h1>
  <p class="hero-sub">
    Transform a project description into a complete IEEE 830 Software Requirements Specification
    through a 7-step causal reasoning pipeline — each stage causally derived from the previous.
  </p>
</div>
""", unsafe_allow_html=True)


# ── Input section ─────────────────────────────────────────────────────────────
EXAMPLES = {
    "🏦 FinTech Payment Platform": """We need to build a real-time payment processing platform for a mid-sized bank.
The system must handle peer-to-peer transfers, bill payments, and merchant transactions.
It should support 50,000 concurrent users, integrate with SWIFT and SEPA networks,
comply with PCI-DSS and GDPR regulations, provide fraud detection, and offer both
mobile app and web portal interfaces. Expected transaction volume: 2M transactions/day.""",

    "🏥 Healthcare Appointment System": """A regional hospital network needs a digital appointment management system
for 15 hospitals and 300+ clinics. The system must allow patients to book, reschedule
and cancel appointments online, support telemedicine video consultations, integrate
with existing EMR systems (Epic/Cerner), send automated reminders via SMS/email,
provide doctor scheduling tools, and ensure HIPAA compliance. Expected: 100K patients.""",

    "🛒 E-Commerce Marketplace": """Build a multi-vendor e-commerce marketplace similar to Etsy for handmade goods.
Sellers can list products, manage inventory, and process orders. Buyers get personalized
recommendations, secure checkout, and order tracking. The platform needs a review system,
seller analytics dashboard, dispute resolution, and integration with Stripe and PayPal.
Target: 10,000 sellers, 500,000 buyers in the first year.""",

    "🤖 ML Model Monitoring Platform": """An enterprise AI team needs a platform to monitor deployed ML models in production.
The system should track model drift, data quality, prediction accuracy, and latency in real-time.
It needs alerting, A/B testing support, model versioning, automated retraining triggers,
and a dashboard for data scientists. Must integrate with AWS SageMaker, Azure ML,
and Kubernetes deployments. Handles 100+ production models.""",
}

col_input, col_example = st.columns([3, 1])
with col_example:
    st.markdown('<div class="section-label">Quick Examples</div>', unsafe_allow_html=True)
    selected_example = st.selectbox(
        "Load example",
        ["— select —"] + list(EXAMPLES.keys()),
        label_visibility="collapsed",
    )
    if selected_example != "— select —":
        st.session_state["loaded_example"] = EXAMPLES[selected_example]

with col_input:
    st.markdown('<div class="section-label">Project Description</div>', unsafe_allow_html=True)
    default_text = st.session_state.get("loaded_example", "")
    description = st.text_area(
        "Describe your software project",
        value=default_text,
        height=180,
        placeholder="Describe the software system you want to build...\n\nInclude: business goals, target users, key features, scale, integrations, compliance needs, etc.",
        label_visibility="collapsed",
    )

# ── Generate button ───────────────────────────────────────────────────────────
st.markdown("")
col_btn, col_hint = st.columns([2, 5])
with col_btn:
    generate_clicked = st.button(
        "🚀 Generate SRS Document",
        use_container_width=True,
        disabled=st.session_state.running,
    )
with col_hint:
    st.markdown("""
    <div style="padding-top:0.7rem; color:#475569; font-size:0.85rem;">
      7 causal reasoning steps · ~2–3 min · IEEE 830 output
    </div>
    """, unsafe_allow_html=True)


# ── Run pipeline ──────────────────────────────────────────────────────────────
if generate_clicked:
    if selected_provider != "ollama" and not api_key:
        st.error(f"⚠️  Please enter your {PROVIDER_LABELS[selected_provider]} API key in the sidebar.")
    elif not description.strip():
        st.error("⚠️  Please enter a project description.")
    else:
        with st.spinner(""):
            progress_bar = st.progress(0, text="Starting causal pipeline...")
            status_text  = st.empty()

            def update_ui(step_idx: int, label: str):
                pct = int((step_idx / len(PIPELINE_STEPS)) * 100)
                progress_bar.progress(pct, text=f"Step {step_idx}/{len(PIPELINE_STEPS)}: {label}")
                status_text.markdown(
                    f'<div style="color:#64748b; font-size:0.85rem; font-family:\'DM Mono\',monospace;">⏳ {label}</div>',
                    unsafe_allow_html=True
                )

            step_ids = [s["id"] for s in PIPELINE_STEPS]

            # Mark first step active
            st.session_state.step_status[step_ids[0]] = "active"

            # ── Configure the LLM provider for all nodes ──────────────────
            configure_llm(
                provider=selected_provider,
                model=model_choice,
                api_key=api_key,
            )

            from graph import build_srs_graph
            from models import SRSState

            graph = build_srs_graph()
            initial_state = SRSState(raw_description=description).model_dump()
            final_state = initial_state

            for i, chunk in enumerate(graph.stream(initial_state)):
                node_name = list(chunk.keys())[0]
                node_state = list(chunk.values())[0]

                if node_name in step_ids:
                    st.session_state.step_status[node_name] = "done"
                    idx = step_ids.index(node_name)
                    if idx + 1 < len(step_ids):
                        st.session_state.step_status[step_ids[idx + 1]] = "active"
                    update_ui(idx + 1, PIPELINE_STEPS[idx]["label"] + " complete")

                final_state = node_state

            st.session_state.srs_state = final_state
            st.session_state.step_status = {s: "done" for s in step_ids}
            progress_bar.progress(100, text="✅ SRS generation complete!")
            status_text.empty()

        st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.srs_state:
    raw = st.session_state.srs_state
    srs = SRSState(**raw) if isinstance(raw, dict) else raw

    if srs.errors:
        for err in srs.errors:
            st.error(f"Pipeline error: {err}")

    if srs.context:
        # ── Metrics bar ──────────────────────────────────────────────────────
        fr_count  = srs.functional_reqs.total_count if srs.functional_reqs else 0
        nfr_count = len(srs.non_functional_reqs.requirements) if srs.non_functional_reqs else 0
        risk_count = len(srs.risks.risks) if srs.risks else 0
        sh_count  = len(srs.stakeholders.stakeholders) if srs.stakeholders else 0

        st.markdown(f"""
        <div class="metric-grid">
          <div class="metric-tile">
            <div class="metric-value metric-blue">{fr_count}</div>
            <div class="metric-label">Functional Reqs</div>
          </div>
          <div class="metric-tile">
            <div class="metric-value metric-cyan">{nfr_count}</div>
            <div class="metric-label">Non-Functional Reqs</div>
          </div>
          <div class="metric-tile">
            <div class="metric-value metric-green">{sh_count}</div>
            <div class="metric-label">Stakeholders</div>
          </div>
          <div class="metric-tile">
            <div class="metric-value metric-amber">{risk_count}</div>
            <div class="metric-label">Risks Identified</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📄 SRS Document",
        "⚙️ Functional Reqs",
        "📊 Non-Functional Reqs",
        "👥 Stakeholders",
        "⚠️ Risks",
        "🚧 Constraints",
        "🔍 Pipeline Data",
    ])

    # ── Tab 1: SRS Document ──────────────────────────────────────────────────
    with tabs[0]:
        if srs.srs_document:
            col_dl, col_copy = st.columns([1, 1])
            with col_dl:
                ts = datetime.now().strftime("%Y%m%d_%H%M")
                name = (srs.context.project_name.replace(" ", "_") if srs.context else "project")
                st.download_button(
                    "⬇️ Download SRS (.md)",
                    data=srs.srs_document,
                    file_name=f"SRS_{name}_{ts}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with col_copy:
                st.download_button(
                    "⬇️ Download as JSON",
                    data=json.dumps(srs.model_dump(), indent=2, default=str),
                    file_name=f"SRS_{name}_{ts}.json",
                    mime="application/json",
                    use_container_width=True,
                )

            st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
            st.markdown(srs.srs_document)
        else:
            st.info("SRS document not yet generated.")

    # ── Tab 2: Functional Requirements ───────────────────────────────────────
    with tabs[1]:
        if srs.functional_reqs:
            fr = srs.functional_reqs
            st.markdown(f'<div class="section-label">Modules: {" · ".join(fr.modules)}</div>', unsafe_allow_html=True)

            # Filter by priority
            prio_filter = st.multiselect(
                "Filter by priority",
                ["Must Have", "Should Have", "Could Have", "Won't Have"],
                default=["Must Have", "Should Have"],
            )

            for req in fr.requirements:
                if req.priority not in prio_filter:
                    continue
                with st.expander(f"{req.id} — {req.title}  {req.priority}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Description:** {req.description}")
                        if req.acceptance_criteria:
                            st.markdown("**Acceptance Criteria:**")
                            for ac in req.acceptance_criteria:
                                st.markdown(f"- ✅ {ac}")
                    with col2:
                        st.markdown(priority_badge(req.priority), unsafe_allow_html=True)
                        if req.stakeholders:
                            st.caption("Stakeholders: " + ", ".join(req.stakeholders[:3]))
                        if req.dependencies:
                            st.caption("Depends on: " + ", ".join(req.dependencies))
        else:
            st.info("Functional requirements not yet generated.")

    # ── Tab 3: Non-Functional Requirements ───────────────────────────────────
    with tabs[2]:
        if srs.non_functional_reqs:
            nfr = srs.non_functional_reqs

            st.markdown(
                f'<div class="section-label">Quality Attributes: {" · ".join(nfr.quality_attributes)}</div>',
                unsafe_allow_html=True
            )

            # Group by category
            from collections import defaultdict
            by_cat = defaultdict(list)
            for r in nfr.requirements:
                by_cat[r.category].append(r)

            for cat, reqs in sorted(by_cat.items()):
                st.markdown(f"### {cat}")
                for r in reqs:
                    with st.expander(f"{r.id} — {r.title}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Description:** {r.description}")
                            st.markdown(f"**Metric:** `{r.metric}`")
                            st.markdown(f"**Rationale:** _{r.rationale}_")
                        with col2:
                            st.markdown(priority_badge(r.priority), unsafe_allow_html=True)
        else:
            st.info("NFRs not yet generated.")

    # ── Tab 4: Stakeholders ───────────────────────────────────────────────────
    with tabs[3]:
        if srs.stakeholders:
            sh = srs.stakeholders
            if sh.key_conflicts:
                st.warning("**Key Conflicts:** " + " | ".join(sh.key_conflicts))

            cols = st.columns(2)
            for i, stakeholder in enumerate(sh.stakeholders):
                with cols[i % 2]:
                    influence_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}.get(stakeholder.influence, "#64748b")
                    st.markdown(f"""
                    <div class="card card-accent">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <b style="font-size:1rem;">{stakeholder.role}</b>
                        <span style="color:{influence_color}; font-size:0.75rem; font-family:'DM Mono',monospace; font-weight:600;">{stakeholder.influence.upper()} INFLUENCE</span>
                      </div>
                      <div style="font-size:0.85rem; color:#64748b; margin-bottom:0.75rem;"><i>{stakeholder.success_criteria}</i></div>
                      <div style="font-size:0.82rem;">{''.join(f'<div style="margin-bottom:0.25rem;">• {n}</div>' for n in stakeholder.needs)}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Stakeholder analysis not yet generated.")

    # ── Tab 5: Risks ──────────────────────────────────────────────────────────
    with tabs[4]:
        if srs.risks:
            ra = srs.risks
            overall_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}.get(ra.overall_risk_level, "#64748b")
            st.markdown(
                f'<div style="margin-bottom:1rem;">Overall Project Risk: <b style="color:{overall_color};">{ra.overall_risk_level}</b></div>',
                unsafe_allow_html=True
            )

            sev_filter = st.multiselect(
                "Filter by severity",
                ["Critical", "High", "Medium", "Low"],
                default=["Critical", "High"],
            )

            for r in ra.risks:
                if r.severity not in sev_filter:
                    continue
                icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(r.severity, "⚪")
                with st.expander(f"{icon} {r.id} — {r.title}  ({r.category})", expanded=r.severity == "Critical"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Description:** {r.description}")
                        st.markdown(f"**Mitigation:** _{r.mitigation}_")
                        if r.linked_requirements:
                            st.caption("Linked: " + ", ".join(r.linked_requirements))
                    with col2:
                        st.markdown(priority_badge(r.severity), unsafe_allow_html=True)
                        st.caption(f"Likelihood: {r.likelihood}")
                        st.caption(f"Impact: {r.impact}")
        else:
            st.info("Risk analysis not yet generated.")

    # ── Tab 6: Constraints ────────────────────────────────────────────────────
    with tabs[5]:
        if srs.constraints:
            ca = srs.constraints

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🚧 Constraints")
                for c in ca.constraints:
                    type_color = {"Technical": "#3b82f6", "Business": "#f59e0b", "Regulatory": "#ef4444", "Time": "#8b5cf6", "Budget": "#10b981", "Resource": "#64748b"}.get(c.type, "#64748b")
                    st.markdown(f"""
                    <div class="card" style="padding:1rem;">
                      <div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.4rem;">
                        <span style="font-size:0.7rem;font-family:'DM Mono',monospace;color:{type_color};text-transform:uppercase;font-weight:700;">{c.id} · {c.type}</span>
                      </div>
                      <div style="font-size:0.88rem;margin-bottom:0.3rem;">{c.description}</div>
                      <div style="font-size:0.78rem;color:#64748b;font-style:italic;">{c.impact}</div>
                    </div>
                    """, unsafe_allow_html=True)

            with col2:
                st.markdown("### 💭 Assumptions")
                for a in ca.assumptions:
                    st.markdown(f"""
                    <div class="card" style="padding:1rem;">
                      <div style="font-size:0.7rem;font-family:'DM Mono',monospace;color:#8b5cf6;margin-bottom:0.4rem;">{a.id}</div>
                      <div style="font-size:0.88rem;margin-bottom:0.3rem;">{a.description}</div>
                      <div style="font-size:0.78rem;color:#f59e0b;">⚠ If wrong: {a.risk_if_wrong}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("### 🚫 Out of Scope")
            for item in ca.out_of_scope:
                st.markdown(f"- ~~{item}~~")
        else:
            st.info("Constraints not yet generated.")

    # ── Tab 7: Pipeline Data (debug) ──────────────────────────────────────────
    with tabs[6]:
        st.markdown("### Raw Pipeline State (JSON)")
        st.caption("Full structured data produced by the causal pipeline — useful for integration or debugging.")

        sections = {
            "🔍 Project Context":          srs.context,
            "👥 Stakeholder Analysis":     srs.stakeholders,
            "⚙️ Functional Requirements":  srs.functional_reqs,
            "📊 Non-Functional Reqs":      srs.non_functional_reqs,
            "🚧 Constraints & Assumptions": srs.constraints,
            "⚠️ Risk Analysis":            srs.risks,
        }
        for label, obj in sections.items():
            if obj:
                with st.expander(label):
                    st.json(obj.model_dump())


# ── Empty state ───────────────────────────────────────────────────────────────
elif not st.session_state.running:
    st.markdown("""
    <div style="text-align:center; padding:3rem 2rem; color:#475569;">
      <div style="font-size:3.5rem; margin-bottom:1rem;">📋</div>
      <div style="font-family:'DM Serif Display',serif; font-size:1.5rem; color:#64748b; margin-bottom:0.5rem;">
        Ready to Generate
      </div>
      <div style="font-size:0.9rem; max-width:480px; margin:0 auto; line-height:1.7;">
        Enter your project description above and click <b>Generate SRS Document</b>.<br>
        The causal pipeline will analyze your requirements through 7 sequential reasoning steps.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards
    feat_cols = st.columns(3)
    features = [
        ("🔗", "Causal Reasoning", "Each requirement is causally derived from the previous analysis stage — no hallucinated requirements."),
        ("📐", "IEEE 830 Standard", "Output follows the IEEE 830 / ISO/IEC 29148 SRS standard with full traceability."),
        ("🎯", "MoSCoW Prioritization", "Every functional requirement is prioritized using MoSCoW methodology with measurable acceptance criteria."),
    ]
    for col, (icon, title, desc) in zip(feat_cols, features):
        with col:
            st.markdown(f"""
            <div class="card" style="text-align:center; padding:1.5rem 1.25rem;">
              <div style="font-size:2rem; margin-bottom:0.75rem;">{icon}</div>
              <div style="font-weight:600; margin-bottom:0.4rem;">{title}</div>
              <div style="font-size:0.82rem; color:#64748b;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
