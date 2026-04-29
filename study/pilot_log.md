# Pilot recruitment log

Fill in one row per participant *as you run them*. Keep personal identifying
info **out** of this file — the table holds only the anonymous participant id
that the app generated, the condition assigned, and pass/fail of the
pre-registered exclusion checks.

The source of truth for quantitative data is `data/study_data.jsonl`. This
file exists so we can reconstruct who was enrolled but did not finish, and
why, which the event log alone cannot tell us.

Target (per `study/preregistration.md`): **n = 9 completed (3 per condition)**
by **2026-05-05**.

| # | date | participant_id | condition | completed? | attention pass? | manip ≥ 50%? | notes |
|---|------|----------------|-----------|------------|-----------------|--------------|-------|
| 1 | 4/29 |    23ae92e8    |treatment_basic| True   |     True         |   True   |    17/24   |
| 2 | 4/29 |   b785f8a2     | treatment_full|     True       |   True              |   True           |  22/24     |
| 3 |  4/29  |    320a37e3    |  control |   True      |   True         |  N/A     |  22/24 |
| 4 |  4/29    |    9ed137e9       |  control  |     False       |       False          |     N/A         |  15/24     |
| 5 |  4/29  | 8624eb10   |   control   |   True         |     False            |     False         |   16/24    |
| 6 |      |                |           |            |                 |              |       |
| 7 |      |                |           |            |                 |              |       |
| 8 |      |                |           |            |                 |              |       |
| 9 |      |                |           |            |                 |              |       |

## Running a session

1. Make sure the app is up: `streamlit run app.py`.
2. Send the participant the URL (or share screen). Ask them to navigate to
   "User Study" from the sidebar.
3. After they hit *Submit Survey*, grab the 8-character participant id
   from the debrief screen (or from the tail of `data/study_data.jsonl`).
4. Record the row. Mark attention and manipulation checks from the dashboard.
5. Spot-check the dashboard after every 3 sessions to catch bugs early.

## Recruitment pitch (feel free to adapt)

> I'm running a ~15-min study for my CS 568 project on whether AI
> explanations help people read legal contracts. You'd read eight short
> clauses, answer a few comprehension questions, and fill out a brief
> survey. No personal info is collected. Can you do it sometime this week?

## Deviations

Record any protocol deviations here (and in
`evaluation/pilot_results.md` when you write up the findings).
