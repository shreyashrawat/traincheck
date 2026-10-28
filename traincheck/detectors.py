"""High-precision detectors for the TrainCheck rubric (v1, deterministic only).

Core-10 detectors are provisional keyword baselines. T1-T6 are the fully
specified novel items: each returns a state, a value, and quote evidence.
A sentence matching a negative pattern is never also counted as positive
for the same item, so contradictions reflect genuinely conflicting clauses.
"""

import re


def _iter_sentences(doc):
    """Yield (sentence, section_title, sentence_id) for every sentence."""
    for sec in doc["sections"]:
        ids = sec.get("sentence_ids") or [None] * len(sec["sentences"])
        for sent, sid in zip(sec["sentences"], ids):
            yield sent, sec["title"], sid


def _find(doc, regexes):
    hits = []
    for sent, title, sid in _iter_sentences(doc):
        for rx in regexes:
            if rx.search(sent):
                hits.append({"quote": sent, "section": title, "sentence_id": sid})
                break
    return hits


def _rx(patterns):
    return [re.compile(p, re.I) for p in patterns]


T1_POS = _rx([
    r"\buse\b.{0,80}?\bto (train|improve|develop)\b",
    r"\btrain(?:ing)?\b.{0,40}?\bmodels?\b",
    r"\bmodels?\b.{0,40}?\btrained on\b",
])
T1_NEG = _rx([
    r"\b(do not|don't|never|will not|won't)\b.{0,60}?\buse\b.{0,60}?\bto train\b",
    r"\bnot used\b.{0,30}?\bfor training\b",
    r"\bdo not train\b",
    r"\bdoes not train\b",
])


def detect_t1(doc):
    pos, neg = [], []
    for sent, title, sid in _iter_sentences(doc):
        if any(rx.search(sent) for rx in T1_NEG):
            neg.append({"quote": sent, "section": title, "sentence_id": sid})
        elif any(rx.search(sent) for rx in T1_POS):
            pos.append({"quote": sent, "section": title, "sentence_id": sid})
    if pos and neg:
        return {"state": "contradictory", "value": "conflicting statements", "quotes": pos + neg}
    if pos:
        by_default = any("by default" in q["quote"].lower() for q in pos)
        return {"state": "stated", "value": "trains_by_default" if by_default else "trains", "quotes": pos}
    if neg:
        return {"state": "stated", "value": "does_not_train", "quotes": neg}
    return {"state": "not stated", "value": None, "quotes": []}


def _training_scoped(doc, regexes):
    """Hits from sentences that also mention training/models."""
    hits = []
    for sent, title, sid in _iter_sentences(doc):
        if not re.search(r"\btrain(?:ing)?\b|\bmodels?\b", sent, re.I):
            continue
        for rx in regexes:
            if rx.search(sent):
                hits.append({"quote": sent, "section": title, "sentence_id": sid})
                break
    return hits


def detect_t2(doc):
    opt_out_rx = _rx([
        r"\bopt[- ]out\b",
        r"\bdisable\b.{0,40}?\btraining\b",
        r"\bturn off\b.{0,40}?\btraining\b",
    ])
    opt_in_rx = _rx([
        r"\bopt[- ]in\b",
        r"\bonly if you\b.{0,40}?\b(agree|choose|opt)\b",
    ])
    scoped_out = _training_scoped(doc, opt_out_rx)
    scoped_in = _training_scoped(doc, opt_in_rx)
    # Control location only counts when tied to a training sentence, so a
    # marketing-settings sentence is not misreported as the training control.
    location = None
    for sent, _title, _sid in _iter_sentences(doc):
        if re.search(r"\btrain(?:ing)?\b", sent, re.I) and re.search(r"settings|privacy dashboard|https?://", sent, re.I):
            location = sent
            break
    if scoped_out:
        return {"state": "stated", "value": {"choice": "opt_out", "control_location": location}, "quotes": scoped_out}
    if scoped_in:
        return {"state": "stated", "value": {"choice": "opt_in", "control_location": location}, "quotes": scoped_in}
    generic = _find(doc, opt_out_rx) or _find(doc, opt_in_rx)
    if generic:
        return {"state": "partially stated", "value": "opt-out found but not tied to training", "quotes": generic[:2]}
    return {"state": "not stated", "value": None, "quotes": []}


INPUT_PATTERNS = {
    "prompts": r"\bprompts?\b",
    "uploads": r"\buploads?\b",
    "inputs": r"\binputs?\b",
    "outputs": r"\boutputs?\b",
    "feedback": r"\bfeedback\b",
    "account/profile data": r"\b(account|profile) (data|information)\b",
}


def detect_t3(doc, trains):
    training_sents = [(s, t, sid) for s, t, sid in _iter_sentences(doc)
                      if re.search(r"\btrain(?:ing)?\b", s, re.I)]
    found, quotes = [], []
    for name, pat in INPUT_PATTERNS.items():
        rx = re.compile(pat, re.I)
        for sent, title, sid in training_sents:
            if rx.search(sent):
                found.append(name)
                quotes.append({"quote": sent, "section": title, "sentence_id": sid})
                break
    if trains and found:
        return {"state": "stated", "value": found, "quotes": quotes}
    if trains:
        return {"state": "partially stated", "value": "training stated, input types not specified", "quotes": []}
    return {"state": "not stated", "value": None, "quotes": []}


