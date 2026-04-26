"""Results Dashboard — pilot data with inferential statistics.

Primary analysis follows ``study/preregistration.md``:
  - Primary outcome: comprehension accuracy (% correct on 24 items).
  - Primary test: one-way ANOVA across the 3 conditions + Tukey HSD.
  - Planned contrasts: treatment_full vs control, treatment_basic vs control
    (Welch's t, Cohen's d, bootstrap 95% CI; Holm correction within the pair).
  - Pre-registered exclusions: failed attention check OR manipulation-check
    "Yes" rate < 50%. Both primary and sensitivity (all completed) views are
    surfaced below.
"""

import os

import numpy as np
import pandas as pd
import streamlit as st

from src.metrics import load_events, load_events_by_type
from src.statistics import (
    apply_preregistered_exclusions,
    bootstrap_ci,
    by_literacy_baseline,
    compare_conditions_anova,
    descriptives_by_condition,
    holm_correct,
    pairwise_t,
    participant_frame,
    synth_events,
)
from src.study_config import (
    CONDITION_DESCRIPTIONS,
    CONTROL,
    LIKERT_QUESTIONS,
    STUDY_CLAUSES,
    TREATMENT_BASIC,
    TREATMENT_FULL,
)

st.set_page_config(page_title="Results Dashboard", page_icon="📊", layout="wide")

st.title("📊 Results Dashboard")


# ---------- Auth (env var / st.secrets, not hardcoded) -----------------------

def _expected_password() -> str | None:
    # Prefer st.secrets (deploy), fall back to env var (dev).
    try:
        if "dashboard_password" in st.secrets:
            return str(st.secrets["dashboard_password"])
    except Exception:
        pass
    return os.environ.get("DASHBOARD_PASSWORD")


expected = _expected_password()
password = st.text_input("Dashboard password:", type="password")
if expected is None:
    st.warning(
        "No dashboard password is configured. Set `DASHBOARD_PASSWORD` in the "
        "environment or `dashboard_password` in `.streamlit/secrets.toml` before "
        "sharing this dashboard."
    )
    if not password:
        st.stop()
elif password != expected:
    st.info("Enter the dashboard password to view results.")
    st.stop()


# ---------- Data source toggle ------------------------------------------------

with st.sidebar:
    st.subheader("Data source")
    use_synth = st.toggle("Use synthetic data (demo)", value=False, help=(
        "Generates a planted-effect dataset via src.statistics.synth_events. "
        "Useful to verify the dashboard before pilot data is collected."
    ))
    synth_n = st.slider("Participants per condition (synthetic only)", 5, 50, 15) if use_synth else 15
    synth_effect = st.slider("Planted effect (synthetic only)", 0.0, 0.4, 0.2, 0.05) if use_synth else 0.2

events = synth_events(n_per_condition=synth_n, effect=synth_effect) if use_synth else load_events()

if not events:
    st.warning("No study data collected yet. Run the User Study to generate data, or toggle synthetic data in the sidebar.")
    st.stop()


# ---------- Build frames + apply exclusions -----------------------------------

df_all = participant_frame(events)
if df_all.empty or "condition" not in df_all:
    st.warning("No completed sessions yet.")
    st.stop()

primary_df, excluded_df = apply_preregistered_exclusions(df_all)

with st.sidebar:
    st.subheader("Analysis sample")
    view = st.radio(
        "View",
        options=["Primary (pre-registered exclusions)", "Sensitivity (all completed)"],
        help="Primary applies attention + manipulation check exclusions. Sensitivity includes everyone.",
    )
df = primary_df if view.startswith("Primary") else df_all

st.caption(
    f"Completed sessions: **{len(df_all)}** — "
    f"primary: **{len(primary_df)}**, excluded: **{len(excluded_df)}** "
    f"(view: **{view}**)"
)


# ---------- Overview ----------------------------------------------------------

st.subheader("📋 Overview")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Participants (completed)", len(df_all))
with col2:
    st.metric("Primary analysis n", len(primary_df))
