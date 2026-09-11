import os
import json
import re
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from groq import Groq
except ImportError:
    Groq = None


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="C&D Waste Recovery — Multi-Agent AI",
    page_icon="🏗️",
    layout="wide",
)


# ============================================================
# DEMO EXAMPLES
# ============================================================

DEMO_EXAMPLES = {
    "Concrete + rebar — Site B demolition":
        "2.5 tons mixed concrete rubble with embedded rebar, "
        "from Site B demolition",

    "Mixed residential C&D debris":
        "18 tons of mixed C&D debris: concrete rubble, "
        "wood framing, drywall scraps, and rebar, "
        "from a residential demolition",

    "Road resurfacing asphalt":
        "9 tons of removed asphalt millings from a road "
        "resurfacing project, low contamination",

    "Office strip-out":
        "4 tons of office strip-out waste: drywall, "
        "ceiling tile, insulation, and plastic partitioning, "
        "mixed contamination",
}


# ============================================================
# PRICING / ENVIRONMENTAL LOOKUP TABLE
# ============================================================
#
# These are illustrative demo assumptions.
# They are NOT live market prices.
#
# price_per_ton:
#     potential recovered-material selling/reuse value
#
# processing_cost_per_ton:
#     estimated processing cost
#
# co2_avoided_kg_per_ton:
#     illustrative avoided CO2 impact
#
# ============================================================

PRICING_TABLE = {
    "concrete": {
        "price_per_ton": 18,
        "processing_cost_per_ton": 7,
        "co2_avoided_kg_per_ton": 120,
    },

    "rebar": {
        "price_per_ton": 280,
        "processing_cost_per_ton": 55,
        "co2_avoided_kg_per_ton": 1400,
    },

    "steel": {
        "price_per_ton": 280,
        "processing_cost_per_ton": 55,
        "co2_avoided_kg_per_ton": 1400,
    },

    "asphalt": {
        "price_per_ton": 25,
        "processing_cost_per_ton": 8,
        "co2_avoided_kg_per_ton": 80,
    },

    "wood": {
        "price_per_ton": 45,
        "processing_cost_per_ton": 20,
        "co2_avoided_kg_per_ton": 500,
    },

    "drywall": {
        "price_per_ton": 12,
        "processing_cost_per_ton": 8,
        "co2_avoided_kg_per_ton": 100,
    },

    "plastic": {
        "price_per_ton": 80,
        "processing_cost_per_ton": 35,
        "co2_avoided_kg_per_ton": 800,
    },

    "mixed_c&d": {
        "price_per_ton": 10,
        "processing_cost_per_ton": 8,
        "co2_avoided_kg_per_ton": 50,
    },
}


# ============================================================
# GROQ API KEY
# ============================================================

def get_groq_api_key():

    api_key = os.getenv("GROQ_API_KEY")

    if api_key:
        return api_key

    try:
        api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        api_key = None

    return api_key


# ============================================================
# GROQ CLIENT
# ============================================================

def get_groq_client():

    api_key = get_groq_api_key()

    if not api_key:
        return None

    if Groq is None:
        return None

    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):

    if not text:
        raise ValueError("Empty AI response.")

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # Direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        json_text = text[start:end + 1]

        return json.loads(json_text)

    raise ValueError(
        "Could not extract valid JSON from AI response."
    )


# ============================================================
# AGENT 1
# MATERIAL CLASSIFICATION
# ============================================================

