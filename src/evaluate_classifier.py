"""Classifier evaluation harness.

Splits CUAD contracts 80/20 by contract id (no clause leakage), fits each
predictor on the train split, evaluates top-1 and top-3 accuracy per clause
on the held-out test split, and writes per-class P/R/F1 + a confusion matrix
to ``evaluation/``.

Compares the TF-IDF classifier against three baselines:
  1. Most-frequent class
  2. Keyword match (clause-type name appears in the clause text)
  3. SBERT cosine similarity (optional, needs sentence-transformers)

Also tunes the TF-IDF similarity threshold via 5-fold CV on the train split.

Usage:
    python -m src.evaluate_classifier [--max-contracts N] [--seed S] [--sbert]
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable

from src.clause_classifier import ClauseClassifier
from src.data_loader import CLAUSE_TYPES, extract_clauses_from_cuad, load_cuad

EVAL_DIR = Path(__file__).parent.parent / "evaluation"


# ---------- Data splitting ----------

def load_contracts(max_contracts: int | None = None) -> list[dict]:
    """Load CUAD test split, flatten to [{title, clauses:[...]}, ...]."""
    dataset = load_cuad()
    contracts = extract_clauses_from_cuad(dataset["test"])
    items = [
        {"title": title, **data}
        for title, data in contracts.items()
        if data["clauses"]
    ]
    if max_contracts is not None:
        items = items[:max_contracts]
    return items


def split_by_contract(contracts: list[dict], test_frac: float, seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    shuffled = contracts[:]
    rng.shuffle(shuffled)
    n_test = max(1, int(len(shuffled) * test_frac))
    return shuffled[n_test:], shuffled[:n_test]


def flatten_clauses(contracts: list[dict]) -> list[tuple[str, str]]:
    """Return [(clause_type, text), ...] across all contracts."""
    out = []
    for c in contracts:
        for clause in c.get("clauses", []):
            ctype = clause.get("clause_type")
            text = clause.get("text", "")
            if ctype and text and ctype in CLAUSE_TYPES:
                out.append((ctype, text))
    return out


# ---------- Predictors ----------

class TFIDFPredictor:
    name = "tfidf"

    def __init__(self, threshold: float = 0.0):
        self.clf = ClauseClassifier()
        self.threshold = threshold

    def fit(self, train_contracts):
        self.clf.fit(train_contracts)

    def predict_topk(self, text: str, k: int = 3) -> list[str]:
        results = self.clf.classify(text, top_k=k, threshold=self.threshold)
        return [r[0] for r in results]


class MostFrequentPredictor:
    name = "most_frequent"

    def __init__(self):
        self.order: list[str] = []

    def fit(self, train_contracts):
        counter = Counter()
        for ctype, _ in flatten_clauses(train_contracts):
            counter[ctype] += 1
        self.order = [t for t, _ in counter.most_common()]

    def predict_topk(self, text: str, k: int = 3) -> list[str]:
        return self.order[:k]


class KeywordPredictor:
    """Rank clause types by whether their (tokenized) name appears in the clause text."""

    name = "keyword"

    def __init__(self):
        self.types: list[str] = []
        self.prior_order: list[str] = []

    def fit(self, train_contracts):
        counter = Counter()
        for ctype, _ in flatten_clauses(train_contracts):
            counter[ctype] += 1
        self.types = list(CLAUSE_TYPES)
        self.prior_order = [t for t, _ in counter.most_common()]

    @staticmethod
    def _match_score(text_lower: str, clause_type: str) -> float:
        name = clause_type.lower().replace("/", " ").replace("-", " ")
        tokens = [t for t in name.split() if len(t) > 2]
        if not tokens:
            return 0.0
        hits = sum(1 for t in tokens if t in text_lower)
        return hits / len(tokens)

    def predict_topk(self, text: str, k: int = 3) -> list[str]:
        text_lower = text.lower()
        scored = [
            (ct, self._match_score(text_lower, ct))
            for ct in self.types
        ]
        scored = [(ct, s) for ct, s in scored if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        picks = [ct for ct, _ in scored[:k]]
        # Pad with priors if keyword match produced fewer than k.
        for ct in self.prior_order:
            if len(picks) >= k:
                break
            if ct not in picks:
                picks.append(ct)
        return picks


class SBERTPredictor:
    """Cosine similarity over SBERT embeddings of clause-type centroids."""

    name = "sbert"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # type: ignore
        import numpy as np  # noqa: F401  (used implicitly)

        self._model = SentenceTransformer(model_name)
        self.centroids: dict[str, "np.ndarray"] = {}
        self.types: list[str] = []

    def fit(self, train_contracts):
        import numpy as np

        grouped: dict[str, list[str]] = defaultdict(list)
        for ctype, text in flatten_clauses(train_contracts):
            grouped[ctype].append(text)

        self.types = list(grouped.keys())
        all_texts: list[str] = []
        spans: list[tuple[int, int]] = []
        for ctype in self.types:
            start = len(all_texts)
            all_texts.extend(grouped[ctype])
            spans.append((start, len(all_texts)))

        embeddings = self._model.encode(all_texts, show_progress_bar=False, normalize_embeddings=True)
        for ctype, (a, b) in zip(self.types, spans):
            centroid = embeddings[a:b].mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            self.centroids[ctype] = centroid

    def predict_topk(self, text: str, k: int = 3) -> list[str]:
        import numpy as np

        q = self._model.encode([text], normalize_embeddings=True)[0]
        sims = [(ct, float(np.dot(q, self.centroids[ct]))) for ct in self.types]
        sims.sort(key=lambda x: x[1], reverse=True)
        return [ct for ct, _ in sims[:k]]


# ---------- Metrics ----------

def per_class_prf(y_true: list[str], y_pred: list[str], classes: list[str]) -> dict[str, dict[str, float]]:
    out = {}
    for ct in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == ct and p == ct)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != ct and p == ct)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == ct and p != ct)
        support = tp + fn
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        out[ct] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
    return out


def summary_metrics(y_true: list[str], topk: list[list[str]], classes: list[str]) -> dict:
    y_pred = [pk[0] if pk else "" for pk in topk]
    top1_correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    top3_correct = sum(1 for t, preds in zip(y_true, topk) if t in preds[:3])
    per = per_class_prf(y_true, y_pred, classes)
    present = [ct for ct in classes if per[ct]["support"] > 0]
    macro_f1 = sum(per[ct]["f1"] for ct in present) / max(len(present), 1)
    return {
        "n": len(y_true),
        "top1_accuracy": round(top1_correct / max(len(y_true), 1), 4),
        "top3_accuracy": round(top3_correct / max(len(y_true), 1), 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per,
    }


def confusion_counts(y_true: list[str], y_pred: list[str], classes: list[str]) -> list[list[int]]:
    idx = {c: i for i, c in enumerate(classes)}
    m = [[0] * len(classes) for _ in classes]
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            m[idx[t]][idx[p]] += 1
    return m


def plot_confusion(y_true: list[str], y_pred: list[str], classes: list[str], path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[skip] matplotlib not installed; confusion matrix PNG not generated.")
        return

    matrix = confusion_counts(y_true, y_pred, classes)
    # Normalize by row (recall per true class) for readable colors.
    normed = []
    for row in matrix:
        s = sum(row)
        normed.append([(v / s) if s else 0.0 for v in row])

    fig, ax = plt.subplots(figsize=(14, 14))
    im = ax.imshow(normed, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(classes)))
    ax.set_yticks(range(len(classes)))
    ax.set_xticklabels(classes, rotation=90, fontsize=6)
    ax.set_yticklabels(classes, fontsize=6)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("TF-IDF classifier: row-normalized confusion matrix")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


# ---------- Threshold tuning ----------

def tune_threshold(
    train_contracts: list[dict],
    thresholds: Iterable[float] = (0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20),
    k_fold: int = 5,
    seed: int = 42,
) -> dict:
    rng = random.Random(seed)
    shuffled = train_contracts[:]
    rng.shuffle(shuffled)
    folds: list[list[dict]] = [shuffled[i::k_fold] for i in range(k_fold)]

    by_threshold: dict[float, list[float]] = defaultdict(list)
    for i in range(k_fold):
        val = folds[i]
        train = [c for j, f in enumerate(folds) if j != i for c in f]
        predictor = TFIDFPredictor(threshold=0.0)
        predictor.fit(train)
        val_clauses = flatten_clauses(val)
        if not val_clauses:
            continue
        y_true = [t for t, _ in val_clauses]
        texts = [x for _, x in val_clauses]
        for th in thresholds:
            predictor.threshold = th
            topk = [predictor.predict_topk(t, k=3) for t in texts]
            metrics = summary_metrics(y_true, topk, CLAUSE_TYPES)
            by_threshold[th].append(metrics["macro_f1"])

    summary = {
        str(th): {
            "mean_macro_f1": round(sum(vs) / max(len(vs), 1), 4),
            "folds": [round(v, 4) for v in vs],
        }
        for th, vs in by_threshold.items()
    }
    best = max(by_threshold.items(), key=lambda kv: sum(kv[1]) / max(len(kv[1]), 1))
    return {"chosen": best[0], "per_threshold": summary}


# ---------- Orchestration ----------

def evaluate_predictor(predictor, test_clauses: list[tuple[str, str]]) -> dict:
    y_true = [t for t, _ in test_clauses]
    topk = [predictor.predict_topk(text, k=3) for _, text in test_clauses]
    metrics = summary_metrics(y_true, topk, CLAUSE_TYPES)
    metrics["predictions_top1"] = [pk[0] if pk else "" for pk in topk]
    metrics["y_true"] = y_true
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-contracts", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-frac", type=float, default=0.2)
    parser.add_argument("--sbert", action="store_true", help="Include SBERT baseline")
    parser.add_argument("--skip-threshold-tuning", action="store_true")
    args = parser.parse_args()

    EVAL_DIR.mkdir(exist_ok=True)

    print("Loading CUAD...")
    contracts = load_contracts(max_contracts=args.max_contracts)
    print(f"  {len(contracts)} contracts with clauses")

    train, test = split_by_contract(contracts, test_frac=args.test_frac, seed=args.seed)
    print(f"  split: {len(train)} train / {len(test)} test")

    test_clauses = flatten_clauses(test)
    print(f"  test clauses: {len(test_clauses)}")

    predictors: list = [
        MostFrequentPredictor(),
        KeywordPredictor(),
        TFIDFPredictor(threshold=0.0),
    ]
    if args.sbert:
        try:
            predictors.append(SBERTPredictor())
        except Exception as e:  # pragma: no cover
            print(f"[skip] SBERT baseline unavailable: {e}")

    results: dict[str, dict] = {}
    for p in predictors:
        print(f"Fitting {p.name}...")
        p.fit(train)
        print(f"Evaluating {p.name}...")
        metrics = evaluate_predictor(p, test_clauses)
        print(
            f"  {p.name}: top1={metrics['top1_accuracy']:.3f} "
            f"top3={metrics['top3_accuracy']:.3f} "
            f"macroF1={metrics['macro_f1']:.3f} (n={metrics['n']})"
        )
        results[p.name] = {k: v for k, v in metrics.items() if k not in {"y_true", "predictions_top1"}}

    threshold_info = None
    if not args.skip_threshold_tuning:
        print("Tuning TF-IDF threshold via 5-fold CV on train split...")
        threshold_info = tune_threshold(train, seed=args.seed)
        print(f"  chosen threshold = {threshold_info['chosen']}")

    # Confusion matrix for the TF-IDF model
    tfidf_metrics = next((evaluate_predictor(p, test_clauses) for p in predictors if p.name == "tfidf"), None)
    if tfidf_metrics:
        plot_confusion(
            tfidf_metrics["y_true"],
            tfidf_metrics["predictions_top1"],
            CLAUSE_TYPES,
            EVAL_DIR / "confusion_matrix.png",
        )

    out = {
        "seed": args.seed,
        "test_frac": args.test_frac,
        "n_train_contracts": len(train),
        "n_test_contracts": len(test),
        "n_test_clauses": len(test_clauses),
        "predictors": results,
        "threshold_tuning": threshold_info,
    }
    out_path = EVAL_DIR / "classifier_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