with col3:
    st.metric("Excluded (pre-registered)", len(excluded_df))


# ---------- Helpers -----------------------------------------------------------

def plot_with_ci(desc: pd.DataFrame, outcome_label: str):
    if desc.empty:
        return
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 3.5))
    x = np.arange(len(desc))
    means = desc["mean"].to_numpy()
    yerr_lo = means - desc["ci_lo"].to_numpy()
    yerr_hi = desc["ci_hi"].to_numpy() - means
    ax.bar(x, means, yerr=[yerr_lo, yerr_hi], capsize=6, color="#1f77b4", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(desc["condition"].tolist(), rotation=0)
    ax.set_ylabel(outcome_label)
    ax.set_title(f"{outcome_label} by condition (mean, 95% bootstrap CI)")
    ax.grid(axis="y", alpha=0.3)
    st.pyplot(fig, clear_figure=True)


def render_inferential(df: pd.DataFrame, outcome: str, contrast_pairs: list[tuple[str, str]]):
    anova = compare_conditions_anova(df, outcome)
    if anova is None:
        st.caption("Not enough data for a significance test yet.")
        return
    st.markdown(
        f"**{anova.test.upper()}:** statistic = **{anova.statistic:.3f}**, "
        f"df = ({anova.df_between}, {anova.df_within}), "
        f"p = **{anova.p_value:.4f}**"
        + (f", η² = {anova.eta_sq:.3f}" if anova.eta_sq is not None else "")
        + ("  _(fallback to non-parametric due to assumption violations)_" if anova.fell_back else "")
    )
    if anova.tukey_rows:
        st.markdown("Tukey HSD (α = 0.05):")
        st.dataframe(pd.DataFrame(anova.tukey_rows), use_container_width=True, hide_index=True)

    pw_results = []
    for c1, c2 in contrast_pairs:
        pw = pairwise_t(df, outcome, c1, c2)
        if pw is not None:
            pw_results.append(pw)
    if pw_results:
        raw_p = [pw.p_value for pw in pw_results]
        holm_p = holm_correct(raw_p)
        rows = []
        for pw, adj in zip(pw_results, holm_p):
            rows.append({
                "contrast": f"{pw.c1} vs {pw.c2}",
                "test": pw.test,
                "n1": pw.n1, "n2": pw.n2,
                "mean_diff": round(pw.mean_diff, 3),
                "cohens_d": None if pw.cohens_d is None else round(pw.cohens_d, 3),
                "rank_biserial": None if pw.rank_biserial is None else round(pw.rank_biserial, 3),
                "ci_95": f"[{pw.ci_lo:.2f}, {pw.ci_hi:.2f}]",
                "p": round(pw.p_value, 4),
                "p_holm": round(adj, 4),
            })
        st.markdown("Planned pairwise contrasts (Holm-corrected within pair):")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------- Primary outcome ---------------------------------------------------

st.divider()
st.subheader("🎯 Comprehension accuracy (primary outcome)")

desc = descriptives_by_condition(df, "comprehension_pct")
st.dataframe(desc, use_container_width=True, hide_index=True)
plot_with_ci(desc, "Comprehension (% correct)")
render_inferential(
    df, "comprehension_pct",
    contrast_pairs=[(TREATMENT_FULL, CONTROL), (TREATMENT_BASIC, CONTROL)],
)


# ---------- Literacy-stratified ----------------------------------------------

st.divider()
st.subheader("📚 Stratified by baseline literacy (exploratory, H3)")
strata = by_literacy_baseline(df)
col_lo, col_hi = st.columns(2)
with col_lo:
    st.markdown("**Below-median literacy**")
    d = descriptives_by_condition(strata["low"], "comprehension_pct")
    if not d.empty:
        st.dataframe(d, use_container_width=True, hide_index=True)
        plot_with_ci(d, "Comprehension (low literacy)")
with col_hi:
    st.markdown("**At-or-above-median literacy**")
    d = descriptives_by_condition(strata["high"], "comprehension_pct")
    if not d.empty:
        st.dataframe(d, use_container_width=True, hide_index=True)
        plot_with_ci(d, "Comprehension (high literacy)")


# ---------- Likert scales -----------------------------------------------------

st.divider()
st.subheader("📈 Likert ratings (secondary outcomes)")

for lq in LIKERT_QUESTIONS:
    col = f"likert_{lq['id']}"
    if col not in df:
        continue
    sub = df[df[col].notna()]
    if sub.empty:
        continue
    st.markdown(f"**{lq['question']}**")
    d = descriptives_by_condition(sub, col)
    st.dataframe(d, use_container_width=True, hide_index=True)
    plot_with_ci(d, f"{lq['id']} (1–5)")
    if lq["id"] in {"trust", "helpfulness"}:
        render_inferential(
            sub, col,
            contrast_pairs=[(TREATMENT_FULL, TREATMENT_BASIC)],
        )


# ---------- Per-clause failure cases -----------------------------------------

st.divider()
st.subheader("🔎 Per-clause accuracy (failure-case analysis)")

# Rebuild per-question accuracy from the event log directly.
answer_events = load_events_by_type("comprehension_answer") if not use_synth else []
cond_of: dict[str, str] = {}
for e in load_events_by_type("condition_assigned") if not use_synth else []:
    cond_of[e["participant_id"]] = e["data"].get("condition", "unknown")

if answer_events:
    rows = []
    for e in answer_events:
        pid = e["participant_id"]
        if pid not in df["participant_id"].values:
            continue  # respect the current view's exclusions
        d = e["data"]
        rows.append({
            "participant_id": pid,
            "condition": cond_of.get(pid, "unknown"),
            "clause_id": d.get("clause_id"),
            "is_correct": int(bool(d.get("is_correct"))),
        })
    qa = pd.DataFrame(rows)
    if not qa.empty:
        pivot = qa.groupby(["clause_id", "condition"])["is_correct"].mean().unstack("condition")
        pivot = pivot.reindex(index=[c["id"] for c in STUDY_CLAUSES])
        pivot.index.name = "clause_id"
        st.dataframe((pivot * 100).round(1).astype(str) + "%", use_container_width=True)
        st.caption("% correct per clause × condition. Look for clauses where treatment does NOT help (or hurts).")
else:
    st.caption("No per-question answers in view. (Synthetic data does not include per-question events.)")


# ---------- Attention + manipulation checks -----------------------------------

st.divider()
st.subheader("🧭 Attention & manipulation checks")

if "attention_pass" in df_all:
    ac_total = df_all["attention_pass"].notna().sum()
    ac_pass = int(df_all["attention_pass"].fillna(False).sum())
    st.metric("Attention check pass rate", f"{ac_pass}/{ac_total}" if ac_total else "—")

manip_events = load_events_by_type("manipulation_check") if not use_synth else []
if manip_events:
    mdf = pd.DataFrame([{**e["data"], "participant_id": e["participant_id"]} for e in manip_events])
    mdf["answered_yes"] = mdf["answer"].str.startswith("Yes")
    summary = mdf.groupby("condition")["answered_yes"].agg(["count", "sum", "mean"])
    summary.columns = ["n", "yes", "yes_rate"]
    st.dataframe(summary, use_container_width=True)


# ---------- Free-text feedback + raw -----------------------------------------

st.divider()
st.subheader("💬 Written feedback")

text_feedback = [e for e in events if e["event_type"] == "feedback_submitted"]
if text_feedback:
    for e in text_feedback:
        text = e["data"].get("text", "")
        if text:
            st.markdown(f"- *\"{text}\"* (pid: `{e['participant_id'][:4]}…`)")
else:
    st.caption("No written feedback yet.")

st.divider()
st.subheader("📥 Raw data")
with st.expander("Show raw events"):
    st.json(events[:200])
st.download_button(
    "Download events as JSONL",
    data="\n".join([__import__("json").dumps(e) for e in events]),
    file_name="study_events.jsonl",
)
