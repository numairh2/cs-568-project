"""User study configuration: conditions, questions, and Likert scales."""

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

# --- Study Clauses (from the sample contract) ---
STUDY_CLAUSES = [
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
                    "The hackers are liable",
                    "The company is NOT liable under this clause",
                    "Both you and the company share liability",
                ],
                "correct": 2,
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
                    "Browsing history, location, device info, uploaded content, and more",
                    "No personal data is collected",
                ],
                "correct": 2,
            },
            {
                "question": "Will you be notified before the Privacy Policy changes?",
                "options": [
                    "Yes, they must give 30 days notice",
                    "Yes, they will email you",
                    "No, the policy can be updated without prior notice",
                    "Changes require your explicit consent",
                ],
                "correct": 2,
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
                    "You are responsible for paying, including attorney's fees",
                    "Nobody pays — the clause prevents lawsuits",
                ],
                "correct": 2,
            },
            {
                "question": "This indemnification clause is triggered by which of the following?",
                "options": [
                    "Only if you intentionally break the rules",
                    "Only if you violate copyright",
                    "Your use of the service, violating the terms, or violating third-party rights",
                    "Only if the company decides to enforce it",
                ],
                "correct": 2,
            },
        ],
    },
]


# --- Likert Scales ---
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


def assign_condition():
    """Randomly assign a study condition."""
    return random.choice(CONDITIONS)