def classification_agent(description):

    client = get_groq_client()

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if client is None:

        text = description.lower()

        materials = []

        # Extract approximate total quantity
        quantity_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:tons?|tonnes?)",
            text,
        )

        total_quantity = (
            float(quantity_match.group(1))
            if quantity_match
            else 1.0
        )

        detected = []

        if "concrete" in text:
            detected.append("concrete")

        if "rebar" in text:
            detected.append("rebar")

        if "steel" in text:
            detected.append("steel")

        if "asphalt" in text:
            detected.append("asphalt")

        if "wood" in text:
            detected.append("wood")

        if "drywall" in text:
            detected.append("drywall")

        if "plastic" in text:
            detected.append("plastic")

        if not detected:
            detected.append("mixed_c&d")

        share = total_quantity / len(detected)

        for material in detected:

            contamination = "medium"

            if "low contamination" in text:
                contamination = "low"

            elif "high contamination" in text:
                contamination = "high"

            materials.append(
                {
                    "material": material,
                    "estimated_quantity_tons": round(
                        share,
                        2,
                    ),
                    "contamination": contamination,
                }
            )

        return {
            "summary":
                "Materials identified using the waste "
                "description.",

            "materials": materials,

            "agent":
                "Agent 1 — Material Classification",
        }

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    prompt = f"""
You are Agent 1 of a Construction and Demolition Waste
Recovery System.

Analyze this construction waste description:

{description}

Identify the major material categories.

Return ONLY valid JSON.

Required format:

{{
    "summary": "short explanation",
    "materials": [
        {{
            "material": "concrete",
            "estimated_quantity_tons": 2.0,
            "contamination": "low"
        }}
    ]
}}

Allowed material names:

- concrete
- rebar
- steel
- asphalt
- wood
- drywall
- plastic
- mixed_c&d

Rules:

1. Estimate quantities conservatively.
2. The sum of material quantities should approximately match
   the total waste quantity when a total is provided.
3. Contamination must be low, medium, or high.
4. Do not use markdown.
5. Return JSON only.
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.1,
        )

        result = extract_json(
            response.choices[0].message.content
        )

        result["agent"] = (
            "Agent 1 — Material Classification"
        )

        return result

    except Exception:

        return classification_agent_fallback(
            description
        )


# ============================================================
# CLASSIFICATION FALLBACK
# ============================================================

def classification_agent_fallback(description):

    text = description.lower()

    materials = []

    quantity_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:tons?|tonnes?)",
        text,
    )

    total_quantity = (
        float(quantity_match.group(1))
        if quantity_match
        else 1.0
    )

    detected = []

    keywords = {
        "concrete": ["concrete"],
        "rebar": ["rebar"],
        "steel": ["steel"],
        "asphalt": ["asphalt"],
        "wood": ["wood", "timber"],
        "drywall": ["drywall", "gypsum"],
        "plastic": ["plastic"],
    }

    for material, words in keywords.items():

        if any(
            word in text
            for word in words
        ):
            detected.append(material)

    if not detected:
        detected.append("mixed_c&d")

    share = total_quantity / len(detected)

    for material in detected:

        contamination = "medium"

        if "low contamination" in text:
            contamination = "low"

        elif "high contamination" in text:
            contamination = "high"

        materials.append(
            {
                "material": material,
                "estimated_quantity_tons": round(
                    share,
                    2,
                ),
                "contamination": contamination,
            }
        )

    return {
        "summary":
            "Fallback classification completed.",

        "materials": materials,

        "agent":
            "Agent 1 — Material Classification",
    }


# ============================================================
# AGENT 2
# RECOVERABILITY
# ============================================================

def recoverability_agent(classification):

    materials = classification.get(
        "materials",
        [],
    )

    recovery_rates = {
        "concrete": 90,
        "rebar": 95,
        "steel": 95,
        "asphalt": 90,
        "wood": 70,
        "drywall": 50,
        "plastic": 45,
        "mixed_c&d": 30,
    }

    assessments = []

    for item in materials:

        material = item.get(
            "material",
            "mixed_c&d",
        ).lower()

        contamination = item.get(
            "contamination",
            "medium",
        ).lower()

        base_rate = recovery_rates.get(
            material,
            40,
        )

        if contamination == "high":

            rate = base_rate - 20

        elif contamination == "medium":

            rate = base_rate - 10

        else:

            rate = base_rate

        rate = max(
            10,
            min(
                rate,
                100,
            ),
        )

        assessments.append(
            {
                "material": item.get(
                    "material",
                    material,
                ),
                "recoverable": rate >= 30,
                "recoverable_percent": rate,
                "reason":
                    get_recovery_reason(
                        material,
                        contamination,
                    ),
            }
        )

    if assessments:

        overall = sum(
            x["recoverable_percent"]
            for x in assessments
        ) / len(assessments)

    else:

        overall = 0

    return {
        "summary":
            "Recoverability was estimated from material "
            "type and contamination level.",

        "overall_recoverability_percent":
            round(
                overall,
                1,
            ),

        "assessments":
            assessments,

        "agent":
            "Agent 2 — Recoverability Assessment",
    }


# ============================================================
# RECOVERY REASON
# ============================================================

def get_recovery_reason(
    material,
    contamination,
):

    reasons = {

        "concrete":
            "Concrete can generally be crushed and "
            "screened into recycled aggregate.",

        "rebar":
            "Rebar can be separated magnetically and "
            "sent to a metal recycling route.",

        "steel":
            "Steel can be separated and recycled through "
            "metal processing facilities.",

        "asphalt":
            "Asphalt millings can potentially be reused "
            "as recycled asphalt material.",

        "wood":
            "Clean wood can potentially be reused, "
            "chipped, or processed into wood products.",

        "drywall":
            "Drywall may be separated for gypsum recovery "
            "when contamination is controlled.",

        "plastic":
            "Separated plastic may be sent to an appropriate "
            "recycling stream.",

        "mixed_c&d":
            "Mixed C&D material requires sorting before "
            "higher-value recovery routes can be used.",
    }

    reason = reasons.get(
        material,
        "Material should be evaluated for appropriate "
        "recovery and recycling options.",
    )

    if contamination == "high":

        reason += (
            " High contamination may reduce practical "
            "recovery efficiency."
        )

    elif contamination == "medium":

        reason += (
            " Moderate contamination means additional "
            "sorting may be required."
        )

    return reason


# ============================================================
# AGENT 3
# DETERMINISTIC VALUE + CO2
# ============================================================

def value_agent(
    classification,
    recoverability,
):

    materials = classification.get(
        "materials",
        [],
    )

    assessments = recoverability.get(
        "assessments",
        [],
    )

    assessment_map = {}

    for assessment in assessments:

        key = assessment.get(
            "material",
            "",
        ).lower()

        assessment_map[key] = assessment

    items = []

    total_net_value = 0.0

    total_co2 = 0.0

    for item in materials:

        material = item.get(
            "material",
            "mixed_c&d",
        )

        key = material.lower()

        quantity = float(
            item.get(
                "estimated_quantity_tons",
                0,
            )
        )

        assessment = assessment_map.get(
            key,
            {},
        )

        recovery_percent = float(
            assessment.get(
                "recoverable_percent",
                0,
            )
        )

        recoverable_quantity = (
            quantity
            * recovery_percent
            / 100
        )

        pricing = PRICING_TABLE.get(
            key,
            PRICING_TABLE["mixed_c&d"],
        )

        price = float(
            pricing["price_per_ton"]
        )

        processing_cost = float(
            pricing[
                "processing_cost_per_ton"
            ]
        )

        co2_factor = float(
            pricing[
                "co2_avoided_kg_per_ton"
            ]
        )

        gross_value = (
            recoverable_quantity
            * price
        )

        processing = (
            recoverable_quantity
            * processing_cost
        )

        net_value = (
            gross_value
            - processing
        )

        co2_avoided = (
            recoverable_quantity
            * co2_factor
        )

        total_net_value += net_value

        total_co2 += co2_avoided

        items.append(
            {
                "material": material,

                "quantity_tons":
                    round(
                        quantity,
                        2,
                    ),

                "recoverable_quantity_tons":
                    round(
                        recoverable_quantity,
                        2,
                    ),

                "recovery_percent":
                    round(
                        recovery_percent,
                        1,
                    ),

                "gross_value":
                    round(
                        gross_value,
                        2,
                    ),

                "processing_cost":
                    round(
                        processing,
                        2,
                    ),

                "net_value":
                    round(
                        net_value,
                        2,
                    ),

                "co2_avoided_kg":
                    round(
                        co2_avoided,
                        2,
                    ),
            }
        )

    return {
        "items": items,

        "total_net_value":
            round(
                total_net_value,
                2,
            ),

        "total_co2_avoided_kg":
            round(
                total_co2,
                2,
            ),

        "calculation_method":
            "Deterministic Python calculation using "
            "the built-in transparent pricing and "
            "environmental lookup table.",

        "agent":
            "Agent 3 — Deterministic Value & CO2",
    }


# ============================================================
# AGENT 4
# RECOVERY PLAN
# ============================================================

def recovery_plan_agent(
    classification,
    recoverability,
    value,
):

    client = get_groq_client()

    # --------------------------------------------------------
    # FALLBACK PLAN
    # --------------------------------------------------------

    if client is None:

        return create_fallback_plan(
            classification,
            recoverability,
            value,
        )

    prompt = f"""
