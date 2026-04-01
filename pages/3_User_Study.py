"""User Study — Between-subjects comparison of legal text comprehension."""

import streamlit as st
from src.study_config import (
    STUDY_CLAUSES, LIKERT_QUESTIONS, CONDITIONS,
    CONDITION_DESCRIPTIONS, CONTROL, TREATMENT_BASIC, TREATMENT_FULL,
    assign_condition,
)
from src.explainer import ClauseExplainer
from src.metrics import track_event, generate_participant_id

st.set_page_config(page_title="User Study", page_icon="🔬", layout="wide")


@st.cache_resource(show_spinner="Loading language model...")
def get_explainer():
    explainer = ClauseExplainer()
    explainer.load_model()
    return explainer


# --- Session state initialization ---
if "study_phase" not in st.session_state:
    st.session_state["study_phase"] = "consent"
if "study_pid" not in st.session_state:
    st.session_state["study_pid"] = generate_participant_id()
if "study_condition" not in st.session_state:
    st.session_state["study_condition"] = None
if "study_answers" not in st.session_state:
    st.session_state["study_answers"] = {}
if "study_likert" not in st.session_state:
    st.session_state["study_likert"] = {}
if "study_explanations" not in st.session_state:
    st.session_state["study_explanations"] = {}

pid = st.session_state["study_pid"]
phase = st.session_state["study_phase"]

st.title("🔬 User Study: Legal Text Comprehension")


# ========== PHASE 1: CONSENT ==========
if phase == "consent":
    st.markdown("""
    ### Study Overview

    Thank you for participating in this study on **legal text comprehension**.

    **What you'll do:**
    - Read 4 clauses from a sample legal contract
    - Answer comprehension questions about each clause
    - Complete a short survey about your experience

    **What we collect:**
    - Your answers to comprehension questions
    - Survey responses
    - No personally identifiable information (name, email, etc.)

    **Time required:** ~10-15 minutes

    All data is stored locally and used only for this CS 568 research project.
    """)

    consent = st.checkbox("I understand and agree to participate in this study.")

    if consent and st.button("Begin Study", type="primary"):
        condition = assign_condition()
        st.session_state["study_condition"] = condition
        st.session_state["study_phase"] = "reading"
        track_event(pid, "condition_assigned", {"condition": condition})
        st.rerun()


# ========== PHASE 2: CLAUSE READING + COMPREHENSION ==========
elif phase == "reading":
    condition = st.session_state["study_condition"]
    clause_idx = st.session_state.get("study_clause_idx", 0)

    # Progress bar
    progress = clause_idx / len(STUDY_CLAUSES)
    st.progress(progress, text=f"Clause {clause_idx + 1} of {len(STUDY_CLAUSES)}")

    if clause_idx >= len(STUDY_CLAUSES):
        st.session_state["study_phase"] = "survey"
        st.rerun()

    clause = STUDY_CLAUSES[clause_idx]

    st.subheader(f"📄 {clause['heading']}")

    # Show clause text (all conditions)
    st.markdown(
        f'<div style="background: #f8f9fa; padding: 16px; border-radius: 8px; '
        f'border-left: 4px solid #1f77b4; margin: 12px 0; font-size: 15px;">'
        f'{clause["text"]}</div>',
        unsafe_allow_html=True,
    )

    # Show explanation based on condition
    if condition == TREATMENT_BASIC:
        # Generate or retrieve brief explanation
        if clause["id"] not in st.session_state["study_explanations"]:
            with st.spinner("Generating explanation..."):
                explainer = get_explainer()
                result = explainer.explain_clause(clause["text"], detail_level="brief")
                st.session_state["study_explanations"][clause["id"]] = result

        result = st.session_state["study_explanations"][clause["id"]]
        st.markdown("**📝 Plain-Language Summary:**")
        st.info(result["summary"] if result["summary"] else result["raw"])

    elif condition == TREATMENT_FULL:
        # Generate or retrieve full explanation
        if clause["id"] not in st.session_state["study_explanations"]:
            with st.spinner("Generating explanation..."):
                explainer = get_explainer()
                result = explainer.explain_clause(clause["text"], detail_level="standard")
                st.session_state["study_explanations"][clause["id"]] = result

        result = st.session_state["study_explanations"][clause["id"]]

        st.markdown("---")
        col_s, col_r, col_a = st.columns(3)
        with col_s:
            st.markdown("**📝 Summary**")
            st.info(result["summary"] if result["summary"] else result["raw"])
        with col_r:
            st.markdown("**⚖️ Rights & Obligations**")
            st.warning(result["rights"] if result["rights"] else "See summary.")
        with col_a:
            st.markdown("**💡 Analogy**")
            st.success(result["analogy"] if result["analogy"] else "See summary.")

    # --- Comprehension questions ---
    st.markdown("---")
    st.markdown("### Comprehension Questions")

    all_answered = True
    for q_idx, q in enumerate(clause["questions"]):
        q_key = f"{clause['id']}_{q_idx}"
        answer = st.radio(
            q["question"],
            options=q["options"],
            index=None,
            key=f"q_{q_key}",
        )
        if answer is not None:
            selected_idx = q["options"].index(answer)
            st.session_state["study_answers"][q_key] = {
                "clause_id": clause["id"],
                "question_idx": q_idx,
                "selected": selected_idx,
                "correct": q["correct"],
                "is_correct": selected_idx == q["correct"],
            }
        else:
            all_answered = False

    # Next button
    if all_answered:
        if st.button("Next Clause →", type="primary"):
            # Log answers
            for q_idx, q in enumerate(clause["questions"]):
                q_key = f"{clause['id']}_{q_idx}"
                if q_key in st.session_state["study_answers"]:
                    track_event(pid, "comprehension_answer", st.session_state["study_answers"][q_key])

            track_event(pid, "clause_viewed", {"clause_id": clause["id"], "condition": condition})
            st.session_state["study_clause_idx"] = clause_idx + 1
            st.rerun()
    else:
        st.caption("Please answer all questions to continue.")


