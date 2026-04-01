"""Main tool page — Simplify legal contracts with design tradeoff controls."""

import streamlit as st
from src.clause_extractor import segment_contract
from src.explainer import ClauseExplainer
from src.clause_classifier import ClauseClassifier
from src.data_loader import load_cuad, get_sample_contracts, get_clause_risk, RISK_COLORS
from src.user_model import LITERACY_LABELS, LITERACY_PROMPT_MODIFIERS, UserProfile
from src.glossary import find_terms_in_text, highlight_terms_html
from src.metrics import track_event, generate_participant_id

st.set_page_config(page_title="Simplify Contract", page_icon="📜", layout="wide")

# --- Sample contract ---
SAMPLE_CONTRACT = """TERMS OF SERVICE AGREEMENT

1. GRANT OF LICENSE
The Company hereby grants to the User a non-exclusive, non-transferable, revocable license to access and use the Service strictly in accordance with these Terms. This license does not include any right to resell or commercial use of the Service or its contents; any collection and use of product listings, descriptions, or prices; any derivative use of the Service or its contents; any downloading or copying of account information for the benefit of another merchant; or any use of data mining, robots, or similar data gathering and extraction tools.

2. LIMITATION OF LIABILITY
IN NO EVENT SHALL THE COMPANY, ITS OFFICERS, DIRECTORS, EMPLOYEES, OR AGENTS, BE LIABLE TO YOU FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, PUNITIVE, OR CONSEQUENTIAL DAMAGES WHATSOEVER RESULTING FROM ANY (I) ERRORS, MISTAKES, OR INACCURACIES OF CONTENT, (II) PERSONAL INJURY OR PROPERTY DAMAGE, OF ANY NATURE WHATSOEVER, RESULTING FROM YOUR ACCESS TO AND USE OF OUR SERVICE, (III) ANY UNAUTHORIZED ACCESS TO OR USE OF OUR SECURE SERVERS AND/OR ANY AND ALL PERSONAL INFORMATION STORED THEREIN.

3. INDEMNIFICATION
You agree to defend, indemnify and hold harmless the Company and its subsidiaries, agents, licensors, managers, and other affiliated companies, and their employees, contractors, agents, officers and directors, from and against any and all claims, damages, obligations, losses, liabilities, costs or debt, and expenses (including but not limited to attorney's fees) arising from: (i) your use of and access to the Service; (ii) your violation of any term of these Terms; (iii) your violation of any third party right, including without limitation any copyright, property, or privacy right.

4. ARBITRATION CLAUSE
Any dispute, controversy or claim arising out of or relating to this contract, or the breach, termination or invalidity thereof, shall be settled by binding arbitration in accordance with the rules of the American Arbitration Association. The arbitration shall take place in San Francisco, California. The arbitrator's award shall be final and binding and may be entered as a judgment in any court of competent jurisdiction. YOU UNDERSTAND THAT BY AGREEING TO THIS CLAUSE, YOU ARE WAIVING YOUR RIGHT TO A JURY TRIAL.

5. DATA COLLECTION AND PRIVACY
The Company reserves the right to collect, store, and process personal data including but not limited to browsing history, usage patterns, device information, location data, and any content uploaded to the Service. This data may be shared with third-party partners for purposes including targeted advertising, analytics, and service improvement. By using the Service, you consent to such collection and sharing of your data as described in our Privacy Policy, which may be updated from time to time without prior notice.

6. TERMINATION
The Company may terminate or suspend your account and bar access to the Service immediately, without prior notice or liability, under our sole discretion, for any reason whatsoever and without limitation, including but not limited to a breach of the Terms. If you wish to terminate your account, you may simply discontinue using the Service. All provisions of the Terms which by their nature should survive termination shall survive termination.

7. GOVERNING LAW
These Terms shall be governed and construed in accordance with the laws of the State of California, United States, without regard to its conflict of law provisions. Our failure to enforce any right or provision of these Terms will not be considered a waiver of those rights.

8. INTELLECTUAL PROPERTY
All content included on the Service, such as text, graphics, logos, images, audio clips, digital downloads, data compilations, and software, is the property of the Company or its content suppliers and is protected by international copyright laws. You may not reproduce, distribute, modify, create derivative works of, publicly display, publicly perform, republish, download, store, or transmit any of the material on our Service without the prior written consent of the Company.
"""


