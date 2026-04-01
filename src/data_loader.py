"""Load and process the CUAD dataset for clause extraction."""

from datasets import load_dataset

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


def load_cuad():
    """Load the CUAD dataset from HuggingFace."""
    dataset = load_dataset("theatticusproject/cuad-qa", trust_remote_code=True)
    return dataset


def extract_clauses_from_cuad(dataset_split):
    """Extract clause annotations grouped by contract from the CUAD-QA dataset.

    The CUAD-QA format has entries with:
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
