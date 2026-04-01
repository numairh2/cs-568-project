"""Legal term glossary for jargon highlighting."""

# Common legal terms and their plain-English definitions
LEGAL_GLOSSARY = {
    "indemnify": "To promise to pay for someone else's losses or damages",
    "indemnification": "A promise to cover someone else's losses or legal costs",
    "liability": "Legal responsibility for something, especially costs or damages",
    "negligence": "Failure to take reasonable care, resulting in harm",
    "arbitration": "Settling a dispute through a private judge instead of a court",
    "binding arbitration": "A dispute resolution process where the decision is final and you cannot appeal to a court",
    "jurisdiction": "The authority of a court to hear and decide a case",
    "governing law": "Which state or country's laws apply to this agreement",
    "severability": "If one part of the contract is invalid, the rest still applies",
    "waiver": "Giving up a right or claim voluntarily",
    "covenant": "A formal promise or agreement in a contract",
    "non-compete": "A promise not to work for competitors or start a competing business",
    "non-solicitation": "A promise not to recruit employees or customers away",
    "non-disclosure": "A promise to keep certain information secret",
    "confidentiality": "The obligation to keep information private and not share it",
    "intellectual property": "Creations of the mind: inventions, designs, brand names, written works",
    "proprietary": "Owned by a specific company; not for public use",
    "license": "Permission to use something under specific conditions",
    "sublicense": "Permission to let someone else use a license you were given",
    "revocable": "Can be taken back or cancelled",
    "irrevocable": "Cannot be taken back or cancelled once granted",
    "perpetual": "Lasting forever; no end date",
    "termination": "Ending the agreement",
    "breach": "Breaking a promise or rule in the contract",
    "remedy": "A way to fix or compensate for a breach of contract",
    "damages": "Money paid as compensation for loss or injury",
    "consequential damages": "Indirect losses that result from a breach (e.g., lost profits)",
    "liquidated damages": "A pre-agreed amount of money to be paid if the contract is broken",
    "force majeure": "Unforeseeable events (war, natural disaster) that excuse non-performance",
    "good faith": "Acting honestly and fairly, without trying to deceive",
    "fiduciary": "A person trusted to act in another's best interest",
    "assignee": "A person or entity that receives rights transferred from another",
    "assignor": "A person or entity that transfers rights to another",
    "lien": "A legal claim on property as security for a debt",
    "escrow": "Money or property held by a third party until conditions are met",
    "warrant": "To guarantee or promise something is true",
    "warranty": "A guarantee that something is true or will work as described",
    "disclaimer": "A statement limiting responsibility or denying liability",
    "statute of limitations": "The time limit for filing a legal claim",
    "tort": "A wrongful act (other than breach of contract) that causes harm",
    "plaintiff": "The person who brings a case to court",
    "defendant": "The person being accused or sued in court",
    "deposition": "Sworn testimony given outside of court",
    "injunction": "A court order requiring someone to do or stop doing something",
    "consideration": "Something of value exchanged between parties in a contract",
    "herein": "In this document",
    "hereinafter": "From this point forward in this document",
    "whereas": "A word used to introduce background facts in a contract",
    "notwithstanding": "Despite; regardless of",
    "pursuant to": "In accordance with; following",
    "in lieu of": "Instead of",
}


def find_terms_in_text(text):
    """Find glossary terms present in the given text.

    Returns a list of (term, definition) tuples sorted by position in text.
    """
    text_lower = text.lower()
    found = []
    for term, definition in LEGAL_GLOSSARY.items():
        idx = text_lower.find(term.lower())
        if idx != -1:
            found.append((term, definition, idx))
    found.sort(key=lambda x: x[2])
    return [(term, defn) for term, defn, _ in found]


def highlight_terms_html(text):
    """Return HTML with glossary terms wrapped in styled spans with tooltips."""
    import re
    result = text
    for term in sorted(LEGAL_GLOSSARY.keys(), key=len, reverse=True):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        definition = LEGAL_GLOSSARY[term]
        replacement = (
            f'<span style="background-color: #fff3cd; padding: 1px 3px; '
            f'border-radius: 3px; cursor: help;" '
            f'title="{definition}">'
            f"\\g<0></span>"
        )
        result = pattern.sub(replacement, result, count=1)
    return result