# --- Model loading ---
@st.cache_resource(show_spinner="Loading language model...")
def get_explainer(model_name):
    explainer = ClauseExplainer(model_name=model_name)
    explainer.load_model()
    return explainer


# --- Data-driven clause classifier (trained on CUAD) ---
@st.cache_resource(show_spinner="Training clause classifier on CUAD dataset...")
def get_classifier():
    """Load CUAD data and train a TF-IDF clause-type classifier."""
    try:
        dataset = load_cuad()
        contracts = get_sample_contracts(dataset, n=50)
        classifier = ClauseClassifier()
        classifier.fit(contracts)
        return classifier
    except Exception:
        return None


# --- Initialize session state ---
if "participant_id" not in st.session_state:
    st.session_state["participant_id"] = generate_participant_id()
if "explanations" not in st.session_state:
    st.session_state["explanations"] = {}
if "flagged" not in st.session_state:
    st.session_state["flagged"] = set()

pid = st.session_state["participant_id"]

# --- Sidebar: Design Tradeoff Controls ---
with st.sidebar:
    st.header("⚙️ Settings")

    # Model selection
    model_name = st.selectbox(
        "Model",
        ["TinyLlama/TinyLlama-1.1B-Chat-v1.0", "microsoft/phi-2", "mistralai/Mistral-7B-Instruct-v0.2"],
        index=0,
    )

    st.divider()

    # --- Personalization vs. Privacy ---
    st.markdown("### 👤 Personalization")
    literacy_key = st.radio(
        "Your legal literacy level:",
        options=list(LITERACY_LABELS.keys()),
        format_func=lambda k: LITERACY_LABELS[k],
        index=0,
    )
    profile = UserProfile(literacy_level=literacy_key)

    st.caption(
        "🔒 **Privacy**: Your preference is stored only in this browser session "
        "and processed entirely on your local machine. No data is sent to any server."
    )
    if st.button("Reset Profile", key="reset_profile"):
        st.session_state.pop("literacy_key", None)
        st.rerun()

    st.divider()

    # --- Automation vs. Control ---
    st.markdown("### 🎛️ Automation Level")
    default_detail = st.select_slider(
        "Default explanation detail:",
        options=["brief", "standard", "detailed"],
        value="standard",
    )

    highlight_jargon = st.toggle("Highlight legal jargon", value=False)

    st.divider()
    st.markdown("### 📊 Design Tradeoffs")
    st.caption(
        "**Automation vs. Control** — Detail level slider, jargon toggle, per-clause controls\n\n"
        "**Precision vs. Recall** — Confidence badges, feedback buttons, flag incorrect\n\n"
        "**Personalization vs. Privacy** — Literacy adaptation, fully local processing"
    )


# --- Main Content ---
st.title("📜 Simplify Contract")

# --- Input ---
tab_paste, tab_upload, tab_demo = st.tabs(["Paste Text", "Upload File", "Demo Contract"])

contract_text = ""

with tab_paste:
    contract_text_paste = st.text_area(
        "Paste your contract or legal text:",
        height=250,
        placeholder="Paste a Terms of Service, lease, employment contract...",
    )
    if contract_text_paste:
        contract_text = contract_text_paste

with tab_upload:
    uploaded_file = st.file_uploader("Upload a .txt contract file", type=["txt"])
    if uploaded_file is not None:
        contract_text = uploaded_file.read().decode("utf-8")

with tab_demo:
    if st.button("Load Sample Terms of Service", type="primary"):
        st.session_state["demo_loaded"] = True
    if st.session_state.get("demo_loaded"):
        contract_text = SAMPLE_CONTRACT


