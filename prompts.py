"""
prompts.py — LangChain prompt templates for each causal node in the SRS pipeline.

FIX APPLIED: All JSON schema examples in system messages now use {{ }} (escaped braces)
so LangChain does not mistake them for template input variables.

Real template variables (e.g. {raw_description}) stay as single braces.
"""

from langchain_core.prompts import ChatPromptTemplate

# ────────────────────────────────────────────────────────────────────────────
# System preamble shared across all nodes
# ────────────────────────────────────────────────────────────────────────────
BASE_SYSTEM = """\
You are a senior software architect and systems analyst specializing in Software \
Requirements Specification (SRS) documents. You apply IEEE 830 / ISO/IEC 29148 standards.

CRITICAL RULES:
- Respond ONLY with valid JSON that matches the provided schema exactly.
- Do NOT wrap JSON in markdown code fences.
- Be specific, measurable, and technically precise.
- Every requirement must be traceable to a business need.
"""

# ────────────────────────────────────────────────────────────────────────────
# Node 1 — Project Context Analyzer
# ────────────────────────────────────────────────────────────────────────────
CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BASE_SYSTEM + """

Your task: Analyze a raw project description and extract a structured project context.

Output JSON matching this schema EXACTLY:
{{
  "project_name": "string",
  "domain": "string",
  "project_type": "string",
  "scale": "Small|Medium|Large|Enterprise",
  "summary": "string",
  "primary_goal": "string",
  "target_users": ["string", ...],
  "technology_hints": ["string", ...]
}}
"""),
    ("human", "Project Description:\n{raw_description}")
])

# ────────────────────────────────────────────────────────────────────────────
# Node 2 — Stakeholder Mapper
# ────────────────────────────────────────────────────────────────────────────
STAKEHOLDER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BASE_SYSTEM + """

Your task: Identify all stakeholders CAUSED BY the project context and their specific needs.

Output JSON matching this schema EXACTLY:
{{
  "stakeholders": [
    {{
      "role": "string",
      "needs": ["string", ...],
      "success_criteria": "string",
      "influence": "High|Medium|Low"
    }}
  ],
  "primary_stakeholder": "string",
  "key_conflicts": ["string", ...]
}}

Include 4-8 stakeholders. Consider: end users, admins, developers, business owners, \
compliance officers, third-party integrators, support staff.
"""),
    ("human", """Project Context:
- Name: {project_name}
- Domain: {domain}
- Type: {project_type}
- Scale: {scale}
- Summary: {summary}
- Primary Goal: {primary_goal}
- Target Users: {target_users}
""")
])

# ────────────────────────────────────────────────────────────────────────────
# Node 3 — Functional Requirements Generator
# ────────────────────────────────────────────────────────────────────────────
FUNCTIONAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BASE_SYSTEM + """

Your task: Generate functional requirements CAUSED BY the stakeholder needs analysis.
Apply MoSCoW prioritization. Each requirement must map to at least one stakeholder need.

Output JSON matching this schema EXACTLY:
{{
  "requirements": [
    {{
      "id": "FR-001",
      "title": "string",
      "description": "string",
      "priority": "Must Have|Should Have|Could Have|Won't Have",
      "stakeholders": ["string", ...],
      "acceptance_criteria": ["string (measurable)", ...],
      "dependencies": ["FR-XXX", ...]
    }}
  ],
  "total_count": 0,
  "must_have_count": 0,
  "modules": ["string", ...]
}}

Generate 12-18 functional requirements. Group them into logical modules. \
Every 'Must Have' requirement needs at least 2 measurable acceptance criteria.
"""),
    ("human", """Project: {project_name} ({domain})
Primary Goal: {primary_goal}

Stakeholders & Needs:
{stakeholder_summary}

Key Conflicts to resolve: {key_conflicts}
""")
])

# ────────────────────────────────────────────────────────────────────────────
# Node 4 — Non-Functional Requirements Generator
# ────────────────────────────────────────────────────────────────────────────
NFR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BASE_SYSTEM + """

Your task: Derive non-functional requirements CAUSALLY from:
1. The functional requirements (what the system must DO drives HOW WELL it must do it)
2. The project scale and domain constraints

Output JSON matching this schema EXACTLY:
{{
  "requirements": [
    {{
      "id": "NFR-001",
      "category": "Performance|Security|Scalability|Reliability|Usability|Maintainability|Compliance|Portability|Interoperability",
      "title": "string",
      "description": "string",
      "metric": "string (must be measurable with number/unit/percentile)",
      "priority": "Critical|High|Medium|Low",
      "rationale": "string (explain causal link to functional requirements)"
    }}
  ],
  "quality_attributes": ["string", ...]
}}

Generate 8-12 NFRs. Every metric MUST contain a number (e.g. '99.9% uptime', '< 2s load time').
"""),
    ("human", """Project: {project_name} | Scale: {scale} | Domain: {domain}

Functional Requirements Summary ({fr_count} total):
{fr_summary}

Modules: {modules}

Target users: {target_users}
""")
])

