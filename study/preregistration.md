# Pre-registration — Legal Language Simplifier pilot study

**Authors:** Ganesh Saranga, Satvik Movva, Numair Hajyani
**Course:** CS 568 — User-Centered Machine Learning, University of Illinois
Urbana-Champaign, Spring 2026
**Version:** v1.0 — 2026-04-23
**Status:** Pre-pilot. No data has been collected at time of registration.

This document is the pre-registered analysis plan for a small pilot study.
It is intentionally modest (n ≈ 6–9) and is not powered to detect small
effects; it is registered to make the predictions, conditions, and analysis
choices explicit **before** looking at results.

---

## 1. Research question

> **RQ:** Does a data-grounded, literacy-adapted LLM explanation of legal
> contract clauses improve lay readers' *comprehension* and *calibrated
> trust* compared to (a) raw clause text only and (b) a minimal
> one-sentence LLM summary?

---

## 2. Hypotheses

- **H1 (comprehension).** Participants in the `treatment_full` condition will
  score higher on the 24-item comprehension test than participants in the
  `control` condition. *(Primary hypothesis.)*
- **H2 (perceived helpfulness and trust).** Participants in `treatment_full`
  will rate the interface higher on the Likert "helpfulness" and "trust"
  scales than participants in `treatment_basic`.
- **H3 (interaction with baseline literacy, exploratory).** The
  comprehension gain of `treatment_full` over `control` is larger for
  participants with below-median scores on the 5-item literacy baseline
  than for above-median participants.

H3 is exploratory: the pilot is not powered for an interaction test; we
pre-register it to signal that we will *look* at this split and not report
only if it is favorable.

---

## 3. Design

Between-subjects with three conditions, randomly assigned (uniform, no
stratification at this sample size):

| Condition         | Stimuli shown to participant                                   |
|-------------------|----------------------------------------------------------------|
| `control`         | Raw clause text only                                           |
| `treatment_basic` | Raw clause text + one-sentence LLM plain-language summary      |
| `treatment_full`  | Raw clause text + 3-part LLM explanation (summary / rights / analogy) |

Clauses are drawn from `src/study_config.py::STUDY_CLAUSES` (eight clauses
covering arbitration, limitation of liability, data collection,
indemnification, termination for convenience, confidentiality, IP
assignment, and automatic renewal). Each clause has 3 MCQ comprehension
items — 24 items total, counterbalanced across the four option positions.
Clause order is per-participant randomized, seeded by the anonymous
participant id, so the same participant always sees the same order on
re-open.

---

## 4. Procedure (per participant)

1. **Informed consent** with an 18+ affirmation.
2. **Demographics** (6 items): age band, education, native-English,
   formal legal training, contract-reading frequency, self-rated
   legal-text comfort.
3. **Literacy baseline** (5 MCQ items on *non-study* legal snippets:
   force majeure, severability, assignment, time-is-of-the-essence,
   entire-agreement). Score (0–5) is logged as `literacy_baseline_score`.
4. **Reading phase** — 8 clauses, randomized order. Treatment conditions
   see an AI explanation plus a per-clause **manipulation check**
   ("Did you read the AI explanation above?" Yes / Skimmed / No).
5. **Post-task survey** — 5 Likert items (confidence, complexity,
   trust [treatment only], willingness-to-sign, helpfulness) with one
   **attention check** ("Please select 'Slightly confident' for this
   item"). Open-text feedback.
6. **Debrief** — comprehension score + answer review.

---

## 5. Sample size and stopping rule

Target: **n = 9 completed sessions (3 per condition)** for the pilot.
Stopping rule: stop recruiting once 9 completed sessions that pass the
pre-registered inclusion criteria (§7) have been collected, or 2026-05-05,
whichever is first. The pilot is not powered for a confirmatory test;
its purpose is to (a) stress-test the study flow end-to-end, (b) produce
descriptive statistics and a directional effect size for the course-project
writeup, and (c) produce qualitative feedback to guide follow-up work.

---

## 6. Primary outcome

**Primary outcome:** mean comprehension accuracy per condition, defined as
the proportion of the 24 comprehension items answered correctly
(`total_correct / total_questions`).

**Secondary outcomes:**
- Mean Likert rating per condition per scale (5 scales).
- Mean literacy-baseline score per condition (sanity check — conditions
  should be balanced on baseline literacy under random assignment).
- Manipulation-check rate per treatment condition (`% "Yes, read carefully"`).

---

## 7. Inclusion / exclusion criteria

A participant's data is included in the **primary** analysis iff:

1. They completed all phases through `study_completed`.
2. They passed the attention check (chose `"Slightly confident"`).
3. They answered `"Yes, read carefully"` or `"Skimmed it"` to at least
   half of the manipulation checks (treatment conditions only).

Participants who fail criterion 2 or 3 are reported in a **sensitivity
analysis** that re-runs the primary analysis including all completed
sessions. Any discrepancy between primary and sensitivity analyses is
flagged in the writeup.

---

## 8. Analysis plan

1. **Descriptives.** Report n, mean, SD, 95 % CI (percentile bootstrap,
   10 000 iterations) for each outcome × condition.
2. **Primary test (H1).** One-way ANOVA across three conditions on
   comprehension accuracy, α = 0.05. Report F, df, p, η². Follow with
   planned pairwise contrasts `treatment_full` vs `control` and
   `treatment_basic` vs `control` via Welch's t-test; report Cohen's d
   and 95 % CI of the mean difference. Because two planned contrasts
   per outcome are pre-specified, Holm correction is applied within the
   family of two.
3. **Assumption checks.** Shapiro–Wilk per condition and Levene's for
   homogeneity of variance. If either is violated (p < 0.05), fall back
   to Kruskal–Wallis + Mann–Whitney U with rank-biserial correlation as
   effect size.
4. **Secondary tests (H2).** Same pipeline on Likert "helpfulness" and
   "trust" scales, restricted to the two treatment conditions.
5. **Exploratory (H3).** Median-split on `literacy_baseline_score`,
   compute Cohen's d for `treatment_full` vs `control` within each
   subgroup, and note the direction of the difference between subgroups.
   No confirmatory claim is made.
6. **Qualitative.** Two team members independently code each free-text
   comment against the codebook in `src/qualitative_analysis.py`
   (clarity / trust / length / accuracy / usability / other) and compute
   Cohen's κ.

All analyses are implemented in `src/statistics.py` and surfaced in
`pages/4_Results_Dashboard.py`. Raw event log is
`data/study_data.jsonl`.

---

## 9. Deviations from this plan

Any deviation discovered during or after data collection will be listed
in a **Deviations** section appended to `evaluation/pilot_results.md`
with a one-sentence justification.

---

## 10. Timestamping

This file is versioned in git. The pre-registration is considered
"locked" at the commit that introduces it to `main`. No further edits
to this file are permitted after recruitment begins except as noted in
§9.

*(OSF.io upload is optional for a course project; the git commit hash
provides equivalent timestamp integrity for our purposes. The instructor
will advise whether formal OSF pre-registration is required.)*
