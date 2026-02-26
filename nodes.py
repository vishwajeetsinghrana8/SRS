"""
nodes.py — LangGraph node functions for the causal SRS generation pipeline.

UPDATED: Multi-provider LLM support.
  - Anthropic Claude  (paid, requires credits)
  - Groq              (FREE tier — llama-3.3-70b, mixtral)
  - Google Gemini     (FREE tier — gemini-1.5-flash, gemini-2.0-flash)
  - Ollama            (FREE, fully local — no API key needed)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

from langchain_core.output_parsers import StrOutputParser

from models import (
    ConstraintsAndAssumptions,
    FunctionalRequirements,
    NonFunctionalRequirements,
    ProjectContext,
    RiskAnalysis,
    SRSState,
    StakeholderAnalysis,
)
from prompts import (
    CONSTRAINTS_PROMPT,
    CONTEXT_PROMPT,
    FUNCTIONAL_PROMPT,
    NFR_PROMPT,
    RISK_PROMPT,
    STAKEHOLDER_PROMPT,
    SRS_DOC_PROMPT,
)

# ── Provider type ─────────────────────────────────────────────────────────────
Provider = Literal["anthropic", "groq", "gemini", "ollama"]

# ── Model catalogues per provider ─────────────────────────────────────────────
PROVIDER_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "groq": [
        "llama-3.3-70b-versatile",   # best free model for structured output
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ],
    "ollama": [
        "llama3.2",
        "llama3.1",
        "mistral",
        "qwen2.5",
    ],
}

PROVIDER_LABELS: dict[str, str] = {
    "anthropic": "Anthropic Claude",
    "groq":      "Groq  (FREE tier)",
    "gemini":    "Google Gemini  (FREE tier)",
    "ollama":    "Ollama  (FREE · local)",
}

PROVIDER_KEY_HELP: dict[str, str] = {
    "anthropic": "Get key → console.anthropic.com  |  Requires paid credits",
    "groq":      "Get FREE key → console.groq.com  |  Generous free tier",
    "gemini":    "Get FREE key → aistudio.google.com  |  Free tier available",
    "ollama":    "No API key needed — Ollama must be running locally (ollama serve)",
}


# ── LLM factory ───────────────────────────────────────────────────────────────

def get_llm(
    provider: Provider = "anthropic",
    model: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
):
    """Return the appropriate LangChain chat model for the given provider."""

    if model is None:
        model = PROVIDER_MODELS[provider][0]

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            anthropic_api_key=key,
        )

    elif provider == "groq":
        from langchain_groq import ChatGroq
        key = api_key or os.environ.get("GROQ_API_KEY", "")
        return ChatGroq(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            groq_api_key=key,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=key,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            temperature=temperature,
            num_predict=max_tokens,
        )

    else:
        raise ValueError(f"Unknown provider: {provider!r}")


def get_doc_llm(provider: Provider = "anthropic", model: str | None = None, api_key: str | None = None):
    """Higher token budget for the final document generation node."""
    return get_llm(provider=provider, model=model, api_key=api_key,
                   temperature=0.2, max_tokens=8192)


# ── JSON extraction helper ─────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    """
    Robustly extract JSON from an LLM response.
    Handles: plain JSON, ```json fences, ``` fences, and leading/trailing noise.
    """
    text = text.strip()

    # Strip markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first { ... } or [ ... ] block
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end   = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract valid JSON from response:\n{text[:300]}")


# ── Shared LLM config (set by app.py before pipeline runs) ───────────────────
# We use a module-level dict so all nodes pick up the same settings without
# threading each value through the LangGraph state dict.

_LLM_CONFIG: dict = {
    "provider":  "anthropic",
    "model":     "claude-opus-4-6",
    "api_key":   "",
}

def configure_llm(provider: Provider, model: str, api_key: str) -> None:
    """Call this once before running the graph to set the active LLM."""
    _LLM_CONFIG["provider"] = provider
    _LLM_CONFIG["model"]    = model
    _LLM_CONFIG["api_key"]  = api_key

    # Also set the standard env-var so LangChain sub-libraries are happy
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "groq":      "GROQ_API_KEY",
        "gemini":    "GOOGLE_API_KEY",
        "ollama":    None,
    }
    env_var = env_map.get(provider)
    if env_var and api_key:
        os.environ[env_var] = api_key


def _llm(**kwargs):
    return get_llm(
        provider=_LLM_CONFIG["provider"],
        model=_LLM_CONFIG["model"],
        api_key=_LLM_CONFIG["api_key"],
        **kwargs,
    )

def _doc_llm():
    return get_doc_llm(
        provider=_LLM_CONFIG["provider"],
        model=_LLM_CONFIG["model"],
        api_key=_LLM_CONFIG["api_key"],
    )


# ── Node 1: Context Analyzer ───────────────────────────────────────────────────

def node_analyze_context(state: dict) -> dict:
    srs = SRSState(**state)
    srs.current_step = "Analyzing project context..."

    chain    = CONTEXT_PROMPT | _llm() | StrOutputParser()
    response = chain.invoke({"raw_description": srs.raw_description})

    srs.context = ProjectContext(**extract_json(response))
    srs.completed_steps.append("context")
    srs.current_step = "Context analysis complete"
    return srs.model_dump()


# ── Node 2: Stakeholder Mapper ─────────────────────────────────────────────────

def node_map_stakeholders(state: dict) -> dict:
    srs = SRSState(**state)
    srs.current_step = "Mapping stakeholders..."

    ctx   = srs.context
    chain = STAKEHOLDER_PROMPT | _llm() | StrOutputParser()
    response = chain.invoke({
        "project_name": ctx.project_name,
        "domain":       ctx.domain,
        "project_type": ctx.project_type,
        "scale":        ctx.scale,
        "summary":      ctx.summary,
        "primary_goal": ctx.primary_goal,
        "target_users": ", ".join(ctx.target_users),
    })

    srs.stakeholders = StakeholderAnalysis(**extract_json(response))
    srs.completed_steps.append("stakeholders")
    srs.current_step = "Stakeholder mapping complete"
    return srs.model_dump()


# ── Node 3: Functional Requirements ───────────────────────────────────────────

def node_generate_functional_reqs(state: dict) -> dict:
    srs = SRSState(**state)
    srs.current_step = "Generating functional requirements..."

    ctx = srs.context
    sh  = srs.stakeholders

    stakeholder_summary = "\n".join(
        f"- {s.role} ({s.influence} influence): {'; '.join(s.needs[:3])}"
        for s in sh.stakeholders
    )

    chain    = FUNCTIONAL_PROMPT | _llm() | StrOutputParser()
    response = chain.invoke({
        "project_name":       ctx.project_name,
        "domain":             ctx.domain,
        "primary_goal":       ctx.primary_goal,
        "stakeholder_summary": stakeholder_summary,
        "key_conflicts":      "; ".join(sh.key_conflicts),
    })

    srs.functional_reqs = FunctionalRequirements(**extract_json(response))
    srs.completed_steps.append("functional_reqs")
    srs.current_step = "Functional requirements complete"
    return srs.model_dump()


# ── Node 4: Non-Functional Requirements ───────────────────────────────────────

def node_generate_nfr(state: dict) -> dict:
    srs = SRSState(**state)
    srs.current_step = "Deriving non-functional requirements..."

    ctx = srs.context
    fr  = srs.functional_reqs

    fr_summary = "\n".join(
        f"- [{r.id}] {r.title} ({r.priority}): {r.description[:100]}..."
        for r in fr.requirements[:10]
    )

    chain    = NFR_PROMPT | _llm() | StrOutputParser()
    response = chain.invoke({
        "project_name": ctx.project_name,
        "scale":        ctx.scale,
        "domain":       ctx.domain,
        "fr_count":     fr.total_count,
        "fr_summary":   fr_summary,
        "modules":      ", ".join(fr.modules),
        "target_users": ", ".join(ctx.target_users),
    })

    srs.non_functional_reqs = NonFunctionalRequirements(**extract_json(response))
    srs.completed_steps.append("non_functional_reqs")
    srs.current_step = "Non-functional requirements complete"
    return srs.model_dump()


# ── Node 5: Constraints & Assumptions ─────────────────────────────────────────

def node_extract_constraints(state: dict) -> dict:
    srs = SRSState(**state)
    srs.current_step = "Extracting constraints and assumptions..."

    ctx = srs.context
    fr  = srs.functional_reqs
    nfr = srs.non_functional_reqs

    must_have_summary = "\n".join(
        f"- [{r.id}] {r.title}: {r.description[:80]}"
        for r in fr.requirements if r.priority == "Must Have"
    )[:8]

    nfr_summary = "\n".join(
        f"- [{r.id}] {r.category} — {r.title}: {r.metric}"
        for r in nfr.requirements
    )

    chain    = CONSTRAINTS_PROMPT | _llm() | StrOutputParser()
    response = chain.invoke({
        "project_name":      ctx.project_name,
        "domain":            ctx.domain,
        "project_type":      ctx.project_type,
        "scale":             ctx.scale,
        "technology_hints":  ", ".join(ctx.technology_hints),
        "must_have_summary": must_have_summary,
        "nfr_summary":       nfr_summary,
    })

    srs.constraints = ConstraintsAndAssumptions(**extract_json(response))
    srs.completed_steps.append("constraints")
    srs.current_step = "Constraints and assumptions complete"
    return srs.model_dump()


# ── Node 6: Risk Analysis ──────────────────────────────────────────────────────

def node_analyze_risks(state: dict) -> dict:
    srs = SRSState(**state)
    srs.current_step = "Analyzing project risks..."

    ctx = srs.context
    ca  = srs.constraints
    fr  = srs.functional_reqs
    nfr = srs.non_functional_reqs

    constraints_summary = "\n".join(
        f"- [{c.id}] {c.type}: {c.description}" for c in ca.constraints
    )
    assumptions_summary = "\n".join(
        f"- [{a.id}] {a.description} -> Risk if wrong: {a.risk_if_wrong}"
        for a in ca.assumptions
    )
    key_reqs = "\n".join(
        f"- [{r.id}] {r.title}"
        for r in (
            [r for r in fr.requirements if r.priority == "Must Have"][:5]
            + [r for r in nfr.requirements if r.priority == "Critical"]
        )
    )

    chain    = RISK_PROMPT | _llm() | StrOutputParser()
    response = chain.invoke({
        "project_name":       ctx.project_name,
        "scale":              ctx.scale,
        "domain":             ctx.domain,
        "constraints_summary": constraints_summary,
        "assumptions_summary": assumptions_summary,
        "key_reqs_summary":   key_reqs,
    })

    srs.risks = RiskAnalysis(**extract_json(response))
    srs.completed_steps.append("risks")
    srs.current_step = "Risk analysis complete"
    return srs.model_dump()


# ── Node 7: SRS Document Generator ────────────────────────────────────────────

def node_generate_srs_document(state: dict) -> dict:
    srs = SRSState(**state)
    srs.current_step = "Generating SRS document..."

    def to_json(obj: Any) -> str:
        return json.dumps(obj.model_dump(), indent=2) if obj else "{}"

    chain    = SRS_DOC_PROMPT | _doc_llm() | StrOutputParser()
    response = chain.invoke({
        "context_json":      to_json(srs.context),
        "stakeholders_json": to_json(srs.stakeholders),
        "fr_json":           to_json(srs.functional_reqs),
        "nfr_json":          to_json(srs.non_functional_reqs),
        "constraints_json":  to_json(srs.constraints),
        "risks_json":        to_json(srs.risks),
    })

    srs.srs_document = response
    srs.completed_steps.append("srs_document")
    srs.current_step = "complete"
    return srs.model_dump()


# ── Error handler ──────────────────────────────────────────────────────────────

def make_safe_node(node_fn):
    """Wrap a node with error handling so one failure doesn't crash the graph."""
    def safe_node(state: dict) -> dict:
        try:
            return node_fn(state)
        except Exception as e:
            srs = SRSState(**state)
            srs.errors.append(f"Error in {node_fn.__name__}: {str(e)}")
            srs.current_step = f"Error: {str(e)[:120]}"
            return srs.model_dump()
    safe_node.__name__ = node_fn.__name__
    return safe_node
