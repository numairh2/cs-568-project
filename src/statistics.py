"""Statistical analysis for the pilot study.

Takes the raw event log produced by ``src.metrics.track_event`` and
produces the numbers the Results Dashboard (and the presentation) needs:

- ``participant_frame(events)``  — one row per participant
- ``compare_conditions_anova(df, outcome)`` — ANOVA + Tukey HSD
- ``pairwise_t(df, outcome, c1, c2)`` — Welch's t, Cohen's d, 95% CI
- ``assumption_checks(values_by_condition)`` — Shapiro + Levene; fall back
  to Kruskal–Wallis / Mann–Whitney U if violated
- ``bootstrap_ci(values)`` — percentile bootstrap CI of the mean
- ``by_literacy_baseline(df)`` — median-split helper for H3

The pre-registration (``study/preregistration.md``) specifies α = 0.05
and Holm correction within the family of two planned contrasts per
outcome.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from scipy import stats  # type: ignore
except ImportError as e:  # pragma: no cover
    raise RuntimeError("scipy is required; pip install scipy") from e

try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd  # type: ignore
except ImportError:  # pragma: no cover
    pairwise_tukeyhsd = None  # type: ignore


# ---------- Event → tidy frame ------------------------------------------------

def participant_frame(events: list[dict]) -> pd.DataFrame:
    """One row per participant, columns:

    participant_id, condition, comprehension_score, comprehension_total,
    comprehension_pct, literacy_baseline_score, attention_pass,
    likert_<scale>, manip_yes_rate
    """
    by_pid: dict[str, dict] = {}
    for e in events:
        pid = e.get("participant_id")
        if not pid:
            continue
        row = by_pid.setdefault(pid, {"participant_id": pid})
        t = e.get("event_type")
        d = e.get("data", {})
        if t == "condition_assigned":
            row["condition"] = d.get("condition")
        elif t == "study_completed":
            correct = d.get("total_correct", 0)
            total = d.get("total_questions", 0) or 1
            row["comprehension_score"] = correct
            row["comprehension_total"] = total
            row["comprehension_pct"] = 100.0 * correct / total
            row["literacy_baseline_score"] = d.get("literacy_baseline_score")
            row["attention_pass"] = d.get("attention_check_passed")
        elif t == "likert_response":
            row[f"likert_{d.get('scale')}"] = d.get("rating")
        elif t == "manipulation_check":
            ans = d.get("answer", "")
            row.setdefault("_manip_total", 0)
            row.setdefault("_manip_yes", 0)
            row["_manip_total"] += 1
            if ans.startswith("Yes"):
                row["_manip_yes"] += 1

    for row in by_pid.values():
        mt = row.pop("_manip_total", None)
        my = row.pop("_manip_yes", None)
        row["manip_yes_rate"] = (my / mt) if mt else None

    df = pd.DataFrame(list(by_pid.values()))
    if df.empty:
        return df
    # Keep only participants who actually completed the study.
    df = df[df.get("comprehension_total").notna()] if "comprehension_total" in df else df
    return df.reset_index(drop=True)


def apply_preregistered_exclusions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split into (primary, excluded) per the pre-registered rule:
    must have attention_pass == True and manip_yes_rate >= 0.5 (if applicable).
    """
    if df.empty:
        return df, df
    primary = df.copy()
    excluded_mask = primary["attention_pass"].astype("boolean").fillna(False).eq(False)
    if "manip_yes_rate" in primary:
        manip = primary["manip_yes_rate"].astype("float64").fillna(1.0)  # control has no manip checks
        excluded_mask = excluded_mask | (manip < 0.5)
    excluded = primary[excluded_mask]
    primary = primary[~excluded_mask]
    return primary.reset_index(drop=True), excluded.reset_index(drop=True)


# ---------- Descriptive stats -------------------------------------------------

