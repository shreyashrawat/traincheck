"""LLM gap-fill layer: the model fills gaps, rules still decide.

Gap-fill runs ONLY on items the deterministic detectors left as
"not stated" or "partially stated", and only per document, before the
merge step — so cross-document contradiction logic still applies to
gap-filled results. A verified quote upgrades the item to "stated";
anything unverified (paraphrase, hallucination, garbled output) is
dropped and reported, never used as evidence.

Evidence produced here carries source "llm:<model>" plus the section
and sentence_id located by matching the verified quote back into the
parsed document, so decision records stay line-anchored.
"""

from .llm import extract_with_client, normalize

PROMPT_VERSION = "llm.build_extraction_prompt/v1"

QUESTIONS = {
    "T1": "Does the policy say user data is used to train AI models, by default or otherwise?",
    "T2": "Does the policy offer a choice (opt-out or opt-in) about training, and where is the control?",
    "T3": "What kinds of user data (prompts, uploads, outputs, feedback, etc.) does the policy say are used for training?",
    "T4": "How long is data retained for training purposes?",
    "T5": "Does the policy say training rules differ for API, enterprise, education, or business users?",
    "T6": "Does the policy address human review of training data, or whether an opt-out applies retroactively?",
    "C1": "What personal data does the policy say is collected, and how is it used?",
    "C2": "Does the policy say data is shared with or collected by third parties?",
    "C3": "What choices or controls does the policy offer the user over their data?",
    "C4": "Can the user access, correct, or delete their data under the policy?",
    "C5": "How long does the policy say data is retained?",
    "C6": "What security measures does the policy describe for stored data?",
    "C7": "How does the policy say users are notified of policy changes?",
    "C8": "Does the policy address Do Not Track signals?",
    "C9": "Does the policy address international transfers or specific audiences?",
    "C10": "What other provisions (children, contact information) does the policy state?",
}


def locate_quote(doc, quote):
    """Find (section_title, sentence_id) for a verified quote.

    Matches a whole sentence first, then a quote contained in a sentence.
    Returns (None, None) when the quote cannot be located (should not
    happen for verified quotes, but the caller must not crash on it).
    """
    norm_q = normalize(quote)
    for sec in doc["sections"]:
        ids = sec.get("sentence_ids") or [None] * len(sec["sentences"])
        for sent, sid in zip(sec["sentences"], ids):
            norm_s = normalize(sent)
            if norm_s == norm_q or norm_q in norm_s:
                return sec["title"], sid
    return None, None


def gapfill_doc_results(results, doc, doc_text, client, model_name):
    """Gap-fill one document's detector results.

    Returns (new_results, diagnostics). new_results is a copy; the input
    is untouched. diagnostics records model, prompt version, which items
    were upgraded, and which quotes were dropped and why.
    """
    unresolved = [(iid, QUESTIONS[iid]) for iid, r in results.items()
                  if r["state"] in ("not stated", "partially stated")
                  and iid in QUESTIONS]
    diagnostics = {"model": model_name, "temperature": 0,
                   "prompt_version": PROMPT_VERSION,
                   "attempted": [iid for iid, _ in unresolved],
                   "upgraded": [], "dropped": {}}
    if not unresolved or client is None:
        return results, diagnostics
    out = extract_with_client(client, doc_text, unresolved)
    diagnostics["dropped"] = out["dropped"]
    new = {}
    for iid, r in results.items():
        new[iid] = dict(r)
        new[iid]["quotes"] = list(r.get("quotes") or [])
    for iid, res in out["results"].items():
        if res["state"] != "stated":
            continue
        section, sid = locate_quote(doc, res["quote"])
        new[iid]["state"] = "stated"
        new[iid]["value"] = None
        new[iid]["quotes"] = [{"quote": res["quote"], "section": section,
                              "sentence_id": sid, "source": f"llm:{model_name}"}]
        new[iid]["gapfilled"] = True
        diagnostics["upgraded"].append(iid)
    return new, diagnostics
