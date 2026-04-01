"""CUAD Dataset Browser — Explore real contracts with clause-type annotations."""

import streamlit as st
import pandas as pd
from src.data_loader import load_cuad, get_sample_contracts, get_clause_risk, RISK_COLORS
from src.clause_classifier import ClauseClassifier
from src.explainer import ClauseExplainer

st.set_page_config(page_title="Browse CUAD", page_icon="📚", layout="wide")


@st.cache_resource(show_spinner="Loading language model...")
def get_explainer(model_name):
    explainer = ClauseExplainer(model_name=model_name)
    explainer.load_model()
    return explainer


@st.cache_data(show_spinner="Loading CUAD dataset (first time may take a few minutes)...")
def load_contracts(n=15):
    dataset = load_cuad()
    return get_sample_contracts(dataset, n=n)


st.title("📚 Browse CUAD Dataset")
st.markdown(
    "Explore real-world contracts from the **Contract Understanding Atticus Dataset (CUAD)** "
    "with expert-labeled clause-type annotations and risk assessments."
)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    model_name = st.selectbox(
        "Model",
        ["TinyLlama/TinyLlama-1.1B-Chat-v1.0", "microsoft/phi-2", "mistralai/Mistral-7B-Instruct-v0.2"],
        index=0,
        key="cuad_model",
    )
    st.divider()
    st.markdown("### Legend")
    st.markdown(f'<span style="color:{RISK_COLORS["high"]}">● High Risk</span>', unsafe_allow_html=True)
    st.markdown(f'<span style="color:{RISK_COLORS["medium"]}">● Medium Risk</span>', unsafe_allow_html=True)
    st.markdown(f'<span style="color:{RISK_COLORS["low"]}">● Low Risk</span>', unsafe_allow_html=True)

# Load data
try:
    contracts = load_contracts()
except Exception as e:
    st.error(f"Failed to load CUAD dataset: {e}")
    st.info("Make sure you have internet access. The dataset downloads from HuggingFace on first use.")
    st.stop()

if not contracts:
    st.warning("No contracts with clause annotations found in the dataset.")
    st.stop()

# Contract selector
contract_titles = [c["title"] for c in contracts]
selected_title = st.selectbox("Select a contract:", contract_titles)

selected = next(c for c in contracts if c["title"] == selected_title)

# --- Contract overview ---
st.divider()
st.subheader(f"📄 {selected['title']}")

overview_cols = st.columns(4)
with overview_cols[0]:
    st.metric("Annotated Clauses", selected["total_clauses"])
with overview_cols[1]:
    st.metric("Clause Types", len(selected["clause_types"]))
with overview_cols[2]:
    st.metric("High Risk", selected["risk_summary"]["high"])
with overview_cols[3]:
    st.metric("Medium Risk", selected["risk_summary"]["medium"])

# Risk breakdown bar
total = max(selected["total_clauses"], 1)
high_pct = selected["risk_summary"]["high"] / total * 100
med_pct = selected["risk_summary"]["medium"] / total * 100
low_pct = selected["risk_summary"]["low"] / total * 100

st.markdown(
    f'<div style="display:flex; height:20px; border-radius:10px; overflow:hidden; margin:10px 0;">'
    f'<div style="width:{high_pct}%; background:{RISK_COLORS["high"]};"></div>'
    f'<div style="width:{med_pct}%; background:{RISK_COLORS["medium"]};"></div>'
    f'<div style="width:{low_pct}%; background:{RISK_COLORS["low"]};"></div>'
    f'</div>',
    unsafe_allow_html=True,
)

# --- Clause annotations ---
st.divider()
st.subheader("🏷️ Annotated Clauses")

# Group clauses by type
clauses_by_type = {}
for clause in selected["clauses"]:
    ct = clause["clause_type"]
    if ct not in clauses_by_type:
        clauses_by_type[ct] = []
    clauses_by_type[ct].append(clause)

# Initialize explanation storage
if "cuad_explanations" not in st.session_state:
    st.session_state["cuad_explanations"] = {}

for clause_type, clauses in sorted(clauses_by_type.items()):
    risk = get_clause_risk(clause_type)
    color = RISK_COLORS[risk]
    badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}[risk]

    with st.expander(f"{badge} **{clause_type}** ({len(clauses)} instance{'s' if len(clauses) > 1 else ''})"):
        for j, clause in enumerate(clauses):
            st.markdown(
                f'<div style="border-left: 4px solid {color}; padding: 8px 12px; '
                f'margin: 8px 0; background: rgba(0,0,0,0.02); border-radius: 4px;">'
                f'{clause["text"][:500]}</div>',
                unsafe_allow_html=True,
            )

            clause_key = f"{clause_type}_{j}"
            if st.button("Explain", key=f"cuad_explain_{clause_key}"):
                with st.spinner("Generating explanation..."):
                    explainer = get_explainer(model_name)
                    result = explainer.explain_clause(
                        clause["text"][:1500],
                        clause_type=clause_type,
                        detail_level="standard",
                    )
                    st.session_state["cuad_explanations"][clause_key] = result

            if clause_key in st.session_state["cuad_explanations"]:
                result = st.session_state["cuad_explanations"][clause_key]
                col_s, col_r, col_a = st.columns(3)
                with col_s:
                    st.markdown("**📝 Summary**")
                    st.info(result["summary"] if result["summary"] else result["raw"])
                with col_r:
                    st.markdown("**⚖️ Rights/Obligations**")
                    st.warning(result["rights"] if result["rights"] else "See summary.")
                with col_a:
                    st.markdown("**💡 Analogy**")
                    st.success(result["analogy"] if result["analogy"] else "See summary.")

# --- Full contract text ---
st.divider()
with st.expander("📄 Full Contract Text"):
    st.text(selected["context"][:5000])
    if len(selected["context"]) > 5000:
        st.caption(f"Showing first 5000 of {len(selected['context'])} characters.")

# --- Data Analysis: How CUAD models the problem ---
st.divider()
st.subheader("📊 Dataset Analysis: How CUAD Models Legal Clauses")
st.markdown(
    "This section shows how the **CUAD dataset** provides a data-driven foundation "
    "for understanding legal contracts. The dataset's 41 clause-type taxonomy and "
    "13,000+ expert annotations enable structured analysis of contract risk."
)

# Build classifier stats from all loaded contracts
try:
    classifier = ClauseClassifier()
    classifier.fit(contracts)
    stats = classifier.get_statistics()

    analysis_cols = st.columns(3)
    with analysis_cols[0]:
        st.metric("Total Labeled Clauses", stats["total_exemplars"])
    with analysis_cols[1]:
        st.metric("Clause Types Found", stats["clause_types_with_data"])
    with analysis_cols[2]:
        risk_dist = stats["risk_distribution"]
        st.metric("High-Risk Annotations", risk_dist["high"])

    # Clause type frequency chart
    if stats["exemplars_per_type"]:
        st.markdown("**Clause Type Frequency Across Loaded Contracts**")
        freq_df = pd.DataFrame(
            list(stats["exemplars_per_type"].items()),
            columns=["Clause Type", "Count"],
        )
        st.bar_chart(freq_df.set_index("Clause Type")["Count"])

    # Risk distribution
    st.markdown("**Risk Distribution of Annotated Clauses**")
    risk_df = pd.DataFrame(
        [{"Risk Level": k.title(), "Count": v} for k, v in risk_dist.items()]
    )
    st.bar_chart(risk_df.set_index("Risk Level")["Count"])

except Exception as e:
    st.caption(f"Could not generate dataset analysis: {e}")