def bootstrap_ci(values: Iterable[float], n_boot: int = 10000, ci: float = 0.95, seed: int = 0) -> tuple[float, float]:
    arr = np.asarray([v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))], dtype=float)
    if arr.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    boots = rng.choice(arr, size=(n_boot, arr.size), replace=True).mean(axis=1)
    lo = float(np.quantile(boots, (1 - ci) / 2))
    hi = float(np.quantile(boots, 1 - (1 - ci) / 2))
    return lo, hi


def descriptives_by_condition(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    rows = []
    for cond, sub in df.groupby("condition", dropna=True):
        vals = sub[outcome].dropna().astype(float)
        lo, hi = bootstrap_ci(vals.tolist()) if len(vals) else (float("nan"), float("nan"))
        rows.append({
            "condition": cond,
            "n": int(len(vals)),
            "mean": float(vals.mean()) if len(vals) else float("nan"),
            "sd": float(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
            "ci_lo": lo,
            "ci_hi": hi,
        })
    return pd.DataFrame(rows).sort_values("condition").reset_index(drop=True)


# ---------- Assumption checks -------------------------------------------------

@dataclass
class AssumptionReport:
    shapiro: dict[str, tuple[float, float]]  # cond -> (W, p)
    levene: tuple[float, float]              # (stat, p)
    violated: bool


def assumption_checks(values_by_condition: dict[str, list[float]]) -> AssumptionReport:
    shapiro: dict[str, tuple[float, float]] = {}
    any_violated = False
    for cond, vals in values_by_condition.items():
        if len(vals) >= 3:
            w, p = stats.shapiro(vals)
            shapiro[cond] = (float(w), float(p))
            if p < 0.05:
                any_violated = True
        else:
            shapiro[cond] = (float("nan"), float("nan"))
    groups = [v for v in values_by_condition.values() if len(v) >= 2]
    if len(groups) >= 2:
        stat, p = stats.levene(*groups, center="median")
        lev = (float(stat), float(p))
        if p < 0.05:
            any_violated = True
    else:
        lev = (float("nan"), float("nan"))
    return AssumptionReport(shapiro=shapiro, levene=lev, violated=any_violated)


# ---------- Omnibus tests -----------------------------------------------------

@dataclass
class AnovaResult:
    test: str                  # "anova" or "kruskal"
    statistic: float
    p_value: float
    df_between: int
    df_within: int
    eta_sq: float | None
    tukey_rows: list[dict]     # pairwise comparisons (empty if not applicable)
    fell_back: bool


def compare_conditions_anova(df: pd.DataFrame, outcome: str) -> AnovaResult | None:
    sub = df[["condition", outcome]].dropna()
    if sub.empty:
        return None
    groups = [g[outcome].astype(float).tolist() for _, g in sub.groupby("condition")]
    groups = [g for g in groups if len(g) >= 2]
    if len(groups) < 2:
        return None

    values_by_cond = {cond: g[outcome].astype(float).tolist() for cond, g in sub.groupby("condition")}
    checks = assumption_checks(values_by_cond)

    if checks.violated:
        stat, p = stats.kruskal(*groups)
        return AnovaResult(
            test="kruskal",
            statistic=float(stat),
            p_value=float(p),
            df_between=len(groups) - 1,
            df_within=sum(len(g) for g in groups) - len(groups),
            eta_sq=None,
            tukey_rows=[],
            fell_back=True,
        )

    f, p = stats.f_oneway(*groups)
    # Eta squared = SS_between / SS_total
    all_vals = np.concatenate([np.asarray(g, dtype=float) for g in groups])
    grand_mean = all_vals.mean()
    ss_total = float(((all_vals - grand_mean) ** 2).sum())
    ss_between = float(sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups))
    eta_sq = (ss_between / ss_total) if ss_total > 0 else 0.0

    tukey_rows: list[dict] = []
    if pairwise_tukeyhsd is not None and len(groups) >= 2:
        try:
            tk = pairwise_tukeyhsd(sub[outcome].astype(float), sub["condition"], alpha=0.05)
            for row in tk._results_table.data[1:]:  # type: ignore[attr-defined]
                tukey_rows.append({
                    "group1": row[0], "group2": row[1],
                    "mean_diff": float(row[2]), "p_adj": float(row[3]),
                    "lower": float(row[4]), "upper": float(row[5]),
                    "reject": bool(row[6]),
                })
        except Exception:  # pragma: no cover
            tukey_rows = []

    return AnovaResult(
        test="anova",
        statistic=float(f),
        p_value=float(p),
        df_between=len(groups) - 1,
        df_within=sum(len(g) for g in groups) - len(groups),
        eta_sq=float(eta_sq),
        tukey_rows=tukey_rows,
        fell_back=False,
    )


# ---------- Pairwise contrasts ------------------------------------------------

@dataclass
class PairwiseResult:
    test: str                  # "welch_t" or "mann_whitney"
    c1: str
    c2: str
    n1: int
    n2: int
    mean_diff: float
    cohens_d: float | None
    rank_biserial: float | None
    ci_lo: float
    ci_hi: float
    p_value: float


def pairwise_t(df: pd.DataFrame, outcome: str, c1: str, c2: str, n_boot: int = 5000, seed: int = 0) -> PairwiseResult | None:
    a = df[df["condition"] == c1][outcome].dropna().astype(float).tolist()
    b = df[df["condition"] == c2][outcome].dropna().astype(float).tolist()
    if len(a) < 2 or len(b) < 2:
        return None

    assumptions_ok = True
    for group in (a, b):
        if len(group) >= 3:
            if stats.shapiro(group).pvalue < 0.05:
                assumptions_ok = False
                break

    if assumptions_ok:
        stat, p = stats.ttest_ind(a, b, equal_var=False)
        # Cohen's d using pooled SD.
        s1, s2 = np.std(a, ddof=1), np.std(b, ddof=1)
        n1, n2 = len(a), len(b)
        sp = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2)) if (n1 + n2) > 2 else 0.0
        d = ((np.mean(a) - np.mean(b)) / sp) if sp > 0 else 0.0
        # Bootstrap CI of the mean difference.
        rng = np.random.default_rng(seed)
        diffs = []
        for _ in range(n_boot):
            da = rng.choice(a, size=n1, replace=True)
            db = rng.choice(b, size=n2, replace=True)
            diffs.append(np.mean(da) - np.mean(db))
        lo, hi = float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))
        return PairwiseResult(
            test="welch_t",
            c1=c1, c2=c2, n1=n1, n2=n2,
            mean_diff=float(np.mean(a) - np.mean(b)),
            cohens_d=float(d),
            rank_biserial=None,
            ci_lo=lo, ci_hi=hi,
            p_value=float(p),
        )

    # Non-parametric fallback: Mann-Whitney U with rank-biserial.
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    n1, n2 = len(a), len(b)
    r_rb = 1 - 2 * float(u) / (n1 * n2) if (n1 * n2) else 0.0
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        da = rng.choice(a, size=n1, replace=True)
        db = rng.choice(b, size=n2, replace=True)
        diffs.append(np.mean(da) - np.mean(db))
    lo, hi = float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))
    return PairwiseResult(
        test="mann_whitney",
        c1=c1, c2=c2, n1=n1, n2=n2,
        mean_diff=float(np.mean(a) - np.mean(b)),
        cohens_d=None,
        rank_biserial=float(r_rb),
        ci_lo=lo, ci_hi=hi,
        p_value=float(p),
    )