You are Agent 4 of a Construction and Demolition Waste
Recovery System.

Create an actionable recovery plan.

Material Classification:
{json.dumps(classification, indent=2)}

Recoverability Assessment:
{json.dumps(recoverability, indent=2)}

Deterministic Value Calculation:
{json.dumps(value, indent=2)}

Create a professional Markdown recovery plan.

Include:

# Recovery Plan

## 1. Waste Segregation
Explain how the materials should be separated.

## 2. Processing
Explain appropriate processing methods.

## 3. Recovery Routes
Explain reuse, recycling, or resale routes.

## 4. Contamination & Safety
Mention important practical considerations.

## 5. Economic Opportunity
Use ONLY the deterministic financial numbers supplied.

## 6. Environmental Impact
Use ONLY the supplied CO2 calculation.

## 7. Priority Actions
Give 3 to 5 practical next steps.

IMPORTANT:

Do NOT invent financial or CO2 numbers.

Do NOT change the supplied calculations.

Return Markdown only.
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
        )

        markdown = (
            response
            .choices[0]
            .message
            .content
        )

        return {
            "markdown_plan": markdown,

            "summary": {
                "status":
                    "Recovery plan generated by Groq AI."
            },

            "agent":
                "Agent 4 — Recovery Plan",
        }

    except Exception:

        return create_fallback_plan(
            classification,
            recoverability,
            value,
        )


