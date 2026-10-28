"""LLM extraction layer for TrainCheck (model-agnostic).

Design rules from the spec:
- The LLM has exactly two jobs: quote-or-abstain extraction and
  plain-language explanation. It never decides an item's state on its own.
- Every returned quote is mechanically verified against the source by code:
  a quote that is not an exact substring (modulo whitespace) is dropped.
- No verified quote means "not stated", never an invented one.
- The model client is pluggable: pass any callable(prompt) -> str.
  No API key is needed to use or test this module; wiring a live model
  client is a separate, later step.
"""

import json
import re


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def build_extraction_prompt(doc_text, items):
    """items: list of (item_id, question). Returns the prompt string."""
    lines = [
        "You are auditing a privacy policy. For each item below, return either:",
        "  - a VERBATIM quote from the policy that answers it, or",
        '  - "NOT STATED" if the policy does not address it.',
        "Rules:",
        "- Quotes must be copied character-for-character from the policy text.",
        "- Never paraphrase, summarize, or invent a quote.",
        "- If two clauses conflict, return both quotes.",
        '- Return ONLY a JSON object mapping item id to {"quote": ...} or {"quote": null}.',
        "",
        "POLICY:",
        doc_text,
        "",
        "ITEMS:",
    ]
    for item_id, question in items:
        lines.append(f"- {item_id}: {question}")
    return "\n".join(lines)


def parse_extraction_response(text):
    """Parse the model's JSON; returns dict item_id -> quote-or-None.

    Raises ValueError on unparseable output (the caller treats that as
    abstain-all, so a garbled response can never fabricate evidence).
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object in response")
    data = json.loads(text[start:end + 1])
    out = {}
    for item_id, entry in data.items():
        if isinstance(entry, dict):
            out[item_id] = entry.get("quote")
        elif isinstance(entry, str):
            out[item_id] = entry
        else:
            out[item_id] = None
    return out


def verify_quotes(doc_text, quotes):
    """Mechanical verbatim check. Returns (verified, dropped).

    verified: item_id -> quote (exact substring, modulo whitespace).
    dropped: item_id -> reason string. Abstentions are neither.
    """
    norm_doc = normalize(doc_text)
    verified, dropped = {}, {}
    for item_id, quote in quotes.items():
        if quote is None or (isinstance(quote, str) and quote.strip().upper() == "NOT STATED"):
            continue  # abstention, not an error
        if not isinstance(quote, str) or not quote.strip():
            dropped[item_id] = "empty quote"
            continue
        if normalize(quote) in norm_doc:
            verified[item_id] = quote.strip()
        else:
            dropped[item_id] = "quote not found verbatim in source"
    return verified, dropped


def extract_with_client(client, doc_text, items):
    """Run one extraction pass. client: callable(prompt) -> str.

    Returns {"results": {item_id: {"state", "quote"}}, "dropped": {...}}.
    State is 'stated' only with a verified quote, else 'not stated'.
    """
    prompt = build_extraction_prompt(doc_text, items)
    try:
        parsed = parse_extraction_response(client(prompt))
    except ValueError:
        parsed = {}
    verified, dropped = verify_quotes(doc_text, parsed)
    results = {}
    for item_id, _question in items:
        if item_id in verified:
            results[item_id] = {"state": "stated", "quote": verified[item_id]}
        else:
            results[item_id] = {"state": "not stated", "quote": None}
    return {"results": results, "dropped": dropped}


def explain_quote(client, quote, question):
    """Plain-language explanation of one verified quote. The explanation is
    never evidence itself; it is always displayed attached to the quote."""
    prompt = (
        "Explain in one plain sentence what this privacy-policy clause means "
        f"for the question: {question}\nClause: {quote}\n"
        "Do not add facts beyond the clause."
    )
    return client(prompt).strip()
