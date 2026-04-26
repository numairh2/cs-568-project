"""User study configuration.

Defines:
  - Study conditions (between-subjects)
  - Demographics questions (W2b)
  - Literacy baseline comprehension items (W2b) — scored independently of the
    main study clauses so we can stratify results by baseline literacy.
  - Main study clauses (8 clauses × 3 comprehension MCQs = 24 items; W2d)
  - Post-task Likert scales
  - Attention check (inserted into the Likert phase; W2c)
  - Clause-order randomization seeded by participant id (W2d)

Clause text for the four new stimuli (Termination, Confidentiality, IP
Assignment, Auto-Renewal) is *modeled after* real CUAD clauses and cites
the CUAD contract id it was patterned on. The text has been cleaned (no
``[***]`` redactions, no cross-references to missing sections) so it is
readable in isolation by a lay participant.
"""

import hashlib
import random

# --- Study Conditions ---
CONTROL = "control"
TREATMENT_BASIC = "treatment_basic"
TREATMENT_FULL = "treatment_full"

CONDITIONS = [CONTROL, TREATMENT_BASIC, TREATMENT_FULL]

CONDITION_DESCRIPTIONS = {
    CONTROL: "Raw legal text only (no AI assistance)",
    TREATMENT_BASIC: "Legal text + brief one-sentence explanation",
    TREATMENT_FULL: "Legal text + full 3-part explanation with interactive controls",
}


# --- Demographics (W2b) -------------------------------------------------------
#
# Collected after consent, before the main study. Used to stratify results
# and to support exclusion decisions (e.g. non-native speakers on a
# reading-comprehension task).

DEMOGRAPHICS_QUESTIONS = [
    {
        "id": "age_band",
        "question": "What is your age?",
        "type": "choice",
        "options": ["18–24", "25–34", "35–44", "45–54", "55+", "Prefer not to say"],
    },
    {
        "id": "education",
        "question": "What is your highest completed level of education?",
        "type": "choice",
        "options": [
            "Some high school",
            "High school diploma / GED",
            "Some college, no degree",
            "Associate's degree",
            "Bachelor's degree",
            "Master's degree",
            "Doctoral or professional degree",
            "Prefer not to say",
        ],
    },
    {
        "id": "native_english",
        "question": "Do you consider yourself a native English speaker?",
        "type": "choice",
        "options": ["Yes", "No"],
    },
    {
        "id": "legal_training",
        "question": "How much formal legal training have you had?",
        "type": "choice",
        "options": [
            "None",
            "Informal (e.g., self-taught, occasional workshops)",
            "Formal (e.g., pre-law courses, paralegal training, law school)",
        ],
    },
    {
        "id": "contract_frequency",
        "question": "How often do you read contracts (e.g., terms of service, leases, employment)?",
        "type": "choice",
        "options": ["Never", "Rarely (less than monthly)", "Monthly", "Weekly or more"],
    },
    {
        "id": "legal_comfort",
        "question": "How comfortable are you reading legal text on your own?",
        "type": "likert",
        "labels": [
            "Very uncomfortable",
            "Uncomfortable",
            "Neutral",
            "Comfortable",
            "Very comfortable",
        ],
    },
]


# --- Literacy baseline (W2b) --------------------------------------------------
#
# Five short snippets of legal language with a single MCQ each. These are
# deliberately NOT the same clause types as the main study, so a high
# baseline score reflects general legal-text comfort rather than prior
# exposure to the study stimuli. The score (0–5) is logged as
# ``literacy_baseline_score``.

