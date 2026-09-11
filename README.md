# Multi-Agent Construction Waste Recovery System

A hackathon prototype: 4 independent, specialized AI agents analyze a construction &
demolition (C&D) waste stream and produce a prioritized, monetized recovery plan.

**Core differentiator:** LLM agents handle language, reasoning, and classification.
All money/CO2 math is computed by deterministic Python functions against a transparent
lookup table (`data/pricing_table.json`) — never hallucinated by the LLM. This is what
makes the system auditable: a judge can open that JSON file and verify every number.

## Architecture

```
Waste Input → Orchestrator (LangGraph) → Final Recovery Plan (JSON + Markdown)
                    │
   ┌────────────────┼────────────────┬────────────────┐
   ▼                ▼                ▼                ▼
Agent 1:        Agent 2:         Agent 3:         Agent 4:
Classification  Recoverability   Value Calc       Recovery Plan
(LLM)           (LLM + lookup)   (DETERMINISTIC)  (LLM)
```

| Agent | File | Uses LLM? |
|---|---|---|
| 1. Classification | `agents/classification_agent.py` | Yes |
| 2. Recoverability | `agents/recoverability_agent.py` | Yes, grounded by `data/recovery_rules.json` |
| 3. Value Calculation | `agents/value_agent.py` | **No — pure Python, unit-tested** |
| 4. Recovery Plan | `agents/plan_agent.py` | Yes, but forbidden from inventing numbers |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env and add your free Groq API key from https://console.groq.com
```

## Run the deterministic core (no API key needed)

```bash
python -m pytest tests/ -v
python agents/value_agent.py
```

## Run the full API

```bash
uvicorn api.main:app --reload --port 8000
```

Test it:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"description": "2.5 tons mixed concrete rubble with embedded rebar, from Site B demolition"}'
```

## Run the Streamlit demo UI

```bash
streamlit run app.py
```

Select a preloaded demo example (recommended for live judging so the demo never
depends on typing on stage) or type your own waste description, then click Analyze.

## Offline fallback (no internet / bad wifi at venue)

Install [Ollama](https://ollama.com) and pull a local model:
```bash
ollama pull llama3.1:8b
```
Then swap `ChatGroq(...)` for `ChatOllama(model="llama3.1:8b")` (from
`langchain-ollama`) in each agent file — the rest of the pipeline is unchanged
since every agent has a strict JSON contract regardless of which LLM backs it.

## Project structure

```
construction-waste-recovery/
├── data/
│   ├── pricing_table.json      # auditable $ + CO2 rates per material
│   └── recovery_rules.json     # auditable recovery pathway rules
├── agents/
│   ├── classification_agent.py
│   ├── recoverability_agent.py
│   ├── value_agent.py          # deterministic — no LLM
│   └── plan_agent.py
├── orchestrator/
│   └── graph.py                # LangGraph wiring
├── api/
│   └── main.py                 # FastAPI app
├── tests/
│   └── test_value_agent.py     # unit tests for the deterministic core
├── app.py                      # Streamlit UI
├── .env.example
└── requirements.txt
```

## Pitch angle (for slides)

- **Multi-agent, not monolithic** — each agent is independently testable and
  swappable; show the LangGraph diagram.
- **Deterministic core** — money/CO2 numbers come from an auditable lookup
  table, not an LLM guess. This is the trust/explainability story.
- **Actionable, not just descriptive** — output is a plan a site manager
  could execute today.
- **Open-source & self-hostable** — runs on Llama/Qwen via Groq or local
  Ollama, no dependency on closed APIs.
- **Scalable** — same pipeline works per line-item or aggregated across an
  entire site manifest (`run_pipeline_batch`).

## Stretch goals (if time remains)

- Photo-based classification via a vision-capable open model
- PDF export of the final recovery plan
- Multi-item site-level dashboard with charts
- Confidence flag routing low-confidence classifications to human review