# ========== PHASE 3: POST-TASK SURVEY ==========
elif phase == "survey":
    st.subheader("📊 Post-Task Survey")
    st.markdown("Please rate the following on a scale of 1-5.")

    all_rated = True
    for lq in LIKERT_QUESTIONS:
        # Skip trust question for control group
        if lq["id"] == "trust" and st.session_state["study_condition"] == CONTROL:
            continue

        st.markdown(f"**{lq['question']}**")
        rating = st.slider(
            lq["question"],
            min_value=1,
            max_value=5,
            value=3,
            key=f"likert_{lq['id']}",
            label_visibility="collapsed",
        )
        # Show labels
        label_cols = st.columns(5)
        for li, label in enumerate(lq["labels"]):
            with label_cols[li]:
                st.caption(label)

        st.session_state["study_likert"][lq["id"]] = rating
        st.markdown("")

    # Open-text feedback
    st.markdown("---")
    feedback = st.text_area(
        "Any additional comments? What was most or least helpful?",
        key="study_feedback",
    )

    if st.button("Submit Survey", type="primary"):
        # Log all Likert responses
        for lq_id, rating in st.session_state["study_likert"].items():
            track_event(pid, "likert_response", {"scale": lq_id, "rating": rating})

        if feedback:
            track_event(pid, "feedback_submitted", {"text": feedback})

        track_event(pid, "study_completed", {
            "condition": st.session_state["study_condition"],
            "total_correct": sum(
                1 for a in st.session_state["study_answers"].values() if a.get("is_correct")
            ),
            "total_questions": len(st.session_state["study_answers"]),
        })

        st.session_state["study_phase"] = "debrief"
        st.rerun()


# ========== PHASE 4: DEBRIEF ==========
elif phase == "debrief":
    st.subheader("🎉 Study Complete — Thank You!")

    condition = st.session_state["study_condition"]
    answers = st.session_state["study_answers"]
    total = len(answers)
    correct = sum(1 for a in answers.values() if a.get("is_correct"))

    st.markdown(f"**Your condition:** {CONDITION_DESCRIPTIONS[condition]}")
    st.markdown(f"**Comprehension score:** {correct} / {total} ({correct/max(total,1)*100:.0f}%)")

    if correct == total:
        st.balloons()
        st.success("Perfect score! You understood all the clauses correctly.")
    elif correct >= total * 0.75:
        st.success("Great job! You understood most of the clauses correctly.")
    elif correct >= total * 0.5:
        st.info("You got about half right. Legal text can be tricky!")
    else:
        st.warning("Legal jargon is tough. This is exactly why tools like this exist!")

    # Show correct answers
    st.markdown("---")
    st.subheader("📝 Answer Review")

    for clause in STUDY_CLAUSES:
        st.markdown(f"**{clause['heading']}**")
        for q_idx, q in enumerate(clause["questions"]):
            q_key = f"{clause['id']}_{q_idx}"
            answer = answers.get(q_key, {})
            correct_opt = q["options"][q["correct"]]
            user_selected = answer.get("selected", -1)
            is_correct = answer.get("is_correct", False)

            icon = "✅" if is_correct else "❌"
            st.markdown(f"{icon} {q['question']}")
            if not is_correct and user_selected >= 0:
                st.caption(f"Your answer: {q['options'][user_selected]}")
            st.caption(f"Correct answer: {correct_opt}")
        st.markdown("")

    # Offer to restart
    if st.button("Start Over"):
        for key in ["study_phase", "study_pid", "study_condition", "study_answers",
                     "study_likert", "study_explanations", "study_clause_idx"]:
            st.session_state.pop(key, None)
        st.rerun()
