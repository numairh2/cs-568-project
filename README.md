# Legal Language Simplifier

An LLM-powered interactive reading tool that translates complex legal contracts into accessible, plain-language explanations. Built for **CS 568: User-Centered Machine Learning** at UIUC, Spring 2026.

## What it does

1. **Paste or upload** a legal document.
2. Clauses are **automatically classified** into one of 41 CUAD clause types using a TF-IDF similarity model trained on CUAD exemplars.
3. Each clause gets a **risk badge** and **type label**.
4. Choose a **detail level** (brief / standard / detailed) and get explanations enhanced with **few-shot CUAD examples** injected into the LLM prompt.

## Data-driven approach

- **Dataset:** [CUAD](https://www.atticusprojectai.org/cuad) — 510 contracts, 13,000+ expert annotations, 41 clause types.
- **Clause classification:** TF-IDF similarity against CUAD exemplars identifies clause types in new contracts.
- **Few-shot learning:** Real CUAD examples are injected into LLM prompts for better explanations.
- **Risk modeling:** Risk taxonomy derived from clause-type analysis.

## Design tradeoffs

- **Automation vs. control** — adjustable explanation depth, jargon highlight toggle, per-clause overrides.
- **Precision vs. recall** — confidence indicators, user feedback, flagging for incorrect explanations.
- **Personalization vs. privacy** — literacy-level adaptation; fully local processing (no contract text leaves the machine).

## Project layout

```
app.py                          # Streamlit landing page
pages/
  1_Simplify_Contract.py        # Main tool: paste a contract, get clause-by-clause explanations
  2_Browse_CUAD.py              # Explore CUAD contracts with annotations and risk badges
  3_User_Study.py               # Between-subjects comparison study UI
  4_Results_Dashboard.py        # Aggregated study results: comprehension, Likert, feedback
src/
  clause_classifier.py          # TF-IDF clause-type classifier
  clause_extractor.py           # Splits raw contract text into clauses
  data_loader.py                # CUAD loading + clause-type metadata
  explainer.py                  # LLM-powered explanation generator (HuggingFace pipeline)
  glossary.py                   # Legal-term glossary
  metrics.py                    # Study metrics
  study_config.py               # Study configuration
  user_model.py                 # User literacy model
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app opens in your browser. Use the sidebar to navigate between the four pages.

The default LLM is `TinyLlama/TinyLlama-1.1B-Chat-v1.0`, which downloads from HuggingFace on first run and runs locally.

## Research

This is a CS 568 research project with a concrete research question, a
pre-registered pilot study, and component-level evaluation of the
classifier and the explainer.

- [`RESEARCH.md`](RESEARCH.md) — research question, hypotheses, contribution.
- [`RELATED_WORK.md`](RELATED_WORK.md) — positioning against legal NLP, readability, XAI, and LLM-evaluation literature.
- [`study/preregistration.md`](study/preregistration.md) — conditions, sample size, exclusion rules, analysis plan.
- [`study/pilot_log.md`](study/pilot_log.md) — participant tracker.

### Evaluation outputs

- **Classifier** — [`evaluation/classifier_results.json`](evaluation/classifier_results.json), [`evaluation/confusion_matrix.png`](evaluation/confusion_matrix.png).
  Generate: `python -m src.evaluate_classifier`.
  TF-IDF classifier: **60.3% top-1**, **81.7% top-3**, **macro-F1 0.528** on held-out CUAD, vs. 23.8% / 0.012 (most-frequent) and 28.2% / 0.177 (keyword) baselines.
- **Explainer** — [`evaluation/explainer_benchmark.jsonl`](evaluation/explainer_benchmark.jsonl), [`evaluation/explainer_results.md`](evaluation/explainer_results.md), [`evaluation/human_ratings.csv`](evaluation/human_ratings.csv).
  Generate: `python -m src.evaluate_explainer all --models tinyllama,anthropic`.
  Frontier-API adapters (`anthropic`, `openai`) read `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` and are skipped if unset.
- **Pilot results** (after collection) — `evaluation/pilot_results.md`.
  Dashboard: `streamlit run app.py` → Results Dashboard (set `DASHBOARD_PASSWORD` in env or `.streamlit/secrets.toml`).

## Authors

Ganesh Saranga, Satvik Movva, and Numair Hajyani — CS 568, Spring 2026.