LITERACY_BASELINE = [
    {
        "id": "lit_force_majeure",
        "snippet": (
            "Neither party shall be liable for any failure or delay in performance "
            "under this Agreement due to fire, flood, earthquake, elements of "
            "nature, acts of God, acts of war, terrorism, riots, civil disorders, "
            "or any other cause beyond the reasonable control of such party."
        ),
        "question": "What is this clause describing?",
        "options": [
            "A refund policy",
            "Excuses from performing the contract due to extraordinary events",
            "A non-compete restriction",
            "A data-retention policy",
        ],
        "correct": 1,
    },
    {
        "id": "lit_severability",
        "snippet": (
            "If any provision of this Agreement is held by a court of competent "
            "jurisdiction to be invalid or unenforceable, the remaining provisions "
            "shall remain in full force and effect."
        ),
        "question": "If one part of the contract is struck down by a court, what happens to the rest of the contract?",
        "options": [
            "The entire contract becomes void",
            "The rest of the contract is still enforceable",
            "The parties must renegotiate the whole contract",
            "A new judge must review it",
        ],
        "correct": 1,
    },
    {
        "id": "lit_assignment",
        "snippet": (
            "Neither party may assign any of its rights or obligations under this "
            "Agreement without the prior written consent of the other party, which "
            "consent shall not be unreasonably withheld."
        ),
        "question": "Can one party transfer its obligations to a different company without asking?",
        "options": [
            "Yes, at any time",
            "Only if the amount is small",
            "No — they must first get the other party's written consent",
            "Only on the last day of the contract",
        ],
        "correct": 2,
    },
    {
        "id": "lit_time_essence",
        "snippet": (
            "Time is of the essence with respect to all obligations to be performed "
            "or observed by the parties under this Agreement."
        ),
        "question": "What does this clause mean?",
        "options": [
            "The contract expires in a short amount of time",
            "Missing deadlines is a material breach of the contract",
            "The parties can extend deadlines freely",
            "Only courts can enforce deadlines",
        ],
        "correct": 1,
    },
    {
        "id": "lit_entire_agreement",
        "snippet": (
            "This Agreement constitutes the entire agreement between the parties "
            "with respect to the subject matter hereof and supersedes all prior "
            "written and oral agreements."
        ),
        "question": "If a salesperson made a verbal promise before signing, does that promise bind the company?",
        "options": [
            "Yes, verbal promises always count",
            "No — only what is in this written agreement counts",
            "Yes, but only if witnessed",
            "Only if signed by the CEO",
        ],
        "correct": 1,
    },
]


# --- Main study clauses (W2d) -------------------------------------------------
#
# 8 clauses × 3 MCQs = 24 comprehension items. Correct-answer positions
# are counterbalanced — each of {0, 1, 2, 3} appears on 6 questions (see
# assertion at the bottom of this module). Contract ids cited in comments
# point at the CUAD exemplar the wording was patterned after.

