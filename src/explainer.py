"""LLM-powered clause explanation generator using a local HuggingFace model."""

import torch
from transformers import pipeline

DEFAULT_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

DETAIL_PROMPTS = {
    "brief": (
        "Provide ONLY a single plain-language sentence explaining what this clause "
        "means in simple everyday language. Nothing else."
    ),
    "standard": (
        "Provide exactly three things:\n\n"
        "1. **Plain-Language Summary**: One sentence explaining what this clause means "
        "in simple everyday language.\n\n"
        "2. **Rights & Obligations**: A bulleted list of the specific rights you are "
        "giving up or obligations you are agreeing to by accepting this clause.\n\n"
        "3. **Real-World Analogy**: A short, relatable real-world analogy that helps "
        "a non-lawyer understand the practical impact of this clause.\n\n"
        "Format your response with clear headers for each section."
    ),
    "detailed": (
        "Provide exactly five things:\n\n"
        "1. **Plain-Language Summary**: One sentence explaining what this clause means "
        "in simple everyday language.\n\n"
        "2. **Rights & Obligations**: A bulleted list of the specific rights you are "
        "giving up or obligations you are agreeing to by accepting this clause.\n\n"
        "3. **Real-World Analogy**: A short, relatable real-world analogy that helps "
        "a non-lawyer understand the practical impact of this clause.\n\n"
        "4. **Key Legal Terms**: Define any legal jargon used in this clause in plain "
        "English.\n\n"
        "5. **Risk Assessment**: Rate the risk level (Low / Medium / High) and explain "
        "why — what's the worst-case scenario for the person agreeing to this?\n\n"
        "Format your response with clear headers for each section."
    ),
}


class ClauseExplainer:
    """Generates plain-language explanations for legal clauses."""

    def __init__(self, model_name=DEFAULT_MODEL):
        self.model_name = model_name
        self.pipe = None

    def load_model(self):
        """Load the model and tokenizer. Call once at startup."""
        self.pipe = pipeline(
            "text-generation",
            model=self.model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
        )

    def explain_clause(
        self,
        clause_text,
        clause_type=None,
        detail_level="standard",
        literacy_level=None,
        few_shot_examples=None,
    ):
        """Generate an explanation for a legal clause.

        Args:
            clause_text: The legal clause text.
            clause_type: Optional CUAD clause type for context.
            detail_level: "brief", "standard", or "detailed".
            literacy_level: Optional literacy modifier string from UserProfile.
            few_shot_examples: Optional list of example clause texts from CUAD
                               for the same clause type (data-driven context).

        Returns:
            dict with keys: summary, rights, analogy, terms, risk, raw, confidence
        """
        if self.pipe is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        clause_context = f" (clause type: {clause_type})" if clause_type else ""
        detail_instruction = DETAIL_PROMPTS.get(detail_level, DETAIL_PROMPTS["standard"])
        literacy_instruction = f"\n\nIMPORTANT AUDIENCE NOTE: {literacy_level}" if literacy_level else ""

        # Build few-shot context from CUAD data
        cuad_context = ""
        if few_shot_examples and clause_type:
            examples_text = "\n---\n".join(ex[:300] for ex in few_shot_examples[:2])
            cuad_context = (
                f"\n\nFor reference, here are examples of \"{clause_type}\" clauses "
                f"from real contracts in the CUAD legal dataset:\n{examples_text}\n"
                f"Use these examples to better understand the pattern and intent "
                f"of this type of clause."
            )

        was_truncated = len(clause_text) > 1500
        if was_truncated:
            clause_text = clause_text[:1500]

        prompt = f"""<|system|>
You are a legal-language simplifier that helps ordinary people understand contracts.{literacy_instruction}</s>
<|user|>
A user is reading a contract and needs help understanding the following clause{clause_context}:

"{clause_text}"
{cuad_context}

{detail_instruction}</s>
<|assistant|>
"""

        result = self.pipe(
            prompt,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            return_full_text=False,
        )

        parsed = self._parse_response(result[0]["generated_text"], detail_level)
        parsed["was_truncated"] = was_truncated
        parsed["confidence"] = self._compute_confidence(parsed, was_truncated)
        return parsed

    def _compute_confidence(self, parsed, was_truncated):
        """Compute a confidence level for the explanation.

        Returns "high", "medium", or "low" with a reason string.
        """
        issues = []
        if was_truncated:
            issues.append("clause was truncated (over 1500 chars)")

        # Check if key sections were successfully parsed
        if not parsed.get("summary"):
            issues.append("could not extract a clear summary")
        if not parsed.get("rights"):
            issues.append("could not extract rights/obligations")

        if len(issues) >= 2:
            return {"level": "low", "reason": "Issues: " + "; ".join(issues)}
        elif len(issues) == 1:
            return {"level": "medium", "reason": issues[0].capitalize()}
        else:
            return {"level": "high", "reason": "All sections successfully generated"}

    def _parse_response(self, raw_text, detail_level="standard"):
        """Parse the LLM output into structured sections."""
        sections = {
            "summary": "",
            "rights": "",
            "analogy": "",
            "terms": "",
            "risk": "",
            "raw": raw_text.strip(),
        }

        text = raw_text.strip()
        lower = text.lower()

        if detail_level == "brief":
            sections["summary"] = text
            return sections

        # Section markers to search for
        marker_map = {
            "summary": ["plain-language summary", "plain language summary", "1."],
            "rights": ["rights & obligations", "rights and obligations", "2."],
            "analogy": ["real-world analogy", "real world analogy", "3."],
            "terms": ["key legal terms", "legal terms", "4."],
            "risk": ["risk assessment", "risk level", "5."],
        }

        def find_section(markers):
            for marker in markers:
                idx = lower.find(marker)
                if idx != -1:
                    return idx
            return -1

        found = []
        for key, markers in marker_map.items():
            idx = find_section(markers)
            if idx >= 0:
                found.append((idx, key))

        found.sort(key=lambda x: x[0])

        for i, (idx, key) in enumerate(found):
            content_start = text.find("\n", idx)
            if content_start < 0:
                content_start = idx
            if i + 1 < len(found):
                content_end = found[i + 1][0]
            else:
                content_end = len(text)
            sections[key] = text[content_start:content_end].strip()

        return sections
