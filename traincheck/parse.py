"""Document parsing for TrainCheck: sections, sentences, effective date."""

import re

_HEADING = re.compile(r"^#{1,3}\s+(.*)")
_DATE = [
    re.compile(r"(?:effective|last updated|updated)\s*(?:as of\s*)?([A-Z][a-z]+ \d{1,2}, \d{4})", re.I),
    re.compile(r"(?:effective|last updated|updated)\s*(?:as of\s*)?(\d{4}-\d{2}-\d{2})", re.I),
]


def _sentences(text):
    flat = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", flat)
    return [p.strip() for p in parts if p.strip()]


def parse_document(text):
    """Split a policy into sections with sentences, and find its date."""
    sections, title, buf = [], "Introduction", []
    for line in text.splitlines():
        m = _HEADING.match(line.strip())
        if m:
            if buf:
                sections.append({"title": title, "text": "\n".join(buf).strip()})
            title, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if buf:
        sections.append({"title": title, "text": "\n".join(buf).strip()})
    sections = [s for s in sections if s["text"]]
    for s in sections:
        s["sentences"] = _sentences(s["text"])
    date = None
    for pat in _DATE:
        m = pat.search(text)
        if m:
            date = m.group(1)
            break
    return {"effective_date": date, "sections": sections}
