"""Decision records: the auditable trail behind every item state.

A decision record answers "which lines caused this decision, and which
layer produced each line?" for one rubric item. The model layers (ML, LLM)
only ever *propose* evidence; the state itself is always set by the
deterministic aggregation rules in merge.py (or, for a single document,
by the detector that fired). Records therefore stay reproducible: same
inputs + same pipeline version = same record.

Evidence entries carry:
- quote, section, document, sentence_id: the exact line
- source: "rule:<item>" | "ml:<model>" | "llm:<model>"
- confidence: only for ML-proposed evidence
"""

import hashlib

PIPELINE_VERSION = "0.2.0"


def _layer(source):
    if not source:
        return "unknown"
    return source.split(":", 1)[0]


def build_decision_records(merged):
    """merged: output of merge_results (or a single doc's detect_all).

    Returns {item_id: record}. For single-doc results the decision_rule
    is "detector" when evidence exists, else "not-stated".
    """
    records = {}
    for item_id, r in merged.items():
        evidence = []
        for q in r.get("quotes") or []:
            ev = {
                "quote": q["quote"],
                "section": q.get("section"),
                "document": q.get("document"),
                "sentence_id": q.get("sentence_id"),
                "source": q.get("source", f"rule:{item_id}"),
            }
            if q.get("confidence") is not None:
                ev["confidence"] = q["confidence"]
            evidence.append(ev)
        rule = r.get("decision_rule")
        if rule is None:
            rule = "detector" if evidence else "not-stated"
        records[item_id] = {
            "item_id": item_id,
            "title": r.get("title"),
            "state": r["state"],
            "value": r.get("value"),
            "decision_rule": rule,
            "gapfilled": bool(r.get("gapfilled")),
            "evidence": evidence,
            "layers": sorted({_layer(e["source"]) for e in evidence}),
        }
    return records


def audit_manifest(doc_texts, models=None):
    """Reproducibility header for an audit run.

    input_sha256 covers the exact input texts, so re-running the same
    texts through the same pipeline version must reproduce the audit.
    """
    joined = "\n\n".join(doc_texts)
    return {
        "pipeline_version": PIPELINE_VERSION,
        "input_sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
        "document_count": len(doc_texts),
        "models": models or {},
    }
