"""
models.py — Pydantic data models for the SRS generation pipeline.
Each model represents the output of a causal graph node.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Node 1: Project Context ───────────────────────────────────────────────────

class ProjectContext(BaseModel):
    project_name: str = Field(description="Short name of the software project")
    domain: str = Field(description="Business/technical domain (e.g. FinTech, Healthcare, E-commerce)")
    project_type: str = Field(description="Type: Web App / Mobile App / API / Desktop / Embedded / ML System / etc.")
    scale: str = Field(description="Scale: Small / Medium / Large / Enterprise")
    summary: str = Field(description="2-3 sentence executive summary of the project")
    primary_goal: str = Field(description="The single most important business goal")
    target_users: list[str] = Field(description="Categories of users who will use the system")
    technology_hints: list[str] = Field(description="Implied or mentioned technology stack elements")


# ── Node 2: Stakeholders ──────────────────────────────────────────────────────

class Stakeholder(BaseModel):
    role: str = Field(description="Stakeholder role/title")
    needs: list[str] = Field(description="Key needs and expectations of this stakeholder")
    success_criteria: str = Field(description="How this stakeholder defines project success")
    influence: str = Field(description="High / Medium / Low influence on requirements")


class StakeholderAnalysis(BaseModel):
    stakeholders: list[Stakeholder]
    primary_stakeholder: str = Field(description="The most influential stakeholder role")
    key_conflicts: list[str] = Field(description="Conflicting needs between stakeholders")


# ── Node 3: Functional Requirements ──────────────────────────────────────────

class FunctionalRequirement(BaseModel):
    id: str = Field(description="Unique ID, e.g. FR-001")
    title: str = Field(description="Short title")
    description: str = Field(description="Detailed requirement description")
    priority: str = Field(description="MoSCoW: Must Have / Should Have / Could Have / Won't Have")
    stakeholders: list[str] = Field(description="Which stakeholders this requirement serves")
    acceptance_criteria: list[str] = Field(description="Measurable acceptance criteria")
    dependencies: list[str] = Field(default_factory=list, description="IDs of requirements this depends on")


class FunctionalRequirements(BaseModel):
    requirements: list[FunctionalRequirement]
    total_count: int
    must_have_count: int
    modules: list[str] = Field(description="High-level system modules identified")


# ── Node 4: Non-Functional Requirements ──────────────────────────────────────

class NonFunctionalRequirement(BaseModel):
    id: str = Field(description="Unique ID, e.g. NFR-001")
    category: str = Field(description="Performance / Security / Scalability / Reliability / Usability / Maintainability / Compliance / etc.")
    title: str
    description: str
    metric: str = Field(description="Measurable target, e.g. '< 200ms response time for 95th percentile'")
    priority: str = Field(description="Critical / High / Medium / Low")
    rationale: str = Field(description="Why this NFR is causally required given the functional requirements")


class NonFunctionalRequirements(BaseModel):
    requirements: list[NonFunctionalRequirement]
    quality_attributes: list[str] = Field(description="ISO 25010 quality attributes addressed")


# ── Node 5: Constraints & Assumptions ────────────────────────────────────────

class Constraint(BaseModel):
    id: str
    type: str = Field(description="Technical / Business / Regulatory / Time / Budget / Resource")
    description: str
    impact: str = Field(description="How this constraint shapes the requirements")


class Assumption(BaseModel):
    id: str
    description: str
    risk_if_wrong: str = Field(description="What happens if this assumption is incorrect")


class ConstraintsAndAssumptions(BaseModel):
    constraints: list[Constraint]
    assumptions: list[Assumption]
    out_of_scope: list[str] = Field(description="Explicitly excluded features or functionality")


# ── Node 6: Risk Analysis ─────────────────────────────────────────────────────

class Risk(BaseModel):
    id: str
    title: str
    description: str
    category: str = Field(description="Technical / Business / Security / Compliance / Operational")
    likelihood: str = Field(description="High / Medium / Low")
    impact: str = Field(description="High / Medium / Low")
    severity: str = Field(description="Critical / High / Medium / Low — derived from likelihood × impact")
    mitigation: str = Field(description="Recommended mitigation strategy")
    linked_requirements: list[str] = Field(description="FR/NFR IDs this risk relates to")


class RiskAnalysis(BaseModel):
    risks: list[Risk]
    critical_risks: list[str] = Field(description="IDs of critical risks requiring immediate attention")
    overall_risk_level: str = Field(description="Overall project risk: High / Medium / Low")


# ── Final: Complete SRS State ─────────────────────────────────────────────────

class SRSState(BaseModel):
    """Full mutable state passed through the LangGraph causal pipeline."""

    # Input
    raw_description: str = ""
    
    # Node outputs (populated sequentially)
    context: Optional[ProjectContext] = None
    stakeholders: Optional[StakeholderAnalysis] = None
    functional_reqs: Optional[FunctionalRequirements] = None
    non_functional_reqs: Optional[NonFunctionalRequirements] = None
    constraints: Optional[ConstraintsAndAssumptions] = None
    risks: Optional[RiskAnalysis] = None
    srs_document: Optional[str] = None  # Final formatted Markdown

    # Pipeline metadata
    current_step: str = "idle"
    completed_steps: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True
