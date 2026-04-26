"""Qualitative-coding CLI for free-text study feedback.

Codebook (fixed; change only if you re-open the pre-registration):

    clarity       — comment is about how clear / unclear the explanation was
    trust         — comment is about trust / skepticism of the AI
    length        — comment is about wanting more / less content
    accuracy      — comment questions whether the explanation is factually right
    usability     — comment is about UI / interaction / flow
    other         — anything that does not fit the above

Usage:
    python -m src.qualitative_analysis code <rater_name>     # interactive
    python -m src.qualitative_analysis report                # to evaluation/qualitative_themes.md
    python -m src.qualitative_analysis kappa                 # Cohen's κ across raters
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from src.metrics import load_events_by_type

CODES = ["clarity", "trust", "length", "accuracy", "usability", "other"]
DATA_DIR = Path(__file__).parent.parent / "data"
CODES_PATH = DATA_DIR / "qualitative_codes.csv"
EVAL_DIR = Path(__file__).parent.parent / "evaluation"
REPORT_PATH = EVAL_DIR / "qualitative_themes.md"


# ---------- Storage ----------

def _ensure_csv():
    DATA_DIR.mkdir(exist_ok=True)
    if not CODES_PATH.exists():
        with open(CODES_PATH, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["participant_id", "rater", "comment", "codes", "notes"])


def load_codes() -> list[dict]:
    if not CODES_PATH.exists():
        return []
    with open(CODES_PATH, newline="") as f:
        return list(csv.DictReader(f))


def save_code(row: dict) -> None:
    _ensure_csv()
    with open(CODES_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["participant_id", "rater", "comment", "codes", "notes"])
        w.writerow(row)


# ---------- Comment source ----------

def load_comments() -> list[dict]:
    out = []
    for e in load_events_by_type("feedback_submitted"):
        text = (e.get("data") or {}).get("text", "").strip()
        if text:
            out.append({"participant_id": e["participant_id"], "comment": text})
    return out


# ---------- CLI: code ----------

def _print_codebook():
    print("\nCodebook:")
    for i, code in enumerate(CODES, start=1):
        print(f"  {i}. {code}")
    print("  Enter codes as comma-separated numbers (e.g., '1,4') or names.\n")


def _parse_codes(raw: str) -> list[str]:
    parts = [p.strip().lower() for p in raw.replace(";", ",").split(",") if p.strip()]
    resolved: list[str] = []
    for p in parts:
        if p.isdigit():
            i = int(p)
            if 1 <= i <= len(CODES):
                resolved.append(CODES[i - 1])
        elif p in CODES:
            resolved.append(p)
    # dedupe, keep order
    seen: set[str] = set()
    out: list[str] = []
    for c in resolved:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:3]


def code_comments(rater: str) -> None:
    comments = load_comments()
    existing = load_codes()
    already = {(r["participant_id"], r["rater"]) for r in existing}
    todo = [c for c in comments if (c["participant_id"], rater) not in already]
    if not todo:
        print(f"No new comments to code for rater '{rater}'. ({len(comments)} total comments in log.)")
        return

    _print_codebook()
    print(f"Rater: {rater}. {len(todo)} comment(s) to code. Enter 'q' to stop.\n")
    for i, c in enumerate(todo, start=1):
        print(f"[{i}/{len(todo)}] pid={c['participant_id']}")
        print(f"  Comment: {c['comment']}")
        raw = input("  Codes: ").strip()
        if raw.lower() == "q":
            print("Stopped.")
            return
        codes = _parse_codes(raw)
        if not codes:
            print("  [skipped — no valid codes]")
            continue
        notes = input("  Notes (optional): ").strip()
        save_code({
            "participant_id": c["participant_id"],
            "rater": rater,
            "comment": c["comment"],
            "codes": "|".join(codes),
            "notes": notes,
        })
        print(f"  saved: {codes}\n")


# ---------- CLI: report ----------

def build_report() -> None:
    rows = load_codes()
    if not rows:
        REPORT_PATH.parent.mkdir(exist_ok=True)
        REPORT_PATH.write_text("No qualitative codes yet. Run `python -m src.qualitative_analysis code <rater>` first.\n")
        return

    code_counts: Counter[str] = Counter()
    quotes_by_code: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        for code in r["codes"].split("|"):
            if not code:
                continue
            code_counts[code] += 1
            q = r["comment"].replace("\n", " ").strip()
            if len(quotes_by_code[code]) < 3 and q not in quotes_by_code[code]:
                quotes_by_code[code].append(q)

    total = sum(code_counts.values())
    lines = [
        "# Qualitative themes in pilot feedback",
        "",
        f"Based on **{len({r['participant_id'] for r in rows})}** participants' free-text feedback, "
        f"coded by **{len({r['rater'] for r in rows})}** rater(s). Total code assignments: **{total}**.",
        "",
        "| Code | Count | % of assignments |",
        "|---|---|---|",
    ]
    for code, count in sorted(code_counts.items(), key=lambda kv: kv[1], reverse=True):
        pct = 100.0 * count / total if total else 0.0
        lines.append(f"| {code} | {count} | {pct:.1f}% |")

    lines += ["", "## Representative quotes", ""]
    for code, _ in sorted(code_counts.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"### {code}")
        for q in quotes_by_code[code]:
            lines.append(f"- _{q}_")
        lines.append("")

    EVAL_DIR.mkdir(exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines).rstrip() + "\n")
    print(f"wrote {REPORT_PATH}")


# ---------- CLI: kappa ----------

def cohens_kappa_pairwise() -> dict[tuple[str, str], tuple[float, int]]:
    """Compute Cohen's κ per pair of raters on *presence* of each code.

    Treats each (participant_id, code) pair as a binary item: did the rater
    assign this code? κ reported across the full set of 6 codes × comments
    pooled. Requires ≥2 raters with overlapping coded participants.
    """
    rows = load_codes()
    by_rater: dict[str, dict[str, set[str]]] = defaultdict(dict)
    for r in rows:
        by_rater[r["rater"]][r["participant_id"]] = set(r["codes"].split("|"))

    raters = sorted(by_rater.keys())
    out: dict[tuple[str, str], tuple[float, int]] = {}
    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            a, b = raters[i], raters[j]
            overlap = set(by_rater[a]) & set(by_rater[b])
            if len(overlap) < 2:
                continue
            tp = fp = fn = tn = 0
            for pid in overlap:
                for code in CODES:
                    ra = code in by_rater[a][pid]
                    rb = code in by_rater[b][pid]
                    if ra and rb: tp += 1
                    elif ra and not rb: fp += 1
                    elif (not ra) and rb: fn += 1
                    else: tn += 1
            n = tp + fp + fn + tn
            po = (tp + tn) / n if n else 0.0
            p_yes_a = (tp + fp) / n if n else 0.0
            p_yes_b = (tp + fn) / n if n else 0.0
            pe = p_yes_a * p_yes_b + (1 - p_yes_a) * (1 - p_yes_b)
            kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
            out[(a, b)] = (kappa, len(overlap))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    action = sys.argv[1]
    if action == "code":
        if len(sys.argv) < 3:
            print("usage: python -m src.qualitative_analysis code <rater_name>", file=sys.stderr)
            sys.exit(1)
        code_comments(sys.argv[2])
    elif action == "report":
        build_report()
    elif action == "kappa":
        result = cohens_kappa_pairwise()
        if not result:
            print("Need ≥2 raters with ≥2 overlapping comments.")
        for (a, b), (k, n) in result.items():
            print(f"κ({a}, {b}) = {k:.3f}  (n={n} overlapping comments)")
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
