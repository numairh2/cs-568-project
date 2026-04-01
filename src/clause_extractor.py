"""Extract and identify clause boundaries from raw contract text.

For user-uploaded contracts (not in CUAD), we use simple heuristics
to segment text into clause-like chunks that can be sent to the LLM.
"""

import re


def segment_contract(text):
    """Split raw contract text into clause-like segments.

    Uses numbered sections, headings, and paragraph breaks as boundaries.
    Returns a list of dicts with 'text' and 'heading' keys.
    """
    # Pattern: numbered sections like "1.", "1.1", "Section 1", or ALL-CAPS headings
    section_pattern = re.compile(
        r"(?:^|\n)"
        r"("
        r"(?:Section\s+)?\d+(?:\.\d+)*\.?\s+"  # "1. " or "Section 1.2 "
        r"|[A-Z][A-Z\s]{4,}(?:\n|\.)"           # ALL CAPS HEADING
        r")",
        re.MULTILINE,
    )

    splits = list(section_pattern.finditer(text))

    if not splits:
        # Fallback: split on double newlines (paragraphs)
        paragraphs = re.split(r"\n\s*\n", text)
        return [
            {"heading": f"Paragraph {i+1}", "text": p.strip()}
            for i, p in enumerate(paragraphs)
            if p.strip()
        ]

    segments = []
    for i, match in enumerate(splits):
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        chunk = text[start:end].strip()
        if not chunk:
            continue

        # Extract heading from the first line
        first_line_end = chunk.find("\n")
        if first_line_end > 0:
            heading = chunk[:first_line_end].strip().rstrip(".")
            body = chunk
        else:
            heading = chunk[:80].strip()
            body = chunk

        segments.append({"heading": heading, "text": body})

    return segments
