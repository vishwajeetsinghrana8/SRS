"""
graph.py — LangGraph causal pipeline for SRS generation.

Graph topology (sequential causal chain):
    START
      │
      ▼
  [analyze_context]          ← parses raw description
      │
      ▼
  [map_stakeholders]         ← caused by: project context
      │
      ▼
  [generate_functional_reqs] ← caused by: stakeholder needs
      │
      ▼
  [generate_nfr]             ← caused by: functional requirements
      │
      ▼
  [extract_constraints]      ← caused by: FR + NFR + project context
      │
      ▼
  [analyze_risks]            ← caused by: constraints + assumptions
      │
      ▼
  [generate_srs_document]    ← synthesizes all previous nodes
      │
      ▼
     END
"""

from langgraph.graph import END, START, StateGraph

from nodes import (
    make_safe_node,
    node_analyze_context,
    node_analyze_risks,
    node_extract_constraints,
    node_generate_functional_reqs,
    node_generate_nfr,
    node_generate_srs_document,
    node_map_stakeholders,
)


# ── Build the causal graph ────────────────────────────────────────────────────

def build_srs_graph() -> StateGraph:
    """
    Construct and compile the LangGraph causal pipeline.
    Each node's output is the causal input for the next node.
    """
    graph = StateGraph(dict)

    # Register nodes (wrapped with error handling)
    graph.add_node("analyze_context",          make_safe_node(node_analyze_context))
    graph.add_node("map_stakeholders",         make_safe_node(node_map_stakeholders))
    graph.add_node("generate_functional_reqs", make_safe_node(node_generate_functional_reqs))
    graph.add_node("generate_nfr",             make_safe_node(node_generate_nfr))
    graph.add_node("extract_constraints",      make_safe_node(node_extract_constraints))
    graph.add_node("analyze_risks",            make_safe_node(node_analyze_risks))
    graph.add_node("generate_srs_document",    make_safe_node(node_generate_srs_document))

    # Causal edge chain
    graph.add_edge(START,                      "analyze_context")
    graph.add_edge("analyze_context",          "map_stakeholders")
    graph.add_edge("map_stakeholders",         "generate_functional_reqs")
    graph.add_edge("generate_functional_reqs", "generate_nfr")
    graph.add_edge("generate_nfr",             "extract_constraints")
    graph.add_edge("extract_constraints",      "analyze_risks")
    graph.add_edge("analyze_risks",            "generate_srs_document")
    graph.add_edge("generate_srs_document",    END)

    return graph.compile()


# ── Pipeline steps metadata (for UI progress display) ────────────────────────

PIPELINE_STEPS = [
    {
        "id": "analyze_context",
        "label": "Context Analysis",
        "icon": "🔍",
        "description": "Extracting domain, scale, project type and goals",
    },
    {
        "id": "map_stakeholders",
        "label": "Stakeholder Mapping",
        "icon": "👥",
        "description": "Identifying stakeholders and their needs",
    },
    {
        "id": "generate_functional_reqs",
        "label": "Functional Requirements",
        "icon": "⚙️",
        "description": "Generating FR with MoSCoW prioritization",
    },
    {
        "id": "generate_nfr",
        "label": "Non-Functional Requirements",
        "icon": "📊",
        "description": "Deriving NFRs from functional requirements",
    },
    {
        "id": "extract_constraints",
        "label": "Constraints & Assumptions",
        "icon": "🚧",
        "description": "Identifying constraints, assumptions, out-of-scope",
    },
    {
        "id": "analyze_risks",
        "label": "Risk Analysis",
        "icon": "⚠️",
        "description": "Causal risk assessment with mitigation strategies",
    },
    {
        "id": "generate_srs_document",
        "label": "SRS Document",
        "icon": "📄",
        "description": "Assembling IEEE 830 compliant SRS document",
    },
]
