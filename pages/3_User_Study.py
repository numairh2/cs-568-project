"""User Study — Between-subjects comparison of legal text comprehension.

Phases:
  1. Consent (W2a)           — plain-language informed consent + 18+ affirmation
  2. Demographics            — 6 demographic items (W2b)
  3. Literacy baseline       — 5 non-study comprehension items (W2b); score
                               logged as ``literacy_baseline_score``
  4. Reading                 — 8 clauses, per-participant randomized order (W2d);
                               treatment conditions get an AI explanation plus a
                               manipulation check after each clause (W2c)
  5. Survey                  — 5 Likert items + attention check (W2c) + feedback
  6. Debrief                 — summary and answer review
"""

import streamlit as st
from src.study_config import (
    ATTENTION_CHECK,
    CONDITION_DESCRIPTIONS,
    CONDITIONS,
    CONTROL,
    DEMOGRAPHICS_QUESTIONS,
    LIKERT_QUESTIONS,
    LITERACY_BASELINE,
    MANIPULATION_CHECK,
    STUDY_CLAUSES,
    TREATMENT_BASIC,
    TREATMENT_FULL,
    assign_condition,
    clause_order_for,
)
from src.explainer import ClauseExplainer
from src.metrics import generate_participant_id, track_event

st.set_page_config(page_title="User Study", page_icon="🔬", layout="wide")


@st.cache_resource(show_spinner="Loading language model...")
def get_explainer():
    explainer = ClauseExplainer()
    explainer.load_model()
    return explainer


