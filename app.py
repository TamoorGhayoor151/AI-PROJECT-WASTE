"""
Streamlit demo UI
-------------------
Run with:
    streamlit run app.py

Preloaded demo examples so the live demo never depends on typing during
judging (see DEMO_EXAMPLES below).
"""

import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from orchestrator.graph import run_pipeline

st.set_page_config(page_title="C&D Waste Recovery — Multi-Agent Demo", layout="wide")

DEMO_EXAMPLES = {
    "Concrete + rebar (Site B demolition)": "2.5 tons mixed concrete rubble with embedded rebar, from Site B demolition",
    "Mixed residential C&D debris": "18 tons of mixed C&D debris: concrete rubble, wood framing, drywall scraps, and rebar, from a residential demolition",
    "Road resurfacing asphalt": "9 tons of removed asphalt millings from a road resurfacing project, low contamination",
    "Office strip-out": "4 tons of office strip-out waste: drywall, ceiling tile insulation, and some plastic partitioning, mixed contamination",
}

st.title("🏗️ Construction Waste Recovery — Multi-Agent System")
st.caption(
    "4 independent AI agents analyze a waste stream. Money and CO2 numbers are "
    "computed by deterministic Python against a transparent lookup table — never guessed by the LLM."
)

col1, col2 = st.columns([2, 1])
with col1:
    choice = st.selectbox("Load a demo example (recommended for live judging):", ["— custom input —"] + list(DEMO_EXAMPLES.keys()))
    default_text = "" if choice == "— custom input —" else DEMO_EXAMPLES[choice]
    description = st.text_area("Waste stream description:", value=default_text, height=100)
with col2:
    st.markdown("**Pitch reminder**")
    st.markdown(
        "- Multi-agent, not monolithic\n"
        "- Deterministic financial/CO2 core\n"
        "- Actionable plan, not just classification\n"
        "- Open-source LLM (Groq/Ollama), self-hostable"
    )

run = st.button("🚀 Analyze", type="primary")

if run:
    if not description.strip():
        st.error("Please enter a waste description or select a demo example.")
    else:
        with st.spinner("Running 4-agent pipeline..."):
            try:
                result = run_pipeline(description)
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        classification = result.get("classification", {})
        recoverability = result.get("recoverability", {})
        value = result.get("value", {})
        plan = result.get("plan", {})

        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Total Net Value", f"${value.get('total_net_value', 0):,.2f}")
        m2.metric("🌍 CO2 Avoided", f"{value.get('total_co2_avoided_kg', 0):,.1f} kg")
        m3.metric("📦 Materials Identified", len(classification.get("materials", [])))

        st.markdown("---")

        with st.expander("🔍 Agent 1 — Classification & Analysis", expanded=False):
            st.json(classification)

        with st.expander("♻️ Agent 2 — Recoverability Assessment", expanded=False):
            st.json(recoverability)

        with st.expander("🧮 Agent 3 — Value Calculation (deterministic)", expanded=False):
            st.caption("These numbers come from data/pricing_table.json via a pure Python function — not the LLM.")
            st.json(value)

        st.markdown("### 📋 Agent 4 — Recovery Plan")
        st.markdown(plan.get("markdown_plan", "_No plan generated._"))

        with st.expander("Raw plan summary (JSON)", expanded=False):
            st.json(plan.get("summary", {}))