# --- Process contract ---
if contract_text:
    segments = segment_contract(contract_text)

    if not segments:
        st.warning("Could not identify any sections in the text.")
        st.stop()

    # --- Data-driven clause classification ---
    classifier = get_classifier()
    clause_classifications = {}
    risk_counts = {"high": 0, "medium": 0, "low": 0}

    if classifier:
        for i, seg in enumerate(segments):
            matches = classifier.classify(seg["text"], top_k=2)
            if matches:
                top_type, top_score, top_risk = matches[0]
                clause_classifications[i] = {
                    "type": top_type,
                    "score": top_score,
                    "risk": top_risk,
                    "matches": matches,
                }
                risk_counts[top_risk] += 1
            else:
                risk_counts["low"] += 1

    # --- Contract overview with data-driven risk analysis ---
    st.divider()
    st.subheader("📊 Contract Overview")
    overview_cols = st.columns(4)
    with overview_cols[0]:
        st.metric("Total Sections", len(segments))
    with overview_cols[1]:
        st.metric("High Risk Clauses", risk_counts["high"])
    with overview_cols[2]:
        st.metric("Medium Risk Clauses", risk_counts["medium"])
    with overview_cols[3]:
        st.metric("Low Risk / Unclassified", risk_counts["low"])

    # Risk breakdown bar
    total = max(len(segments), 1)
    if any(risk_counts.values()):
        high_pct = risk_counts["high"] / total * 100
        med_pct = risk_counts["medium"] / total * 100
        low_pct = risk_counts["low"] / total * 100
        st.markdown(
            f'<div style="display:flex; height:16px; border-radius:8px; overflow:hidden; margin:8px 0;">'
            f'<div style="width:{high_pct}%; background:{RISK_COLORS["high"]};"></div>'
            f'<div style="width:{med_pct}%; background:{RISK_COLORS["medium"]};"></div>'
            f'<div style="width:{low_pct}%; background:{RISK_COLORS["low"]};"></div>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; font-size:12px; color:#666;">'
            f'<span>🔴 High Risk</span><span>🟡 Medium</span><span>🟢 Low</span></div>',
            unsafe_allow_html=True,
        )
        st.caption("Clause types classified using TF-IDF similarity against the CUAD legal dataset (510 contracts, 13,000+ annotations).")

    # --- Bulk explain (Automation tradeoff) ---
    st.divider()
    col_bulk, col_warn = st.columns([1, 3])
    with col_bulk:
        bulk_explain = st.button("Explain All Clauses", type="secondary")
    with col_warn:
        if bulk_explain:
            st.info(f"Generating explanations for all {len(segments)} clauses. This may take a while...")

    # --- Clause-by-clause display ---
    st.subheader("📋 Contract Sections")

    for i, seg in enumerate(segments):
        # Build expander label with classification badge
        classification = clause_classifications.get(i)
        if classification:
            risk = classification["risk"]
            badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}[risk]
            label = f"{badge} **{seg['heading'][:80]}** — _{classification['type']}_ ({classification['score']:.0%})"
        else:
            label = f"**{seg['heading'][:100]}**"

        with st.expander(label, expanded=False):

            # Show data-driven classification details
            if classification:
                cls_cols = st.columns([2, 1])
                with cls_cols[0]:
                    st.caption(
                        f"📊 **CUAD Classification**: {classification['type']} "
                        f"(confidence: {classification['score']:.0%}, risk: {classification['risk']})"
                    )
                with cls_cols[1]:
                    if len(classification["matches"]) > 1:
                        alt = classification["matches"][1]
                        st.caption(f"Also similar to: {alt[0]} ({alt[1]:.0%})")

            # --- Left: Original text / Right: Explanation ---
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown("**Original Text**")
                if highlight_jargon:
                    html = highlight_terms_html(seg["text"][:2000])
                    st.markdown(html, unsafe_allow_html=True)

                    terms = find_terms_in_text(seg["text"])
                    if terms:
                        with st.popover("📖 Glossary terms found"):
                            for term, defn in terms:
                                st.markdown(f"**{term}**: {defn}")
                else:
                    st.text(seg["text"][:2000])

            with col_right:
                st.markdown("**AI Explanation**")

                # Per-clause detail override (Automation vs Control)
                clause_detail = st.select_slider(
                    "Detail level for this clause:",
                    options=["brief", "standard", "detailed"],
                    value=default_detail,
                    key=f"detail_{i}",
                )

                should_explain = st.button("Explain", key=f"explain_{i}", type="primary") or bulk_explain

                if should_explain:
                    with st.spinner("Generating..."):
                        explainer = get_explainer(model_name)

                        # Get few-shot examples from CUAD (data-driven)
                        few_shot = None
                        detected_type = None
                        if classification and classifier:
                            detected_type = classification["type"]
                            few_shot = classifier.get_exemplars(detected_type, n=2)

                        result = explainer.explain_clause(
                            seg["text"][:1500],
                            clause_type=detected_type,
                            detail_level=clause_detail,
                            literacy_level=profile.get_prompt_modifier(),
                            few_shot_examples=few_shot,
                        )
                        st.session_state["explanations"][i] = result
                        track_event(pid, "explanation_requested", {
                            "clause_index": i,
                            "detail_level": clause_detail,
                            "literacy_level": literacy_key,
                            "classified_type": detected_type,
                            "classification_score": classification["score"] if classification else None,
                        })

                # Show explanation if available
                if i in st.session_state["explanations"]:
                    result = st.session_state["explanations"][i]

                    # --- Confidence indicator (Precision vs Recall) ---
                    conf = result.get("confidence", {})
                    conf_level = conf.get("level", "unknown")
                    conf_colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}
                    st.caption(f"{conf_colors.get(conf_level, '⚪')} Confidence: **{conf_level.upper()}** — {conf.get('reason', '')}")

                    if result.get("was_truncated"):
                        st.warning("⚠️ This clause was truncated. Explanation may be incomplete.")

                    # Summary
                    if result.get("summary"):
                        st.markdown("**📝 Plain-Language Summary**")
                        st.info(result["summary"])

                    # Rights
                    if result.get("rights"):
                        st.markdown("**⚖️ Rights & Obligations**")
                        st.warning(result["rights"])

                    # Analogy
                    if result.get("analogy"):
                        st.markdown("**💡 Real-World Analogy**")
                        st.success(result["analogy"])

                    # Detailed-only sections
                    if clause_detail == "detailed":
                        if result.get("terms"):
                            st.markdown("**📖 Key Legal Terms**")
                            st.markdown(result["terms"])
                        if result.get("risk"):
                            st.markdown("**⚠️ Risk Assessment**")
                            st.error(result["risk"])

                    # --- Feedback (Precision vs Recall) ---
                    st.markdown("---")
                    feedback_cols = st.columns([1, 1, 2])
                    with feedback_cols[0]:
                        if st.button("👍", key=f"up_{i}"):
                            track_event(pid, "explanation_rated", {"clause_index": i, "rating": "positive"})
                            st.toast("Thanks for the feedback!")
                    with feedback_cols[1]:
                        if st.button("👎", key=f"down_{i}"):
                            track_event(pid, "explanation_rated", {"clause_index": i, "rating": "negative"})
                            st.toast("Thanks — we'll work on improving this.")
                    with feedback_cols[2]:
                        if st.button("🚩 Flag as Incorrect", key=f"flag_{i}"):
                            st.session_state["flagged"].add(i)
                            track_event(pid, "explanation_rated", {"clause_index": i, "rating": "flagged"})

                    if i in st.session_state["flagged"]:
                        st.error("⚠️ This explanation has been flagged as potentially incorrect.")
                        flag_text = st.text_input("What was wrong? (optional)", key=f"flag_text_{i}")
                        if flag_text:
                            track_event(pid, "feedback_submitted", {"clause_index": i, "text": flag_text})

    # --- Free-form query ---
    st.divider()
    st.subheader("❓ Ask About Any Clause")
    user_query = st.text_input("Paste a specific clause or question:")
    if user_query and st.button("Explain", key="explain_query"):
        with st.spinner("Generating..."):
            explainer = get_explainer(model_name)
            result = explainer.explain_clause(
                user_query,
                detail_level=default_detail,
                literacy_level=profile.get_prompt_modifier(),
            )
        if result.get("summary"):
            st.info(result["summary"])
        if result.get("rights"):
            st.warning(result["rights"])
        if result.get("analogy"):
            st.success(result["analogy"])
        if not result.get("summary"):
            st.markdown(result["raw"])