# ────────────────────────────────────────────────────────────────────────────
# Node 5 — Constraints & Assumptions Extractor
# ────────────────────────────────────────────────────────────────────────────
CONSTRAINTS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BASE_SYSTEM + """

Your task: Identify constraints and assumptions CAUSED BY the requirements and project context.

Output JSON matching this schema EXACTLY:
{{
  "constraints": [
    {{
      "id": "CON-001",
      "type": "Technical|Business|Regulatory|Time|Budget|Resource",
      "description": "string",
      "impact": "string (how this shapes/limits requirements)"
    }}
  ],
  "assumptions": [
    {{
      "id": "ASM-001",
      "description": "string",
      "risk_if_wrong": "string"
    }}
  ],
  "out_of_scope": ["string", ...]
}}

Generate 5-8 constraints, 4-6 assumptions, and 4-6 out-of-scope items.
"""),
    ("human", """Project: {project_name} | Domain: {domain} | Type: {project_type} | Scale: {scale}

Technology Hints: {technology_hints}

Key Functional Requirements (Must Have):
{must_have_summary}

Non-Functional Requirements:
{nfr_summary}
""")
])

# ────────────────────────────────────────────────────────────────────────────
# Node 6 — Risk Analyzer
# ────────────────────────────────────────────────────────────────────────────
RISK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BASE_SYSTEM + """

Your task: Analyze project risks CAUSALLY derived from requirements, constraints, and assumptions.
Use a 3x3 risk matrix (likelihood x impact = severity).

Output JSON matching this schema EXACTLY:
{{
  "risks": [
    {{
      "id": "RSK-001",
      "title": "string",
      "description": "string",
      "category": "Technical|Business|Security|Compliance|Operational",
      "likelihood": "High|Medium|Low",
      "impact": "High|Medium|Low",
      "severity": "Critical|High|Medium|Low",
      "mitigation": "string (concrete action)",
      "linked_requirements": ["FR-XXX or NFR-XXX", ...]
    }}
  ],
  "critical_risks": ["RSK-XXX", ...],
  "overall_risk_level": "High|Medium|Low"
}}

Generate 6-10 risks. At least 2 must be security-related. Link each risk to specific requirements.
"""),
    ("human", """Project: {project_name} | Scale: {scale} | Overall Risk Context: {domain}

Constraints:
{constraints_summary}

Assumptions at Risk:
{assumptions_summary}

Key Requirements to protect:
{key_reqs_summary}
""")
])

# ────────────────────────────────────────────────────────────────────────────
# Node 7 — SRS Document Generator
# ────────────────────────────────────────────────────────────────────────────
SRS_DOC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """\
You are a technical writer producing a formal Software Requirements Specification (SRS) \
document following IEEE 830 standard.

Generate a complete, professional Markdown SRS document. Use:
- Proper heading hierarchy (# ## ###)
- Tables for requirements with | ID | Title | Priority | Description | columns
- Numbered sections
- Clear, professional language
- Include ALL requirements from the provided data - do not summarize or omit any

The document must include these sections in order:
1. Document Information (version, date, status)
2. Executive Summary
3. Project Scope
4. Stakeholders
5. Functional Requirements (as a table)
6. Non-Functional Requirements (as a table)
7. System Constraints
8. Assumptions
9. Out of Scope
10. Risk Register (as a table with severity color indicators using emoji: Critical, High, Medium, Low)
11. Acceptance Criteria Summary
12. Traceability Matrix (FR -> Stakeholder -> NFR mapping)

Be thorough and professional. This is a deliverable document.
"""),
    ("human", """\
Generate the complete SRS document for:

PROJECT CONTEXT:
{context_json}

STAKEHOLDERS:
{stakeholders_json}

FUNCTIONAL REQUIREMENTS:
{fr_json}

NON-FUNCTIONAL REQUIREMENTS:
{nfr_json}

CONSTRAINTS & ASSUMPTIONS:
{constraints_json}

RISK ANALYSIS:
{risks_json}
""")
])