# ============================================================
# FALLBACK RECOVERY PLAN
# ============================================================

def create_fallback_plan(
    classification,
    recoverability,
    value,
):

    lines = []

    lines.append(
        "# 📋 Construction Waste Recovery Plan"
    )

    lines.append(
        "## 1. Waste Segregation"
    )

    lines.append(
        "Separate the waste stream into individual "
        "material categories before processing."
    )

    lines.append(
        "Prioritize clean concrete, metals, asphalt, "
        "wood, drywall, and plastics."
    )

    lines.append(
        "## 2. Processing"
    )

    lines.append(
        "Concrete should be crushed and screened where "
        "appropriate. Metals should be separated for "
        "recycling. Other materials should be sorted "
        "according to their recovery route."
    )

    lines.append(
        "## 3. Recovery Routes"
    )

    for assessment in recoverability.get(
        "assessments",
        [],
    ):

        material = assessment.get(
            "material",
            "Unknown",
        )

        percentage = assessment.get(
            "recoverable_percent",
            0,
        )

        lines.append(
            f"- **{material}**: target approximately "
            f"**{percentage}% recovery**."
        )

    lines.append(
        "## 4. Contamination & Safety"
    )

    lines.append(
        "Inspect incoming material for hazardous "
        "contaminants and separate unsuitable material "
        "before processing. Use appropriate PPE and "
        "site safety procedures."
    )

    lines.append(
        "## 5. Economic Opportunity"
    )

    lines.append(
        f"Estimated net recovery value: "
        f"**${value.get('total_net_value', 0):,.2f}**"
    )

    lines.append(
        "This value is calculated using the deterministic "
        "lookup table rather than generated by the LLM."
    )

    lines.append(
        "## 6. Environmental Impact"
    )

    lines.append(
        f"Estimated CO₂ avoided: "
        f"**{value.get('total_co2_avoided_kg', 0):,.1f} kg**"
    )

    lines.append(
        "## 7. Priority Actions"
    )

    lines.append(
        "1. Characterize and segregate the waste."
    )

    lines.append(
        "2. Remove contamination and unsuitable materials."
    )

    lines.append(
        "3. Process high-value recyclable materials first."
    )

    lines.append(
        "4. Identify local reuse and recycling outlets."
    )

    lines.append(
        "5. Track recovered quantities and disposal reduction."
    )

    return {
        "markdown_plan":
            "\n\n".join(lines),

        "summary": {
            "status":
                "Fallback recovery plan generated."
        },

        "agent":
            "Agent 4 — Recovery Plan",
    }


# ============================================================
# COMPLETE MULTI-AGENT PIPELINE
# ============================================================

