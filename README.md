# 📋 Causal SRS Generator

> An LLM application that transforms a project description into a complete **IEEE 830 Software Requirements Specification** through a 7-step causal reasoning pipeline built with **LangGraph**, **LangChain**, and **Streamlit**.

---

## 🏗 Architecture

```
User Input (project description)
        │
        ▼
┌─────────────────────────────────────────────┐
│         LangGraph Causal Pipeline           │
│                                             │
│  [1] Context Analyzer                       │
│       ↓ (causes)                            │
│  [2] Stakeholder Mapper                     │
│       ↓ (causes)                            │
│  [3] Functional Requirements Generator      │
│       ↓ (causes)                            │
│  [4] Non-Functional Requirements Deriver    │
│       ↓ (causes)                            │
│  [5] Constraints & Assumptions Extractor    │
│       ↓ (causes)                            │
│  [6] Risk Analyzer                          │
│       ↓ (causes)                            │
│  [7] SRS Document Generator                 │
└─────────────────────────────────────────────┘
        │
        ▼
   IEEE 830 SRS Document (Markdown + JSON)
```

Each node's output **causally drives** the next — stakeholder needs cause functional requirements, which cause NFRs, which cause constraints to be identified, which cause risks to be assessed.

---

## 📁 Project Structure

```
srs_generator/
├── app.py            ← Streamlit frontend (UI, tabs, pipeline runner)
├── graph.py          ← LangGraph pipeline definition & topology
├── nodes.py          ← 7 pipeline node functions (LangChain chains)
├── prompts.py        ← Structured LangChain prompt templates
├── models.py         ← Pydantic data models for each pipeline stage
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Get an API Key

Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key.

### 3. Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### 4. Generate an SRS

1. Paste or type your project description (or use a built-in example)
2. Enter your Anthropic API key in the sidebar
3. Click **Generate SRS Document**
4. Watch the 7-step pipeline run live
5. Explore tabs or download the Markdown/JSON output

---

## 🔧 Framework Roles

| Framework | Role |
|---|---|
| **LangGraph** | Orchestrates the causal 7-node DAG pipeline; streams node results |
| **LangChain** | `ChatAnthropic` LLM wrapper, `ChatPromptTemplate`, `StrOutputParser` |
| **Streamlit** | Full-stack web UI: input, live pipeline status, tabbed results |
| **Pydantic v2** | Strict type-validated models for each pipeline stage output |

---

## 📊 Pipeline Stages

| # | Node | Input | Output |
|---|---|---|---|
| 1 | Context Analyzer | Raw description | Domain, scale, goals, users |
| 2 | Stakeholder Mapper | Project context | Stakeholders, needs, conflicts |
| 3 | Functional Reqs | Stakeholder needs | FR-001…FR-018 with MoSCoW |
| 4 | Non-Functional Reqs | Functional reqs | NFR-001…NFR-012 with metrics |
| 5 | Constraints | FR + NFR + context | Technical, business, regulatory |
| 6 | Risk Analysis | Constraints + assumptions | Risk matrix with mitigations |
| 7 | SRS Document | All previous | Full IEEE 830 Markdown doc |

---

## 📤 Output Formats

- **SRS Markdown** — Downloadable `.md` IEEE 830 document with tables, traceability matrix, risk register
- **JSON Export** — Full structured pipeline state for integration into other tools

---

## ⚙️ Configuration

| Option | Values |
|---|---|
| Model | `claude-opus-4-6` (best), `claude-sonnet-4-6` (faster), `claude-haiku-4-5-20251001` (cheapest) |
| API Key | Enter in sidebar or set `ANTHROPIC_API_KEY` env var |

---

## 📋 Example SRS Sections Generated

1. Document Information
2. Executive Summary
3. Project Scope
4. Stakeholder Analysis
5. Functional Requirements Table (with IDs, MoSCoW, acceptance criteria)
6. Non-Functional Requirements Table (with measurable metrics)
7. System Constraints
8. Assumptions
9. Out of Scope
10. Risk Register (🔴🟠🟡🟢 severity)
11. Acceptance Criteria Summary
12. Requirements Traceability Matrix

---

## 🛠 Requirements

- Python **3.10+**
- `anthropic >= 0.40.0`
- `langchain >= 0.3.0`
- `langchain-anthropic >= 0.3.0`
- `langgraph >= 0.2.0`
- `streamlit >= 1.40.0`
- `pydantic >= 2.0.0`
