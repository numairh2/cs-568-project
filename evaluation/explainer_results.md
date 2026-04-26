# Explainer benchmark results

Per-model averages across the CUAD explainer benchmark (N = 2 clauses).

_Coverage: 2 / 20 benchmark clauses have at least one generation. Run `python -m src.evaluate_explainer run --models ...` to fill in. The frontier-API models (`anthropic`, `openai`) are fast (~seconds/clause) but require an API key; local models are slow on CPU (~7–10 min/clause for TinyLlama)._

| Model | n | ROUGE-L F1 (mean ± SD) | Parse success | Length (chars) | Elapsed (s) |
|---|---|---|---|---|---|
| tinyllama | 2 | 0.206 ± 0.041 | 1.00 | 1160 | 552.58 |

## Notes

- **ROUGE-L F1** is computed against the CUAD answer span (the text a lawyer highlighted).
  This is a *weak* reference because we want explanations, not extractions — treat it as a
  proxy for whether the explanation mentions the right content. Human ratings below are the
  primary quality signal.
- **Parse success** is the fraction of expected structured sections
  (summary / rights / analogy [/ terms / risk]) that the post-processor extracted.
- **Elapsed** is wall-clock seconds per clause (lower is faster, not better).

## Human ratings

The three team members each rate 2 clauses × 1 models on Clarity,
Faithfulness, and Completeness (1–5 Likert). Fill in `evaluation/human_ratings.csv`;
inter-rater agreement (Krippendorff's α) goes into the presentation once collected.