# --- Session state ----------------------------------------------------------
_DEFAULTS = {
    "study_phase": "consent",
    "study_pid": None,
    "study_condition": None,
    "study_demographics": {},
    "study_literacy_answers": {},
    "study_clause_idx": 0,
    "study_answers": {},
    "study_explanations": {},
    "study_manipulation": {},
    "study_likert": {},
    "study_attention_pass": None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
if st.session_state["study_pid"] is None:
    st.session_state["study_pid"] = generate_participant_id()

pid = st.session_state["study_pid"]
phase = st.session_state["study_phase"]

st.title("🔬 User Study: Legal Text Comprehension")


# ========== PHASE 1: CONSENT ==========
if phase == "consent":
    st.subheader("Informed Consent")
    st.markdown("""
**Study title:** Does AI-generated, literacy-adapted explanation improve lay
comprehension of legal contract clauses?

**Who is running this study?** CS 568 (User-Centered Machine Learning) course
project, University of Illinois Urbana-Champaign, Spring 2026.

**What you will do.** You will read eight short clauses from legal contracts
(≈1–3 sentences each) and answer short multiple-choice comprehension questions
about each one. Depending on the condition you are randomly assigned to, you
may also see an AI-generated plain-language explanation of the clause. You will
then complete a short survey. Before the main study begins you will answer a
few demographic questions and a short (5-item) general legal-reading quiz.

**Time required.** Approximately 15 minutes.

**What we collect.** Your answers, ratings, and a randomly generated anonymous
participant id. We do **not** collect your name, email, IP address, or any
other directly identifying information. Free-text feedback is stored verbatim —
please do not enter anything that could identify you.

**Risks and benefits.** There are no foreseeable risks beyond those of reading
text on a screen. There is no direct benefit to you. No compensation is
provided.

**Voluntary participation.** Participation is entirely voluntary. You may
withdraw at any time by closing the browser tab; no partial data will be kept.

**Data retention.** Study data is stored locally on the researchers' machine
until the end of the Spring 2026 semester and then deleted, except for
aggregate (non-identifying) statistics used in the course project writeup.

**Questions.** Contact: numair@hajyani.com. Course staff:
see the CS 568 course page.

**IRB determination.** This is a course project collecting anonymous data from
adult volunteers and is treated as IRB-exempt under the standard course-project
carve-out. Your instructor will confirm.
""")

    st.markdown("---")
    agree = st.checkbox("I have read the above and voluntarily agree to participate.")
    adult = st.checkbox("I am 18 years of age or older.")
    if agree and adult:
        if st.button("Begin Study", type="primary"):
            condition = assign_condition()
            st.session_state["study_condition"] = condition
            st.session_state["study_phase"] = "demographics"
            track_event(pid, "consent_given", {"adult": True})
            track_event(pid, "condition_assigned", {"condition": condition})
            st.rerun()
    else:
        st.caption("Please confirm both statements to continue.")


# ========== PHASE 2: DEMOGRAPHICS ==========
elif phase == "demographics":
    st.subheader("A little about you")
    st.caption("Six quick questions. Your answers are stored only with your anonymous participant id.")

    for q in DEMOGRAPHICS_QUESTIONS:
        key = f"demo_{q['id']}"
        if q["type"] == "choice":
            answer = st.radio(q["question"], options=q["options"], index=None, key=key)
            if answer is not None:
                st.session_state["study_demographics"][q["id"]] = answer
        elif q["type"] == "likert":
            rating = st.slider(
                q["question"],
                min_value=1,
                max_value=len(q["labels"]),
                value=3,
                key=key,
            )
            label_cols = st.columns(len(q["labels"]))
            for i, label in enumerate(q["labels"]):
                with label_cols[i]:
                    st.caption(label)
            st.session_state["study_demographics"][q["id"]] = rating

    all_answered = all(
        q["id"] in st.session_state["study_demographics"]
        for q in DEMOGRAPHICS_QUESTIONS
    )
    if st.button("Continue", type="primary", disabled=not all_answered):
        track_event(pid, "demographics_submitted", st.session_state["study_demographics"])
        st.session_state["study_phase"] = "literacy"
        st.rerun()


# ========== PHASE 3: LITERACY BASELINE ==========
elif phase == "literacy":
    st.subheader("Quick legal-reading check")
    st.caption(
        "Five short snippets of legal language — **not** the same types of clauses "
        "you will see in the main study. We use this to understand your baseline "
        "comfort with legal text."
    )

    for item in LITERACY_BASELINE:
        st.markdown(
            f'<div style="background: #f8f9fa; color: #1a1a1a; padding: 12px; border-radius: 8px; '
            f'border-left: 4px solid #999; margin: 12px 0;">'
            f'{item["snippet"]}</div>',
            unsafe_allow_html=True,
        )
        answer = st.radio(
            item["question"],
            options=item["options"],
            index=None,
            key=f"lit_{item['id']}",
        )
        if answer is not None:
            selected = item["options"].index(answer)
            st.session_state["study_literacy_answers"][item["id"]] = {
                "selected": selected,
                "correct": item["correct"],
                "is_correct": selected == item["correct"],
            }

    all_answered = len(st.session_state["study_literacy_answers"]) == len(LITERACY_BASELINE)
    if st.button("Start main study", type="primary", disabled=not all_answered):
        score = sum(1 for a in st.session_state["study_literacy_answers"].values() if a["is_correct"])
        track_event(pid, "literacy_baseline", {
            "score": score,
            "total": len(LITERACY_BASELINE),
            "answers": st.session_state["study_literacy_answers"],
        })
        st.session_state["study_phase"] = "reading"
        st.rerun()


# ========== PHASE 4: CLAUSE READING + COMPREHENSION ==========
elif phase == "reading":
    condition = st.session_state["study_condition"]
    order = clause_order_for(pid)
    clause_idx = st.session_state["study_clause_idx"]

    progress = clause_idx / len(order)
    st.progress(progress, text=f"Clause {clause_idx + 1} of {len(order)}")

    if clause_idx >= len(order):
        st.session_state["study_phase"] = "survey"
        st.rerun()

    clause = STUDY_CLAUSES[order[clause_idx]]
    st.subheader(f"📄 {clause['heading']}")

    st.markdown(
        f'<div style="background: #f8f9fa; color: #1a1a1a; padding: 16px; border-radius: 8px; '
        f'border-left: 4px solid #1f77b4; margin: 12px 0; font-size: 15px;">'
        f'{clause["text"]}</div>',
        unsafe_allow_html=True,
    )

    # --- AI explanation (treatment conditions) ---
    showed_explanation = False
    if condition == TREATMENT_BASIC:
        if clause["id"] not in st.session_state["study_explanations"]:
            with st.spinner("Generating explanation..."):
                explainer = get_explainer()
                result = explainer.explain_clause(clause["text"], detail_level="brief")
                st.session_state["study_explanations"][clause["id"]] = result
        result = st.session_state["study_explanations"][clause["id"]]
        st.markdown("**📝 Plain-Language Summary:**")
        st.info(result["summary"] if result["summary"] else result["raw"])
        showed_explanation = True

    elif condition == TREATMENT_FULL:
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
        showed_explanation = True

    # --- Manipulation check (treatment only) ---
    manip_answer = None
    if showed_explanation:
        manip_answer = st.radio(
            MANIPULATION_CHECK["question"],
            options=MANIPULATION_CHECK["options"],
            index=None,
            key=f"manip_{clause['id']}",
        )

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

    manip_ok = (not showed_explanation) or (manip_answer is not None)

    if all_answered and manip_ok:
        if st.button("Next Clause →", type="primary"):
            for q_idx, _ in enumerate(clause["questions"]):
                q_key = f"{clause['id']}_{q_idx}"
                if q_key in st.session_state["study_answers"]:
                    track_event(pid, "comprehension_answer", st.session_state["study_answers"][q_key])

            if showed_explanation and manip_answer is not None:
                st.session_state["study_manipulation"][clause["id"]] = manip_answer
                track_event(pid, "manipulation_check", {
                    "clause_id": clause["id"],
                    "condition": condition,
                    "answer": manip_answer,
                })

            track_event(pid, "clause_viewed", {"clause_id": clause["id"], "condition": condition})
            st.session_state["study_clause_idx"] = clause_idx + 1
            st.rerun()
    else:
        if not all_answered:
            st.caption("Please answer all comprehension questions to continue.")
        elif not manip_ok:
            st.caption("Please answer the manipulation-check question above.")


# ========== PHASE 5: POST-TASK SURVEY ==========
elif phase == "survey":
    st.subheader("📊 Post-Task Survey")
    st.markdown("Please rate the following on a scale of 1–5.")

    # Decide order of Likert items, interleaving the attention check.
    condition = st.session_state["study_condition"]

    def render_likert(lq: dict, key: str) -> int:
        st.markdown(f"**{lq['question']}**")
        rating = st.slider(
            lq["question"],
            min_value=1,
            max_value=len(lq["labels"]),
            value=3,
            key=key,
            label_visibility="collapsed",
        )
        label_cols = st.columns(len(lq["labels"]))
        for i, label in enumerate(lq["labels"]):
            with label_cols[i]:
                st.caption(label)
        st.markdown("")
        return rating

    ratings: dict[str, int] = {}
    for lq in LIKERT_QUESTIONS:
        if lq["id"] == "trust" and condition == CONTROL:
            continue  # Trust question only for treatment conditions.
        ratings[lq["id"]] = render_likert(lq, f"likert_{lq['id']}")

    # Attention check (between complexity and willingness for visibility).
    ac_rating = render_likert(ATTENTION_CHECK, f"likert_{ATTENTION_CHECK['id']}")
    ac_chosen_label = ATTENTION_CHECK["labels"][ac_rating - 1]
    attention_pass = ac_chosen_label == ATTENTION_CHECK["correct_label"]

    st.markdown("---")
    feedback = st.text_area(
        "Any additional comments? What was most or least helpful?",
        key="study_feedback",
    )

    if st.button("Submit Survey", type="primary"):
        for lq_id, rating in ratings.items():
            track_event(pid, "likert_response", {"scale": lq_id, "rating": rating})

        track_event(pid, "attention_check", {
            "chosen_label": ac_chosen_label,
            "expected_label": ATTENTION_CHECK["correct_label"],
            "passed": attention_pass,
        })
        st.session_state["study_attention_pass"] = attention_pass
        st.session_state["study_likert"] = ratings

        if feedback:
            track_event(pid, "feedback_submitted", {"text": feedback})

        correct = sum(1 for a in st.session_state["study_answers"].values() if a.get("is_correct"))
        total = len(st.session_state["study_answers"])
        literacy_score = sum(
            1 for a in st.session_state["study_literacy_answers"].values() if a.get("is_correct")
        )
        track_event(pid, "study_completed", {
            "condition": condition,
            "total_correct": correct,
            "total_questions": total,
            "literacy_baseline_score": literacy_score,
            "attention_check_passed": attention_pass,
        })

        st.session_state["study_phase"] = "debrief"
        st.rerun()


# ========== PHASE 6: DEBRIEF ==========
elif phase == "debrief":
    st.subheader("🎉 Study Complete — Thank You!")

    condition = st.session_state["study_condition"]
    answers = st.session_state["study_answers"]
    total = len(answers)
    correct = sum(1 for a in answers.values() if a.get("is_correct"))
    order = clause_order_for(pid)

    st.markdown(f"**Your condition:** {CONDITION_DESCRIPTIONS[condition]}")
    st.markdown(f"**Comprehension score:** {correct} / {total} ({correct/max(total,1)*100:.0f}%)")

    if st.session_state.get("study_attention_pass") is False:
        st.caption("Note: attention check did not match the requested response. This does not affect your debrief, but your data may be excluded from the primary analysis per the pre-registered plan.")

    if correct == total:
        st.balloons()
        st.success("Perfect score! You understood all the clauses correctly.")
    elif correct >= total * 0.75:
        st.success("Great job! You understood most of the clauses correctly.")
    elif correct >= total * 0.5:
        st.info("You got about half right. Legal text can be tricky!")
    else:
        st.warning("Legal jargon is tough. This is exactly why tools like this exist!")

    # Answer review in the order the participant actually saw them.
    st.markdown("---")
    st.subheader("📝 Answer Review")
    for i in order:
        clause = STUDY_CLAUSES[i]
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

    if st.button("Start Over"):
        for key in list(_DEFAULTS.keys()):
            st.session_state.pop(key, None)
        st.rerun()