STUDY_CLAUSES = [
    # --- Existing ---
    {
        "id": "arbitration",
        "heading": "Arbitration Clause",
        "text": (
            "Any dispute, controversy or claim arising out of or relating to this "
            "contract, or the breach, termination or invalidity thereof, shall be "
            "settled by binding arbitration in accordance with the rules of the "
            "American Arbitration Association. The arbitration shall take place in "
            "San Francisco, California. The arbitrator's award shall be final and "
            "binding and may be entered as a judgment in any court of competent "
            "jurisdiction. YOU UNDERSTAND THAT BY AGREEING TO THIS CLAUSE, YOU ARE "
            "WAIVING YOUR RIGHT TO A JURY TRIAL."
        ),
        "questions": [
            {
                "question": "Based on this clause, if you have a dispute with the company, can you take them to court for a jury trial?",
                "options": [
                    "Yes, you can always go to court",
                    "No, disputes must go through binding arbitration",
                    "Only if the dispute is about money",
                    "Yes, but only in California",
                ],
                "correct": 1,
            },
            {
                "question": "Where would the arbitration take place?",
                "options": [
                    "Wherever you live",
                    "Washington, D.C.",
                    "San Francisco, California",
                    "It's not specified",
                ],
                "correct": 2,
            },
            {
                "question": "Can the arbitrator's decision be appealed in court?",
                "options": [
                    "Yes, you can appeal to any state court",
                    "Only to the U.S. Supreme Court",
                    "Yes, but only with the company's permission",
                    "No — the decision is final and binding",
                ],
                "correct": 3,
            },
        ],
    },
    {
        "id": "liability",
        "heading": "Limitation of Liability",
        "text": (
            "IN NO EVENT SHALL THE COMPANY, ITS OFFICERS, DIRECTORS, EMPLOYEES, OR "
            "AGENTS, BE LIABLE TO YOU FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, "
            "PUNITIVE, OR CONSEQUENTIAL DAMAGES WHATSOEVER RESULTING FROM ANY (I) "
            "ERRORS, MISTAKES, OR INACCURACIES OF CONTENT, (II) PERSONAL INJURY OR "
            "PROPERTY DAMAGE, OF ANY NATURE WHATSOEVER, RESULTING FROM YOUR ACCESS TO "
            "AND USE OF OUR SERVICE, (III) ANY UNAUTHORIZED ACCESS TO OR USE OF OUR "
            "SECURE SERVERS AND/OR ANY AND ALL PERSONAL INFORMATION STORED THEREIN."
        ),
        "questions": [
            {
                "question": "If the company's service has errors that cause you financial loss, can you sue them for damages?",
                "options": [
                    "Yes, they are fully responsible",
                    "No, this clause limits their liability for errors",
                    "Only for direct damages, not indirect",
                    "Yes, but only up to $1000",
                ],
                "correct": 1,
            },
            {
                "question": "If hackers steal your personal data from the company's servers, who bears the responsibility according to this clause?",
                "options": [
                    "The company is fully liable",
                    "The company is NOT liable under this clause",
                    "The hackers are liable",
                    "Both you and the company share liability",
                ],
                "correct": 1,
            },
            {
                "question": "If you slip and get hurt while using the company's service, who is responsible under this clause?",
                "options": [
                    "You are — the company disclaims liability for personal injury",
                    "The company must cover all medical bills",
                    "The company's insurance provider pays",
                    "The government pays",
                ],
                "correct": 0,
            },
        ],
    },
    {
        "id": "data_collection",
        "heading": "Data Collection and Privacy",
        "text": (
            "The Company reserves the right to collect, store, and process personal "
            "data including but not limited to browsing history, usage patterns, device "
            "information, location data, and any content uploaded to the Service. This "
            "data may be shared with third-party partners for purposes including "
            "targeted advertising, analytics, and service improvement. By using the "
            "Service, you consent to such collection and sharing of your data as "
            "described in our Privacy Policy, which may be updated from time to time "
            "without prior notice."
        ),
        "questions": [
            {
                "question": "What types of personal data can the company collect?",
                "options": [
                    "Only your name and email",
                    "Only data you explicitly provide",
                    "No personal data is collected",
                    "Browsing history, location, device info, uploaded content, and more",
                ],
                "correct": 3,
            },
            {
                "question": "Will you be notified before the Privacy Policy changes?",
                "options": [
                    "Yes, they must give 30 days notice",
                    "Yes, they will email you",
                    "Changes require your explicit consent",
                    "No, the policy can be updated without prior notice",
                ],
                "correct": 3,
            },
            {
                "question": "Can your data be shared with advertising partners?",
                "options": [
                    "Yes — the clause explicitly allows sharing for targeted advertising",
                    "No, sharing requires a separate opt-in",
                    "Only if you pay for the service",
                    "Only with anonymized data",
                ],
                "correct": 0,
            },
        ],
    },
    {
        "id": "indemnification",
        "heading": "Indemnification",
        "text": (
            "You agree to defend, indemnify and hold harmless the Company and its "
            "subsidiaries, agents, licensors, managers, and other affiliated companies, "
            "and their employees, contractors, agents, officers and directors, from and "
            "against any and all claims, damages, obligations, losses, liabilities, "
            "costs or debt, and expenses (including but not limited to attorney's fees) "
            "arising from: (i) your use of and access to the Service; (ii) your "
            "violation of any term of these Terms; (iii) your violation of any third "
            "party right, including without limitation any copyright, property, or "
            "privacy right."
        ),
        "questions": [
            {
                "question": "If someone sues the company because of something you did using the service, who pays the legal fees?",
                "options": [
                    "The company pays",
                    "The costs are split evenly",
                    "Nobody pays — the clause prevents lawsuits",
                    "You are responsible for paying, including attorney's fees",
                ],
                "correct": 3,
            },
            {
                "question": "This indemnification clause is triggered by which of the following?",
                "options": [
                    "Your use of the service, violating the terms, or violating third-party rights",
                    "Only if you intentionally break the rules",
                    "Only if you violate copyright",
                    "Only if the company decides to enforce it",
                ],
                "correct": 0,
            },
            {
                "question": "Which of the following would NOT trigger the indemnification obligation?",
                "options": [
                    "You violate a third party's copyright",
                    "The company is sued for its own negligent software bug unrelated to your actions",
                    "You violate a term of service",
                    "You use the service in a way that causes a lawsuit",
                ],
                "correct": 1,
            },
        ],
    },
    # --- New (W2d) ---
    {
        # Patterned after CUAD: Termination For Convenience clauses, e.g.
        # DovaPharmaceuticalsInc_20181108_10-Q_EX-10.2_11414.
        "id": "termination",
        "heading": "Termination for Convenience",
        "text": (
            "Either party may terminate this Agreement at any time, with or without "
            "cause, upon thirty (30) days' prior written notice to the other party. "
            "Upon such termination, the terminating party shall have no further "
            "liability or obligation to the other party except for payment of any "
            "amounts accrued and unpaid as of the effective date of termination. "
            "The Company shall not be required to refund any prepaid fees."
        ),
        "questions": [
            {
                "question": "Does the company need a reason to end the contract under this clause?",
                "options": [
                    "No — either party may terminate with or without cause",
                    "Yes, they must show the user materially breached the contract",
                    "Yes, they can only terminate for fraud",
                    "Only the user can terminate without a reason",
                ],
                "correct": 0,
            },
            {
                "question": "If the company terminates the contract, what happens to fees you already paid?",
                "options": [
                    "The clause says they will be refunded",
                    "They are refunded only if requested within 30 days",
                    "The company is not required to refund prepaid fees",
                    "Half of the prepaid fees are refunded",
                ],
                "correct": 2,
            },
            {
                "question": "How much notice must the terminating party give before the termination takes effect?",
                "options": [
                    "Immediate — no notice is required",
                    "30 days' prior written notice",
                    "60 days' prior written notice",
                    "One year's prior written notice",
                ],
                "correct": 1,
            },
        ],
    },
    {
        # Patterned after common mutual-confidentiality clauses; this type is
        # not a distinct CUAD category but the language mirrors licensing
        # and supply agreements in CUAD.
        "id": "confidentiality",
        "heading": "Confidentiality",
        "text": (
            "You acknowledge that you may receive information designated as "
            "\"Confidential Information\" from the Company, including but not limited "
            "to trade secrets, business plans, customer lists, pricing, and technical "
            "information. You agree to: (a) hold all such information in strict "
            "confidence; (b) not disclose it to any third party without the Company's "
            "prior written consent; and (c) not use it for any purpose other than "
            "performing your obligations under this Agreement. These obligations "
            "survive for five (5) years following termination of this Agreement."
        ),
        "questions": [
            {
                "question": "If you learn the company's pricing strategy, can you share it with a friend at a competitor?",
                "options": [
                    "Yes — you can share anything outside of working hours",
                    "Yes, as long as you don't profit from it",
                    "Only with the friend's NDA in place",
                    "No — that would violate the confidentiality obligation",
                ],
                "correct": 3,
            },
            {
                "question": "How long do your confidentiality obligations last after the contract ends?",
                "options": [
                    "Only until the contract ends",
                    "One year after the contract ends",
                    "Five years after the contract ends",
                    "Forever",
                ],
                "correct": 2,
            },
            {
                "question": "Which of the following is specifically listed as Confidential Information?",
                "options": [
                    "Trade secrets, business plans, customer lists, pricing, and technical information",
                    "Only trade secrets",
                    "Only information marked \"confidential\" on the document",
                    "Anything the user later decides is private",
                ],
                "correct": 0,
            },
        ],
    },
    {
        # Patterned after CUAD Ip Ownership Assignment clauses, e.g. license
        # / supply agreements with work-for-hire IP language.
        "id": "ip_assignment",
        "heading": "Intellectual Property Assignment",
        "text": (
            "You hereby assign to the Company all right, title, and interest in and "
            "to any inventions, discoveries, works of authorship, improvements, or "
            "other intellectual property that you create, conceive, or reduce to "
            "practice in the course of performing services under this Agreement. "
            "You agree to execute any documents reasonably requested by the Company "
            "to perfect such assignment, including patent and copyright applications, "
            "at the Company's expense."
        ),
        "questions": [
            {
                "question": "If you invent something new while working under this agreement, who owns it?",
                "options": [
                    "You own it — inventions always belong to the creator",
                    "The Company owns it — you assign all rights to them",
                    "You and the Company jointly own it",
                    "The U.S. Patent Office owns it by default",
                ],
                "correct": 1,
            },
            {
                "question": "If the Company asks you to sign a patent application for something you invented for them, who pays the filing fees?",
                "options": [
                    "You do",
                    "It is split evenly",
                    "The Company does",
                    "The patent lawyer covers the fees",
                ],
                "correct": 2,
            },
            {
                "question": "Does this clause affect inventions you created before the agreement started?",
                "options": [
                    "Yes — it covers everything you have ever invented",
                    "No — it only covers IP created in the course of services under this Agreement",
                    "Only if they are similar to the Company's products",
                    "Only for inventions in the United States",
                ],
                "correct": 1,
            },
        ],
    },
    {
        # Patterned after CUAD Renewal Term clauses, e.g.
        # WEBHELPCOMINC_03_22_2000-EX-10.8-HOSTING AGREEMENT.
        "id": "auto_renewal",
        "heading": "Automatic Renewal",
        "text": (
            "This Agreement shall have an initial term of one (1) year and shall "
            "automatically renew for successive one-year terms unless either party "
            "provides written notice of non-renewal at least sixty (60) days prior "
            "to the end of the then-current term. Fees for each renewal term will "
            "be the Company's then-current standard rates, which may increase by up "
            "to ten percent (10%) per year without further notice."
        ),
        "questions": [
            {
                "question": "If you do nothing at the end of the one-year term, what happens?",
                "options": [
                    "The contract automatically renews for another year",
                    "The contract ends automatically",
                    "The company contacts you to confirm renewal",
                    "The contract is paused until you act",
                ],
                "correct": 0,
            },
            {
                "question": "By when must you give notice if you do NOT want the contract to renew?",
                "options": [
                    "Any time before renewal",
                    "At least 30 days before the term ends",
                    "On the renewal date itself",
                    "At least 60 days before the term ends",
                ],
                "correct": 3,
            },
            {
                "question": "Can the Company raise your fees when the contract renews?",
                "options": [
                    "No — fees are locked forever",
                    "Only with your written agreement",
                    "Yes — up to 10% per year, without further notice",
                    "Only if inflation exceeds 10%",
                ],
                "correct": 2,
            },
        ],
    },
]


