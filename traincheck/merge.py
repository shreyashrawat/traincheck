"""Merge per-document rubric results into one audit.

Rules:
- "contradictory" anywhere wins, then "stated", then "partially stated".
- T1 gets a cross-document check: training-positive clauses in one document
  and a trains-negative clause in another is a contradiction, even though
  each document alone looks consistent.
- Every quote keeps the document it came from, so the report can show
  which document each clause was found in.
"""

TRAIN_VALUES = ("trains", "trains_by_default")


def merge_results(per_doc_results):
    """per_doc_results: list of (doc_name, results_dict) in input order."""
    merged = {}
    item_ids = list(per_doc_results[0][1].keys())
    for item_id in item_ids:
        title = per_doc_results[0][1][item_id].get("title")
        states, quotes, values = [], [], []
        for doc_name, results in per_doc_results:
            r = results[item_id]
            states.append(r["state"])
            values.append(r.get("value"))
            for q in r.get("quotes") or []:
                qq = dict(q)
                qq["document"] = doc_name
                quotes.append(qq)
        if item_id == "T1" and any(v in TRAIN_VALUES for v in values) and "does_not_train" in values:
            state, value = "contradictory", "conflicting statements across documents"
            rule = "cross-document-contradiction"
        elif "contradictory" in states:
            state, value = "contradictory", "conflicting statements"
            rule = "contradictory-wins"
        elif "stated" in states:
            state = "stated"
            value = next((v for v in values if v is not None), None)
            rule = "stated-wins"
        elif "partially stated" in states:
            state = "partially stated"
            value = next((v for v in values if v is not None), None)
            rule = "partially-stated-wins"
        else:
            state, value = "not stated", None
            rule = "not-stated"
        merged[item_id] = {"title": title, "state": state, "value": value,
                           "quotes": quotes, "decision_rule": rule}
    return merged