def run_pipeline(description):

    # Agent 1
    classification = classification_agent(
        description
    )

    # Agent 2
    recoverability = recoverability_agent(
        classification
    )

    # Agent 3
    value = value_agent(
        classification,
        recoverability,
    )

    # Agent 4
    plan = recovery_plan_agent(
        classification,
        recoverability,
        value,
    )

    return {
        "classification":
            classification,

        "recoverability":
            recoverability,

        "value":
            value,

        "plan":
            plan,
    }


# ============================================================
# HEADER
# ============================================================

st.title(
    "🏗️ Construction Waste Recovery"
)

st.subheader(
    "Multi-Agent AI Recovery System"
)

st.caption(
    "Four specialized AI agents analyze construction "
    "waste, assess recoverability, calculate potential "
    "value and CO₂ savings, and generate an actionable "
    "recovery plan."
)


# ============================================================
# SYSTEM ARCHITECTURE DISPLAY
# ============================================================

with st.expander(
    "🤖 View Multi-Agent Architecture",
    expanded=False,
):

    st.markdown(
        """
        ### Multi-Agent Workflow

        **User Waste Description**
        ↓

        **Agent 1 — Material Classification**
        ↓

        **Agent 2 — Recoverability Assessment**
        ↓

        **Agent 3 — Deterministic Value + CO₂**
        ↓

        **Agent 4 — Recovery Plan**
        ↓

        **Actionable Recovery Recommendation**

        ---

        ### Why this is different from a normal chatbot

        - Specialized agents perform different tasks
        - Financial calculations are deterministic
        - CO₂ calculations are deterministic
        - AI does not invent the final financial numbers
        - Produces an actionable recovery strategy
        """
    )


st.markdown("---")


# ============================================================
# INPUT AREA
# ============================================================

col1, col2 = st.columns(
    [2, 1]
)


with col1:

    choice = st.selectbox(
        "📦 Load a demo example:",
        [
            "— Custom input —"
        ]
        + list(
            DEMO_EXAMPLES.keys()
        ),
    )

    if choice == "— Custom input —":

        default_text = ""

    else:

        default_text = DEMO_EXAMPLES[
            choice
        ]

    description = st.text_area(
        "Waste stream description:",
        value=default_text,
        height=140,
        placeholder=(
            "Example: 10 tons of concrete rubble "
            "with rebar from a demolition site"
        ),
    )


with col2:

    st.markdown(
        "### 🎯 Pitch Highlights"
    )

    st.markdown(
        """
        **🤖 Multi-Agent**

        Specialized AI agents instead of one monolithic prompt.

        **♻️ Recoverability**

        Identifies which materials can potentially be recovered.

        **💰 Deterministic Economics**

        Value is calculated using Python.

        **🌍 Environmental Impact**

        CO₂ impact is calculated using deterministic factors.

        **📋 Actionable**

        Generates a practical recovery plan.
        """
    )


# ============================================================
# ANALYZE BUTTON
# ============================================================

st.markdown("---")


analyze = st.button(
    "🚀 Analyze Waste Stream",
    type="primary",
    use_container_width=True,
)


# ============================================================
# RUN PIPELINE
# ============================================================