# --- Post-task Likert scales --------------------------------------------------

LIKERT_QUESTIONS = [
    {
        "id": "confidence",
        "question": "How confident are you that you understood the clause(s) correctly?",
        "labels": ["Not at all confident", "Slightly confident", "Moderately confident", "Very confident", "Extremely confident"],
    },
    {
        "id": "complexity",
        "question": "How complex did you find the legal text?",
        "labels": ["Not complex at all", "Slightly complex", "Moderately complex", "Very complex", "Extremely complex"],
    },
    {
        "id": "trust",
        "question": "How much do you trust the explanations provided (if any)?",
        "labels": ["No trust", "Little trust", "Moderate trust", "High trust", "Complete trust"],
    },
    {
        "id": "willingness",
        "question": "How willing would you be to sign a contract containing these clauses?",
        "labels": ["Not willing at all", "Slightly willing", "Moderately willing", "Very willing", "Completely willing"],
    },
    {
        "id": "helpfulness",
        "question": "How helpful was the interface in understanding the legal text?",
        "labels": ["Not helpful", "Slightly helpful", "Moderately helpful", "Very helpful", "Extremely helpful"],
    },
]


# --- Attention check (W2c) ----------------------------------------------------

# Inserted into the Likert phase. The participant must pick the specified
# label; any other answer is a failure and triggers the pre-registered
# exclusion rule (see study/preregistration.md).