def holm_correct(p_values: list[float]) -> list[float]:
    """Return Holm-adjusted p-values, preserving input order."""
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    m = len(p_values)
    adj = [0.0] * m
    running_max = 0.0
    for rank, i in enumerate(order):
        candidate = (m - rank) * p_values[i]
        running_max = max(running_max, candidate)
        adj[i] = min(running_max, 1.0)
    return adj


# ---------- Stratification ----------------------------------------------------

def by_literacy_baseline(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return {'low': df_below_median, 'high': df_at_or_above_median}."""
    if df.empty or "literacy_baseline_score" not in df:
        return {"low": df.iloc[:0], "high": df.iloc[:0]}
    scores = df["literacy_baseline_score"].dropna()
    if scores.empty:
        return {"low": df.iloc[:0], "high": df.iloc[:0]}
    median = float(scores.median())
    low = df[df["literacy_baseline_score"] < median]
    high = df[df["literacy_baseline_score"] >= median]
    return {"low": low.reset_index(drop=True), "high": high.reset_index(drop=True)}


# ---------- Synthetic events generator (for development only) -----------------

def synth_events(n_per_condition: int = 10, effect: float = 0.15, seed: int = 1) -> list[dict]:
    """Fabricate an event log with a planted comprehension effect.

    Used by tests and the dashboard smoke check; not exposed in the UI.
    Effect size ``effect`` is added to the pass probability per item for
    ``treatment_full`` vs ``control``, with ``treatment_basic`` halfway
    between.
    """
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    out: list[dict] = []
    conditions = ["control", "treatment_basic", "treatment_full"]
    for cond in conditions:
        boost = {"control": 0.0, "treatment_basic": effect / 2, "treatment_full": effect}[cond]
        for _ in range(n_per_condition):
            pid = f"s{rng.randrange(10**8):08d}"
            out.append({"timestamp": 0.0, "participant_id": pid, "event_type": "condition_assigned", "data": {"condition": cond}})
            lit = int(nrng.integers(0, 6))
            total_q = 24
            # Each correct answer is bernoulli(0.5 + boost + small literacy boost).
            p = 0.5 + boost + 0.03 * (lit - 2)
            p = max(0.05, min(0.95, p))
            correct = int(nrng.binomial(total_q, p))
            out.append({"timestamp": 0.0, "participant_id": pid, "event_type": "study_completed", "data": {
                "condition": cond,
                "total_correct": correct,
                "total_questions": total_q,
                "literacy_baseline_score": lit,
                "attention_check_passed": True,
            }})
            for scale in ("confidence", "complexity", "willingness", "helpfulness"):
                rating = int(np.clip(nrng.normal(3 + boost * 4, 1), 1, 5))
                out.append({"timestamp": 0.0, "participant_id": pid, "event_type": "likert_response", "data": {"scale": scale, "rating": rating}})
            if cond != "control":
                rating = int(np.clip(nrng.normal(3 + boost * 4, 1), 1, 5))
                out.append({"timestamp": 0.0, "participant_id": pid, "event_type": "likert_response", "data": {"scale": "trust", "rating": rating}})
    return out


if __name__ == "__main__":  # pragma: no cover
    # Smoke run for the module itself.
    events = synth_events(n_per_condition=15, effect=0.2, seed=42)
    df = participant_frame(events)
    primary, excluded = apply_preregistered_exclusions(df)
    print(f"primary n={len(primary)}, excluded n={len(excluded)}")
    print(descriptives_by_condition(primary, "comprehension_pct").to_string(index=False))
    r = compare_conditions_anova(primary, "comprehension_pct")
    if r:
        print(f"\n{r.test}: stat={r.statistic:.3f} p={r.p_value:.4f} eta_sq={r.eta_sq}")
        for row in r.tukey_rows:
            print("  Tukey:", row)
    pw = pairwise_t(primary, "comprehension_pct", "treatment_full", "control")
    if pw:
        print(f"\nfull vs control: mean_diff={pw.mean_diff:.2f} d={pw.cohens_d} p={pw.p_value:.4f} CI=[{pw.ci_lo:.2f},{pw.ci_hi:.2f}]")
