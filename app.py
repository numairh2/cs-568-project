"""Landing page — Make Jargon and Technical Language Understandable For All."""

import streamlit as st

st.set_page_config(
    page_title="Legal Language Simplifier",
    page_icon="📜",
    layout="wide",
)

st.title("📜 Make Jargon and Technical Language Understandable For All")

st.markdown("""
An **LLM-powered interactive reading tool** that translates complex legal contracts
into accessible, human-understandable language in real-time.

Built for **CS 568: User-Centered Machine Learning** at UIUC.
""")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🔍 How It Works")
    st.markdown("""
    1. **Paste or upload** a legal document
    2. Clauses are **automatically classified** using a TF-IDF model trained on CUAD data
    3. Each clause gets a **risk badge** and **type label**
    4. Choose your **detail level** and get explanations enhanced with **few-shot CUAD examples**
    """)

with col2:
    st.markdown("### 📊 Data-Driven Approach")
    st.markdown("""
    - **CUAD Dataset**: 510 contracts, 13,000+ expert annotations, 41 clause types
    - **Clause Classification**: TF-IDF similarity against CUAD exemplars identifies clause types in new contracts
    - **Few-Shot Learning**: Real CUAD examples injected into LLM prompts for better explanations
    - **Risk Modeling**: Data-derived risk taxonomy from clause-type analysis
    """)

with col3:
    st.markdown("### 🎛️ Design Tradeoffs")
    st.markdown("""
    - **Automation vs. Control** — Choose explanation depth, toggle jargon highlights, per-clause overrides
    - **Precision vs. Recall** — Confidence indicators, user feedback, flag incorrect explanations
    - **Personalization vs. Privacy** — Literacy-level adaptation, fully local processing
    """)

st.divider()

st.markdown("### 📄 Pages")

col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    st.markdown("**Simplify Contract**")
    st.caption("The main tool — paste a contract and get clause-by-clause explanations with user controls.")

with col_b:
    st.markdown("**Browse CUAD**")
    st.caption("Explore real contracts from the CUAD dataset with clause-type annotations and risk badges.")

with col_c:
    st.markdown("**User Study**")
    st.caption("Participate in a between-subjects comparison study evaluating the tool's effectiveness.")

with col_d:
    st.markdown("**Results Dashboard**")
    st.caption("View aggregated study results: comprehension scores, Likert ratings, and feedback.")

st.divider()
st.caption("Ganesh Saranga, Satvik Movva, & Numair Hajyani — CS 568, Spring 2026")