def detect_t4(doc):
    dur = re.compile(r"(\d+\s*(?:days?|months?|years?))", re.I)
    for sent, title, sid in _iter_sentences(doc):
        if re.search(r"\btrain(?:ing)?\b", sent, re.I):
            m = dur.search(sent)
            if m:
                return {"state": "stated", "value": m.group(1), "quotes": [{"quote": sent, "section": title, "sentence_id": sid}]}
            if re.search(r"\bindefinitely\b", sent, re.I):
                return {"state": "stated", "value": "indefinite", "quotes": [{"quote": sent, "section": title, "sentence_id": sid}]}
            if re.search(r"\buntil you (delete|remove)\b", sent, re.I):
                return {"state": "stated", "value": "until deletion", "quotes": [{"quote": sent, "section": title, "sentence_id": sid}]}
    ret = _find(doc, _rx([r"\bretain\w*\b", r"\bretention\b"]))
    if ret:
        return {"state": "partially stated", "value": "retention mentioned, not tied to training", "quotes": ret[:1]}
    return {"state": "not stated", "value": None, "quotes": []}


def detect_t5(doc):
    scopes, quotes = {}, []
    for name, pat in [("api", r"\bapi\b"), ("enterprise", r"\benterprise\b"),
                      ("education", r"\beducation(?:al)?\b"), ("business", r"\bbusiness\b")]:
        # Scope terms only count in a training/applicability sentence, so a
        # passing mention (e.g. "education information" as a data category)
        # is not misread as a training carve-out.
        for sent, title, sid in _iter_sentences(doc):
            if re.search(pat, sent, re.I) and re.search(r"train|appl|exclud|separate terms|covered by|terms", sent, re.I):
                scopes[name] = True
                quotes.append({"quote": sent, "section": title, "sentence_id": sid})
                break
    carve = _find(doc, _rx([r"\bdoes not apply\b", r"\bdo not apply\b", r"\bexclud", r"\bseparate terms\b"]))
    if scopes:
        return {"state": "stated", "value": {"scopes": sorted(scopes), "carve_out": bool(carve)}, "quotes": quotes}
    return {"state": "not stated", "value": None, "quotes": []}


def detect_t6(doc):
    hr = _find(doc, _rx([r"human review", r"reviewed by humans?"]))
    retro = _find(doc, _rx([r"retroactiv", r"already (been )?used",
                            r"opt(?:ing)?-?out.{0,60}?does not (affect|apply to|remove|undo)"]))
    if hr or retro:
        return {"state": "stated",
                "value": {"human_review": bool(hr), "retroactivity_addressed": bool(retro)},
                "quotes": hr + retro}
    return {"state": "not stated", "value": None, "quotes": []}


CORE = {
    "C1": (r"\bwe collect\b", "First Party Collection/Use"),
    "C2": (r"\b(share|disclose)\b.{0,60}?\bthird[- ]part", "Third Party Sharing/Collection"),
    "C3": (r"\b(opt[- ]out|choice|settings|preferences)\b", "User Choice/Control"),
    "C4": (r"\b(access|correct|delete)\b.{0,40}?\byour (data|information)\b", "User Access, Edit, and Deletion"),
    "C5": (r"\bretain\w*\b|\bretention\b", "Data Retention"),
    "C6": (r"\b(security|encrypt\w*)\b", "Data Security"),
    "C7": (r"\b(update|change)\b.{0,40}?\bthis policy\b", "Policy Change"),
    "C8": (r"\bdo not track\b", "Do Not Track"),
    "C9": (r"\binternational\w*\b", "International and Specific Audiences"),
    "C10": (r"\b(children|minors|contact us)\b", "Other provisions"),
}

T_TITLES = {
    "T1": "Trains by default?",
    "T2": "Choice and where it lives",
    "T3": "What inputs count",
    "T4": "Retention for training",
    "T5": "Scope: consumer vs API vs enterprise",
    "T6": "Human review and retroactivity",
}


def detect_all(doc):
    """Run every rubric detector; returns an ordered dict of item results."""
    results = {}
    for cid, (pat, title) in CORE.items():
        hits = _find(doc, _rx([pat]))
        results[cid] = {"title": title, "state": "stated" if hits else "not stated",
                        "value": None, "quotes": hits[:2]}
    t1 = detect_t1(doc)
    t1["title"] = T_TITLES["T1"]
    results["T1"] = t1
    # Contradictory still counts as training-discussed: positive clauses exist,
    # so T3 can still evaluate which inputs those clauses name.
    trains = t1["value"] in ("trains", "trains_by_default", "conflicting statements")
    t2 = detect_t2(doc)
    t2["title"] = T_TITLES["T2"]
    results["T2"] = t2
    t3 = detect_t3(doc, trains)
    t3["title"] = T_TITLES["T3"]
    results["T3"] = t3
    t4 = detect_t4(doc)
    t4["title"] = T_TITLES["T4"]
    results["T4"] = t4
    t5 = detect_t5(doc)
    t5["title"] = T_TITLES["T5"]
    results["T5"] = t5
    t6 = detect_t6(doc)
    t6["title"] = T_TITLES["T6"]
    results["T6"] = t6
    # Provenance: every rule-produced quote is tagged with the item whose
    # detector produced it, so decision records can say which layer fired.
    for item_id, r in results.items():
        for q in r.get("quotes") or []:
            q.setdefault("source", f"rule:{item_id}")
    return results