if analyze:

    if not description.strip():

        st.error(
            "Please enter a waste description "
            "or select a demo example."
        )

        st.stop()

    with st.spinner(
        "Running 4-agent recovery pipeline..."
    ):

        try:

            result = run_pipeline(
                description
            )

        except Exception as error:

            st.error(
                f"Pipeline error: {error}"
            )

            st.exception(error)

            st.stop()


    classification = result.get(
        "classification",
        {},
    )

    recoverability = result.get(
        "recoverability",
        {},
    )

    value = result.get(
        "value",
        {},
    )

    plan = result.get(
        "plan",
        {},
    )


    # ========================================================
    # SUMMARY METRICS
    # ========================================================

    st.markdown(
        "## 📊 Recovery Summary"
    )

    m1, m2, m3, m4 = st.columns(
        4
    )


    with m1:

        st.metric(
            "💰 Net Recovery Value",
            f"${value.get('total_net_value', 0):,.2f}",
        )


    with m2:

        st.metric(
            "🌍 CO₂ Avoided",
            f"{value.get('total_co2_avoided_kg', 0):,.1f} kg",
        )


    with m3:

        st.metric(
            "📦 Materials Identified",
            len(
                classification.get(
                    "materials",
                    [],
                )
            ),
        )


    with m4:

        st.metric(
            "♻️ Recoverability",
            f"{recoverability.get('overall_recoverability_percent', 0):.0f}%",
        )


    st.markdown("---")


    # ========================================================
    # AGENT 1 OUTPUT
    # ========================================================

    with st.expander(
        "🔍 Agent 1 — Material Classification",
        expanded=True,
    ):

        st.write(
            classification.get(
                "summary",
                "No summary available.",
            )
        )

        materials = classification.get(
            "materials",
            [],
        )

        if materials:

            st.markdown(
                "### Identified Materials"
            )

            for item in materials:

                material = item.get(
                    "material",
                    "Unknown",
                )

                quantity = item.get(
                    "estimated_quantity_tons",
                    0,
                )

                contamination = item.get(
                    "contamination",
                    "Unknown",
                )

                st.markdown(
                    f"""
                    **{material.title()}**

                    - Estimated quantity: **{quantity} tons**
                    - Contamination: **{contamination.title()}**
                    """
                )


    # ========================================================
    # AGENT 2 OUTPUT
    # ========================================================

    with st.expander(
        "♻️ Agent 2 — Recoverability Assessment",
        expanded=True,
    ):

        st.write(
            recoverability.get(
                "summary",
                "No summary available.",
            )
        )

        assessments = recoverability.get(
            "assessments",
            [],
        )

        for item in assessments:

            material = item.get(
                "material",
                "Unknown",
            )

            percentage = item.get(
                "recoverable_percent",
                0,
            )

            recoverable = item.get(
                "recoverable",
                False,
            )

            reason = item.get(
                "reason",
                "",
            )

            if recoverable:

                st.success(
                    f"♻️ {material.title()}: "
                    f"{percentage}% recoverable"
                )

            else:

                st.warning(
                    f"⚠️ {material.title()}: "
                    f"{percentage}% recoverable"
                )

            if reason:

                st.caption(
                    reason
                )


    # ========================================================
    # AGENT 3 OUTPUT
    # ========================================================

    with st.expander(
        "🧮 Agent 3 — Deterministic Value & CO₂",
        expanded=True,
    ):

        st.info(
            "These numbers are calculated by Python "
            "using the deterministic lookup table. "
            "The LLM does not generate these values."
        )

        value_items = value.get(
            "items",
            [],
        )

        if value_items:

            for item in value_items:

                st.markdown(
                    f"""
                    ### {item.get('material', 'Unknown').title()}

                    | Metric | Value |
                    |---|---:|
                    | Original quantity | {item.get('quantity_tons', 0):,.2f} tons |
                    | Recoverable quantity | {item.get('recoverable_quantity_tons', 0):,.2f} tons |
                    | Recovery rate | {item.get('recovery_percent', 0):,.1f}% |
                    | Gross value | ${item.get('gross_value', 0):,.2f} |
                    | Processing cost | ${item.get('processing_cost', 0):,.2f} |
                    | Net value | ${item.get('net_value', 0):,.2f} |
                    | CO₂ avoided | {item.get('co2_avoided_kg', 0):,.1f} kg |
                    """
                )

        st.markdown("### 💰 Total Economic Value")

        st.metric(
            "Total Net Value",
            f"${value.get('total_net_value', 0):,.2f}",
        )

        st.metric(
            "Total CO₂ Avoided",
            f"{value.get('total_co2_avoided_kg', 0):,.1f} kg",
        )


    # ========================================================
    # AGENT 4 OUTPUT
    # ========================================================

    st.markdown(
        "## 📋 Agent 4 — Recovery Plan"
    )

    markdown_plan = plan.get(
        "markdown_plan",
        "",
    )

    if markdown_plan:

        st.markdown(
            markdown_plan
        )

    else:

        st.warning(
            "No recovery plan was generated."
        )


    # ========================================================
    # RAW OUTPUT
    # ========================================================

    with st.expander(
        "🔧 Technical Pipeline Output",
        expanded=False,
    ):

        st.json(
            result
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "🏗️ Construction & Demolition Waste Recovery | "
    "Multi-Agent AI Prototype"
)
