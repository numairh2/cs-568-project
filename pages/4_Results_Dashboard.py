"""Results Dashboard — Visualize user study data."""

import streamlit as st
import pandas as pd
from src.metrics import load_events, load_events_by_type
from src.study_config import CONDITION_DESCRIPTIONS, LIKERT_QUESTIONS

st.set_page_config(page_title="Results Dashboard", page_icon="📊", layout="wide")

st.title("📊 Results Dashboard")

# Simple password protection
password = st.text_input("Enter dashboard password:", type="password")
if password != "cs568":
    st.info("Enter the dashboard password to view results. (Hint: cs568)")
    st.stop()

# Load all events
events = load_events()

if not events:
    st.warning("No study data collected yet. Run the User Study to generate data.")
    st.stop()

df = pd.DataFrame(events)

# --- Overview ---
st.subheader("📋 Overview")
col1, col2, col3 = st.columns(3)

# Participants
completed = load_events_by_type("study_completed")
condition_assignments = load_events_by_type("condition_assigned")

with col1:
    st.metric("Total Participants", len(completed))
with col2:
    st.metric("Total Events Logged", len(events))
with col3:
    st.metric("Condition Assignments", len(condition_assignments))

# --- Participants by Condition ---
st.divider()
st.subheader("👥 Participants by Condition")

if condition_assignments:
    conditions = [e["data"]["condition"] for e in condition_assignments]
    cond_df = pd.DataFrame({"condition": conditions})
    cond_counts = cond_df["condition"].value_counts().reset_index()
    cond_counts.columns = ["Condition", "Count"]
    cond_counts["Description"] = cond_counts["Condition"].map(CONDITION_DESCRIPTIONS)
    st.bar_chart(cond_counts.set_index("Condition")["Count"])
    st.dataframe(cond_counts, use_container_width=True)

# --- Comprehension Scores by Condition ---
st.divider()
st.subheader("🎯 Comprehension Scores by Condition")

if completed:
    comp_data = []
    for e in completed:
        d = e["data"]
        total = d.get("total_questions", 0)
        correct = d.get("total_correct", 0)
        pct = (correct / total * 100) if total > 0 else 0
        comp_data.append({
            "Condition": d.get("condition", "unknown"),
            "Score (%)": pct,
            "Correct": correct,
            "Total": total,
            "Participant": e["participant_id"],
        })

    comp_df = pd.DataFrame(comp_data)

    # Average by condition
    avg_scores = comp_df.groupby("Condition")["Score (%)"].mean().reset_index()
    avg_scores.columns = ["Condition", "Average Score (%)"]
    st.bar_chart(avg_scores.set_index("Condition"))

    st.markdown("**Individual Scores:**")
    st.dataframe(comp_df, use_container_width=True)

# --- Likert Ratings ---
st.divider()
st.subheader("📈 Likert Scale Ratings")

likert_events = load_events_by_type("likert_response")

if likert_events:
    # Get condition for each participant
    pid_condition = {}
    for e in condition_assignments:
        pid_condition[e["participant_id"]] = e["data"]["condition"]

    likert_data = []
    for e in likert_events:
        likert_data.append({
            "Participant": e["participant_id"],
            "Condition": pid_condition.get(e["participant_id"], "unknown"),
            "Scale": e["data"]["scale"],
            "Rating": e["data"]["rating"],
        })

    likert_df = pd.DataFrame(likert_data)

    # Average ratings per scale per condition
    for lq in LIKERT_QUESTIONS:
        scale_data = likert_df[likert_df["Scale"] == lq["id"]]
        if not scale_data.empty:
            st.markdown(f"**{lq['question']}**")
            avg = scale_data.groupby("Condition")["Rating"].mean().reset_index()
            avg.columns = ["Condition", "Average Rating"]
            st.bar_chart(avg.set_index("Condition"))

# --- Explanation Feedback ---
st.divider()
st.subheader("💬 Explanation Feedback")

feedback_events = load_events_by_type("explanation_rated")
if feedback_events:
    ratings = [e["data"].get("rating", "unknown") for e in feedback_events]
    rating_df = pd.DataFrame({"Rating": ratings})
    rating_counts = rating_df["Rating"].value_counts().reset_index()
    rating_counts.columns = ["Rating", "Count"]
    st.bar_chart(rating_counts.set_index("Rating"))

# Text feedback
text_feedback = load_events_by_type("feedback_submitted")
if text_feedback:
    st.markdown("**Written Feedback:**")
    for e in text_feedback:
        text = e["data"].get("text", "")
        if text:
            st.markdown(f"- *\"{text}\"* (Participant: {e['participant_id'][:4]}...)")

# --- Raw Data Export ---
st.divider()
st.subheader("📥 Raw Data")
if st.button("Show Raw Events"):
    st.json(events)
