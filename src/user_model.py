"""User profile model for personalization vs. privacy tradeoff."""

from dataclasses import dataclass, field
from typing import Literal

LiteracyLevel = Literal["no_legal_background", "some_familiarity", "law_professional"]

LITERACY_LABELS = {
    "no_legal_background": "No legal background",
    "some_familiarity": "Some familiarity with legal docs",
    "law_professional": "Law student / professional",
}

LITERACY_PROMPT_MODIFIERS = {
    "no_legal_background": (
        "The reader has NO legal background. Use very simple everyday language. "
        "Avoid all legal terminology. Use concrete analogies and examples. "
        "Explain as if talking to a high school student."
    ),
    "some_familiarity": (
        "The reader has some familiarity with legal documents but is not a lawyer. "
        "Use plain language but you can reference common legal concepts like "
        "'liability' or 'indemnification' if you briefly define them."
    ),
    "law_professional": (
        "The reader is a law student or legal professional. Be precise and use "
        "correct legal terminology. Focus on identifying non-standard or unusual "
        "provisions rather than explaining basic concepts. Skip the analogy section "
        "and instead note how this clause compares to standard contract language."
    ),
}


@dataclass
class UserProfile:
    literacy_level: LiteracyLevel = "no_legal_background"
    interests: list = field(default_factory=list)

    def get_prompt_modifier(self):
        """Return the prompt modifier string for the current literacy level."""
        return LITERACY_PROMPT_MODIFIERS[self.literacy_level]
