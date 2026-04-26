"""Explainer benchmark.

Curate a fixed set of CUAD clauses, generate plain-language explanations
with each configured model, compute automatic metrics against the CUAD
answer span (treated as a weak reference), and emit:

- ``evaluation/explainer_benchmark.jsonl``  clauses + references
- ``evaluation/explainer_generations.jsonl``  model outputs
- ``evaluation/explainer_results.md``        per-model summary table
- ``evaluation/human_ratings.csv``           empty template for Likert rating

Usage:
    python -m src.evaluate_explainer curate    # pick 20 clauses
    python -m src.evaluate_explainer run       # run models
    python -m src.evaluate_explainer report    # aggregate to results.md
    python -m src.evaluate_explainer all       # curate + run + report

Models are selected via flags, e.g. ``--models tinyllama,phi2,anthropic``.
The anthropic/openai options read ANTHROPIC_API_KEY / OPENAI_API_KEY from
the environment and are skipped if unset.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

from src.data_loader import CLAUSE_TYPES, extract_clauses_from_cuad, load_cuad
from src.explainer import DETAIL_PROMPTS, ClauseExplainer

EVAL_DIR = Path(__file__).parent.parent / "evaluation"
BENCHMARK_PATH = EVAL_DIR / "explainer_benchmark.jsonl"
GENERATIONS_PATH = EVAL_DIR / "explainer_generations.jsonl"
REPORT_PATH = EVAL_DIR / "explainer_results.md"
HUMAN_RATING_PATH = EVAL_DIR / "human_ratings.csv"

DEFAULT_DETAIL = "standard"
N_BENCHMARK = 20


# ---------- Curation ----------

def curate_benchmark(n: int = N_BENCHMARK, seed: int = 7) -> list[dict]:
    """Pick ``n`` diverse CUAD clauses spanning multiple clause types and lengths."""
    rng = random.Random(seed)
    splits = load_cuad()
    contracts = extract_clauses_from_cuad(splits["test"])

    by_type: dict[str, list[dict]] = {ct: [] for ct in CLAUSE_TYPES}
    for title, data in contracts.items():
        for clause in data.get("clauses", []):
            ct = clause["clause_type"]
            if ct in by_type and 100 <= len(clause["text"]) <= 2000:
                by_type[ct].append({
                    "clause_type": ct,
                    "text": clause["text"],
                    "contract_title": title,
                })

    # Prefer clause types with multiple annotations so we can sample diverse lengths.
    populated = [ct for ct, items in by_type.items() if items]
    rng.shuffle(populated)

    selected: list[dict] = []
    seen_types: set[str] = set()
    # First pass: one short + one long from each of several clause types.
    for ct in populated:
        items = by_type[ct]
        if len(selected) >= n:
            break
        items_sorted = sorted(items, key=lambda c: len(c["text"]))
        pick = items_sorted[0]
        if pick["clause_type"] in seen_types:
            continue
        selected.append(pick)
        seen_types.add(pick["clause_type"])
        if len(items_sorted) > 2 and len(selected) < n:
            long_pick = items_sorted[-1]
            if long_pick["text"] != pick["text"]:
                selected.append(long_pick)

    # Fill remaining slots with random picks from any type.
    if len(selected) < n:
        pool = [c for items in by_type.values() for c in items if c not in selected]
        rng.shuffle(pool)
        selected.extend(pool[: n - len(selected)])

    selected = selected[:n]
    for i, c in enumerate(selected):
        c["id"] = f"bench-{i:02d}"
        # Reference = the CUAD answer span itself (what an expert highlighted).
        # This is a weak reference for explanations, but gives an anchor for ROUGE/BERTScore.
        c["reference"] = c["text"]
    return selected


def write_benchmark(clauses: list[dict]) -> None:
    EVAL_DIR.mkdir(exist_ok=True)
    with open(BENCHMARK_PATH, "w") as f:
        for c in clauses:
            f.write(json.dumps(c) + "\n")


def load_benchmark() -> list[dict]:
    if not BENCHMARK_PATH.exists():
        return []
    with open(BENCHMARK_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------- Model adapters ----------

class LocalHFModel:
    def __init__(self, name: str, hf_id: str):
        self.name = name
        self.hf_id = hf_id
        self._explainer: ClauseExplainer | None = None

    def load(self):
        print(f"  loading {self.hf_id}...", flush=True)
        self._explainer = ClauseExplainer(model_name=self.hf_id)
        self._explainer.load_model()

    def explain(self, clause_text: str, detail_level: str, clause_type: str | None) -> dict:
        assert self._explainer is not None
        return self._explainer.explain_clause(
            clause_text=clause_text,
            clause_type=clause_type,
            detail_level=detail_level,
        )


class AnthropicModel:
    def __init__(self, model_id: str = "claude-haiku-4-5-20251001"):
        self.name = "anthropic"
        self.model_id = model_id
        self._client = None

    def load(self):
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError("pip install anthropic") from e
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    def explain(self, clause_text: str, detail_level: str, clause_type: str | None) -> dict:
        assert self._client is not None
        clause_context = f" (clause type: {clause_type})" if clause_type else ""
        detail_instruction = DETAIL_PROMPTS.get(detail_level, DETAIL_PROMPTS["standard"])
        user_msg = (
            f"A user is reading a contract and needs help understanding the following "
            f"clause{clause_context}:\n\n\"{clause_text}\"\n\n{detail_instruction}"
        )
        resp = self._client.messages.create(
            model=self.model_id,
            max_tokens=1024,
            system="You are a legal-language simplifier that helps ordinary people understand contracts.",
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        # Reuse the parser from ClauseExplainer for consistency.
        dummy = ClauseExplainer.__new__(ClauseExplainer)
        parsed = dummy._parse_response(text, detail_level)  # noqa: SLF001
        parsed["was_truncated"] = False
        parsed["confidence"] = {"level": "high", "reason": "API model"}
        return parsed


class OpenAIModel:
    def __init__(self, model_id: str = "gpt-4o-mini"):
        self.name = "openai"
        self.model_id = model_id
        self._client = None

    def load(self):
        try:
            import openai  # type: ignore
        except ImportError as e:
            raise RuntimeError("pip install openai") from e
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self._client = openai.OpenAI(api_key=api_key)

    def explain(self, clause_text: str, detail_level: str, clause_type: str | None) -> dict:
        assert self._client is not None
        clause_context = f" (clause type: {clause_type})" if clause_type else ""
        detail_instruction = DETAIL_PROMPTS.get(detail_level, DETAIL_PROMPTS["standard"])
        user_msg = (
            f"A user is reading a contract and needs help understanding the following "
            f"clause{clause_context}:\n\n\"{clause_text}\"\n\n{detail_instruction}"
        )
        resp = self._client.chat.completions.create(
            model=self.model_id,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": "You are a legal-language simplifier that helps ordinary people understand contracts."},
                {"role": "user", "content": user_msg},
            ],
        )
        text = resp.choices[0].message.content or ""
        dummy = ClauseExplainer.__new__(ClauseExplainer)
        parsed = dummy._parse_response(text, detail_level)  # noqa: SLF001
        parsed["was_truncated"] = False
        parsed["confidence"] = {"level": "high", "reason": "API model"}
        return parsed


MODEL_FACTORIES: dict[str, Callable[[], object]] = {
    "tinyllama": lambda: LocalHFModel("tinyllama", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
    "phi2": lambda: LocalHFModel("phi2", "microsoft/phi-2"),
    "mistral": lambda: LocalHFModel("mistral", "mistralai/Mistral-7B-Instruct-v0.2"),
    "anthropic": AnthropicModel,
    "openai": OpenAIModel,
}


# ---------- Metrics ----------

def _rouge_l_f1(reference: str, hypothesis: str) -> float:
    """Minimal ROUGE-L F1 (LCS over whitespace tokens). No external dep."""
    ref_tokens = reference.split()
    hyp_tokens = hypothesis.split()
    if not ref_tokens or not hyp_tokens:
        return 0.0
    m, n = len(ref_tokens), len(hyp_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            if ref_tokens[i] == hyp_tokens[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])
    lcs = dp[m][n]
    precision = lcs / n
    recall = lcs / m
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def parse_success(parsed: dict, detail_level: str) -> float:
    """Fraction of expected structured sections that were successfully parsed."""
    if detail_level == "brief":
        return 1.0 if parsed.get("summary") else 0.0
    expected = ["summary", "rights", "analogy"]
    if detail_level == "detailed":
        expected += ["terms", "risk"]
    filled = sum(1 for k in expected if (parsed.get(k) or "").strip())
    return filled / len(expected)


def compute_metrics(reference: str, parsed: dict, detail_level: str) -> dict:
    explanation = (parsed.get("summary") or "") + " " + (parsed.get("rights") or "") + " " + (parsed.get("analogy") or "")
    explanation = explanation.strip() or parsed.get("raw", "")
    return {
        "rouge_l_f1": round(_rouge_l_f1(reference, explanation), 4),
        "parse_success": round(parse_success(parsed, detail_level), 4),
        "length_chars": len(explanation),
        "confidence_level": (parsed.get("confidence") or {}).get("level", "unknown"),
    }


# ---------- Orchestration ----------

def run_models(models: list[str], detail_level: str, limit: int | None) -> list[dict]:
    benchmark = load_benchmark()
    if not benchmark:
        raise RuntimeError("No benchmark found. Run `curate` first.")
    if limit is not None:
        benchmark = benchmark[:limit]

    # Stream results so a crash mid-run does not lose earlier generations.
    EVAL_DIR.mkdir(exist_ok=True)
    existing: list[dict] = []
    if GENERATIONS_PATH.exists():
        with open(GENERATIONS_PATH) as f:
            existing = [json.loads(line) for line in f if line.strip()]
    done = {(r["model"], r["clause_id"], r["detail_level"]) for r in existing}

    with open(GENERATIONS_PATH, "a") as out:
        for model_name in models:
            factory = MODEL_FACTORIES.get(model_name)
            if factory is None:
                print(f"[skip] unknown model '{model_name}'")
                continue
            try:
                m = factory()
                m.load()
            except Exception as e:
                print(f"[skip] could not load {model_name}: {e}")
                continue
            for c in benchmark:
                key = (model_name, c["id"], detail_level)
                if key in done:
                    continue
                print(f"  {model_name} :: {c['id']} ({c['clause_type']})", flush=True)
                t0 = time.time()
                try:
                    parsed = m.explain(c["text"], detail_level=detail_level, clause_type=c.get("clause_type"))
                except Exception as e:
                    print(f"    [error] {e}")
                    continue
                elapsed = time.time() - t0
                metrics = compute_metrics(c["reference"], parsed, detail_level)
                record = {
                    "model": model_name,
                    "clause_id": c["id"],
                    "clause_type": c["clause_type"],
                    "detail_level": detail_level,
                    "elapsed_s": round(elapsed, 2),
                    "parsed": {k: parsed.get(k, "") for k in ("summary", "rights", "analogy", "terms", "risk", "raw")},
                    "metrics": metrics,
                }
                out.write(json.dumps(record) + "\n")
                out.flush()
                existing.append(record)
    return existing


def write_human_rating_template(benchmark: list[dict], models: list[str], detail_level: str) -> None:
    EVAL_DIR.mkdir(exist_ok=True)
    fields = [
        "clause_id", "clause_type", "model", "detail_level", "rater",
        "clarity_1_5", "faithfulness_1_5", "completeness_1_5", "notes",
    ]
    with open(HUMAN_RATING_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for c in benchmark:
            for model in models:
                writer.writerow([c["id"], c["clause_type"], model, detail_level, "", "", "", "", ""])


def write_report(records: list[dict]) -> None:
    if not records:
        REPORT_PATH.write_text("No generations yet. Run `python -m src.evaluate_explainer run`.\n")
        return

    by_model: dict[str, list[dict]] = {}
    for r in records:
        by_model.setdefault(r["model"], []).append(r)

    def agg(values: list[float]) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        return round(statistics.mean(values), 4), round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0

    n_unique = len({r["clause_id"] for r in records})
    total_benchmark = len(load_benchmark()) or N_BENCHMARK
    status_note = (
        f"_Coverage: {n_unique} / {total_benchmark} benchmark clauses have at least one "
        f"generation. Run `python -m src.evaluate_explainer run --models ...` to fill in."
        " The frontier-API models (`anthropic`, `openai`) are fast (~seconds/clause) but require"
        " an API key; local models are slow on CPU (~7–10 min/clause for TinyLlama)._"
    )
    lines = [
        "# Explainer benchmark results",
        "",
        "Per-model averages across the CUAD explainer benchmark "
        f"(N = {n_unique} clauses).",
        "",
        status_note,
        "",
        "| Model | n | ROUGE-L F1 (mean ± SD) | Parse success | Length (chars) | Elapsed (s) |",
        "|---|---|---|---|---|---|",
    ]
    for model, rows in sorted(by_model.items()):
        rouge = [r["metrics"]["rouge_l_f1"] for r in rows]
        parse = [r["metrics"]["parse_success"] for r in rows]
        length = [r["metrics"]["length_chars"] for r in rows]
        elapsed = [r["elapsed_s"] for r in rows]
        r_m, r_s = agg(rouge)
        p_m, _ = agg(parse)
        l_m, _ = agg([float(x) for x in length])
        e_m, _ = agg(elapsed)
        lines.append(
            f"| {model} | {len(rows)} | {r_m:.3f} ± {r_s:.3f} | {p_m:.2f} | {l_m:.0f} | {e_m:.2f} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- **ROUGE-L F1** is computed against the CUAD answer span (the text a lawyer highlighted).",
        "  This is a *weak* reference because we want explanations, not extractions — treat it as a",
        "  proxy for whether the explanation mentions the right content. Human ratings below are the",
        "  primary quality signal.",
        "- **Parse success** is the fraction of expected structured sections",
        "  (summary / rights / analogy [/ terms / risk]) that the post-processor extracted.",
        "- **Elapsed** is wall-clock seconds per clause (lower is faster, not better).",
        "",
        "## Human ratings",
        "",
        f"The three team members each rate {len({r['clause_id'] for r in records})} clauses × {len(by_model)} models on Clarity,",
        "Faithfulness, and Completeness (1–5 Likert). Fill in `evaluation/human_ratings.csv`;",
        "inter-rater agreement (Krippendorff's α) goes into the presentation once collected.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["curate", "run", "report", "all", "template"])
    parser.add_argument("--models", default="tinyllama")
    parser.add_argument("--detail-level", default=DEFAULT_DETAIL, choices=list(DETAIL_PROMPTS.keys()))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n", type=int, default=N_BENCHMARK)
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]

    if args.action in {"curate", "all"}:
        print("Curating benchmark...")
        clauses = curate_benchmark(n=args.n, seed=args.seed)
        write_benchmark(clauses)
        write_human_rating_template(clauses, models, args.detail_level)
        print(f"  wrote {BENCHMARK_PATH} ({len(clauses)} clauses)")

    if args.action in {"run", "all"}:
        print(f"Running models: {models} (detail_level={args.detail_level})")
        run_models(models, args.detail_level, args.limit)

    if args.action in {"report", "all"}:
        records: list[dict] = []
        if GENERATIONS_PATH.exists():
            with open(GENERATIONS_PATH) as f:
                records = [json.loads(line) for line in f if line.strip()]
        write_report(records)
        print(f"  wrote {REPORT_PATH}")

    if args.action == "template":
        benchmark = load_benchmark()
        if not benchmark:
            print("No benchmark yet; run `curate` first.", file=sys.stderr)
            sys.exit(1)
        write_human_rating_template(benchmark, models, args.detail_level)
        print(f"  wrote {HUMAN_RATING_PATH}")


if __name__ == "__main__":
    main()