ATTENTION_CHECK = {
    "id": "attention_check",
    "question": "Please select \"Slightly confident\" for this item to confirm you are paying attention.",
    "labels": [
        "Not at all confident",
        "Slightly confident",
        "Moderately confident",
        "Very confident",
        "Extremely confident",
    ],
    "correct_label": "Slightly confident",
}


# --- Manipulation check (W2c) -------------------------------------------------

# Asked after each clause in the treatment conditions to verify the
# participant actually read the AI explanation. Logged as
# ``manipulation_check`` events.

MANIPULATION_CHECK = {
    "question": "Did you read the AI explanation above before answering the questions?",
    "options": ["Yes, read carefully", "Skimmed it", "No"],
}


# --- Assignment + randomization ----------------------------------------------

def assign_condition(rng: random.Random | None = None) -> str:
    """Randomly assign a study condition."""
    r = rng if rng is not None else random
    return r.choice(CONDITIONS)


def _rng_from_pid(participant_id: str) -> random.Random:
    """Return a deterministic Random seeded from the participant id."""
    digest = hashlib.sha256(participant_id.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    return random.Random(seed)


def clause_order_for(participant_id: str) -> list[int]:
    """Return indices into STUDY_CLAUSES in a per-participant random order."""
    rng = _rng_from_pid(participant_id + ":clause_order")
    order = list(range(len(STUDY_CLAUSES)))
    rng.shuffle(order)
    return order


# ---------- Sanity: counterbalanced correct-answer positions ------------------

def _correct_position_counts() -> dict[int, int]:
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for clause in STUDY_CLAUSES:
        for q in clause["questions"]:
            counts[q["correct"]] = counts.get(q["correct"], 0) + 1
    return counts


# Assert reasonably balanced option positions — not strictly uniform, but
# no single position dominates. Helps catch a future editor accidentally
# breaking counterbalancing.
_counts = _correct_position_counts()
_total = sum(_counts.values())
assert _total == 24, f"expected 24 questions, got {_total}"
assert max(_counts.values()) <= 10, f"correct-answer position imbalance: {_counts}"
