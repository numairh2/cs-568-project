"""Load and process the CUAD dataset for clause extraction.

We fetch CUAD's ``data.zip`` from the Atticus Project GitHub release and
parse the SQuAD-format JSON ourselves. We used to go through HuggingFace
``datasets``, but ``datasets`` >= 3.0 dropped support for script-based
datasets (and CUAD is distributed as a loader script), so direct fetch
is the portable option.
"""

import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path

# The 41 CUAD clause types
CLAUSE_TYPES = [
    "Document Name", "Parties", "Agreement Date", "Effective Date",
    "Expiration Date", "Renewal Term", "Notice Period To Terminate Renewal",
    "Governing Law", "Most Favored Nation", "Non-Compete",
    "Exclusivity", "No-Solicit Of Customers", "No-Solicit Of Employees",
    "Non-Disparagement", "Termination For Convenience",
    "Rofr/Rofo/Rofn", "Change Of Control", "Anti-Assignment",
    "Revenue/Profit Sharing", "Price Restrictions",
    "Minimum Commitment", "Volume Restriction",
    "Ip Ownership Assignment", "Joint Ip Ownership",
    "License Grant", "Non-Transferable License",
    "Affiliate License-Licensor", "Affiliate License-Licensee",
    "Unlimited/All-You-Can-Eat-License", "Irrevocable Or Perpetual License",
    "Source Code Escrow", "Post-Termination Services",
    "Audit Rights", "Uncapped Liability", "Cap On Liability",
    "Liquidated Damages", "Warranty Duration",
    "Insurance", "Covenant Not To Sue",
    "Third Party Beneficiary",
]

# Clauses that are typically high-risk for the agreeing party
HIGH_RISK_CLAUSES = {
    "Uncapped Liability",
    "Non-Compete",
    "Termination For Convenience",
    "Change Of Control",
    "Anti-Assignment",
    "Covenant Not To Sue",
    "Liquidated Damages",
    "Exclusivity",
    "No-Solicit Of Customers",
    "No-Solicit Of Employees",
}

MEDIUM_RISK_CLAUSES = {
    "Non-Disparagement",
    "Most Favored Nation",
    "Ip Ownership Assignment",
    "Revenue/Profit Sharing",
    "Price Restrictions",
    "Minimum Commitment",
    "Volume Restriction",
    "Audit Rights",
}

RISK_COLORS = {
    "high": "#ff4b4b",
    "medium": "#ffa726",
    "low": "#66bb6a",
}


def get_clause_risk(clause_type):
    """Return risk level for a clause type: 'high', 'medium', or 'low'."""
    if clause_type in HIGH_RISK_CLAUSES:
        return "high"
    elif clause_type in MEDIUM_RISK_CLAUSES:
        return "medium"
    return "low"


CUAD_URL = "https://github.com/TheAtticusProject/cuad/raw/main/data.zip"
CUAD_CACHE_DIR = Path(__file__).parent.parent / "data" / "cuad"


def _download_cuad(cache_dir: Path = CUAD_CACHE_DIR) -> Path:
    """Download and extract CUAD's data.zip into ``cache_dir`` (idempotent)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    train_path = cache_dir / "train_separate_questions.json"
    test_path = cache_dir / "test.json"
    if train_path.exists() and test_path.exists():
        return cache_dir

    with urllib.request.urlopen(CUAD_URL) as resp:
        raw = resp.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for member in zf.namelist():
            if member.endswith("/") or os.path.isabs(member) or ".." in member:
                continue
            name = os.path.basename(member)
            if name in {"train_separate_questions.json", "test.json", "CUAD_v1.json"}:
                with zf.open(member) as src, open(cache_dir / name, "wb") as dst:
                    dst.write(src.read())
    return cache_dir


def _squad_to_entries(squad_json: dict) -> list[dict]:
    """Flatten SQuAD-format CUAD into the per-QA entry shape the rest of this
    module expects (matching the old HF ``cuad-qa`` loader output).
    """
    entries = []
    for example in squad_json.get("data", []):
        title = (example.get("title") or "").strip()
        for paragraph in example.get("paragraphs", []):
            context = (paragraph.get("context") or "").strip()
            for qa in paragraph.get("qas", []):
                answers = qa.get("answers", []) or []
                entries.append({
                    "id": qa.get("id"),
                    "title": title,
                    "context": context,
                    "question": (qa.get("question") or "").strip(),
                    "answers": {
                        "text": [(a.get("text") or "").strip() for a in answers],
                        "answer_start": [a.get("answer_start", 0) for a in answers],
                    },
                })
    return entries


def load_cuad():
    """Load the CUAD dataset. Returns a dict with ``train`` and ``test`` keys,
    each a list of per-QA entries (same shape as the old HF output)."""
    cache_dir = _download_cuad()
    splits = {}
    for split, fname in (("train", "train_separate_questions.json"), ("test", "test.json")):
        path = cache_dir / fname
        if path.exists():
            with open(path, encoding="utf-8") as f:
                splits[split] = _squad_to_entries(json.load(f))
    return splits


def extract_clauses_from_cuad(dataset_split):
    """Extract clause annotations grouped by contract from CUAD.

    ``dataset_split`` is a list of per-QA entries (as returned by
    ``load_cuad()[split]``), each with:
      - context: the contract text
      - question: a question encoding the clause type
      - answers: {"text": [...], "answer_start": [...]}
      - title: contract title

    Returns:
        dict mapping contract title -> {
            "context": full contract text,
            "clauses": [{"clause_type": str, "text": str, "start": int}, ...]
        }
    """
    contracts = {}
    for entry in dataset_split:
        title = entry.get("title", "Untitled")
        context = entry["context"]

        if title not in contracts:
            contracts[title] = {
                "context": context,
                "clauses": [],
            }

        # Parse clause type from the question field
        question = entry.get("question", "")
        clause_type = _parse_clause_type(question)

        answers = entry.get("answers", {})
        texts = answers.get("text", [])
        starts = answers.get("answer_start", [])

        for text, start in zip(texts, starts):
            if text.strip():
                contracts[title]["clauses"].append({
                    "clause_type": clause_type,
                    "text": text.strip(),
                    "start": start,
                    "risk": get_clause_risk(clause_type),
                })

    return contracts


def _parse_clause_type(question):
    """Extract clause type name from a CUAD question string.

    CUAD questions follow patterns like:
    'Highlight the parts (if any) of this contract related to "Non-Compete"...'
    """
    for clause_type in CLAUSE_TYPES:
        if clause_type.lower() in question.lower():
            return clause_type
    # Fallback: return the question truncated
    return question[:50] if question else "Unknown"


def get_sample_contracts(dataset, n=10, split="test"):
    """Get n sample contracts with their clause annotations.

    Returns a list of dicts with title, context preview, clause count, risk summary.
    """
    contracts = extract_clauses_from_cuad(dataset[split])
    samples = []
    for title, data in list(contracts.items())[:n]:
        if not data["clauses"]:
            continue
        risk_counts = {"high": 0, "medium": 0, "low": 0}
        clause_types = set()
        for c in data["clauses"]:
            risk_counts[c["risk"]] += 1
            clause_types.add(c["clause_type"])
        samples.append({
            "title": title,
            "context": data["context"],
            "clauses": data["clauses"],
            "clause_types": sorted(clause_types),
            "risk_summary": risk_counts,
            "total_clauses": len(data["clauses"]),
        })
    return samples
