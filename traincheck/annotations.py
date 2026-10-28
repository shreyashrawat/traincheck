"""Annotation tooling for TrainCheck: sentence-level gold data.

One annotation file = one policy, labeled by one annotator:
{
  "policy_id": "anthropic-2026-09",
  "source_url": "https://www.anthropic.com/legal/privacy",
  "annotator": "shrey",
  "documents": [
    {"name": "Policy",
     "text": "<full policy text>",
     "sentences": [
       {"id": "S1", "section": "Introduction", "text": "...",
        "labels": [{"item": "T1", "stance": "states"}]},
       ...
     ]}
  ],
  "items": {
    "T1": {"state": "stated",
           "evidence": [{"document": "Policy", "sentence_id": "S4"}]},
    ...
  }
}

Rules the validator enforces:
- Every document's sentence list must match parse_document() output
  exactly (normalized whitespace), in order, with IDs S1..Sn.
- Labels reference real rubric items; stance in {states, denies, mentions}.
- Item evidence references must point at sentences that exist.
- Item states use the rubric states.

Two layers of gold come out of this:
- sentence_dataset(): rows for ML training (sentence -> items evidenced).
- item_gold(): per-policy item states for evaluation (evaluate.py).
Splitting train/dev/test must be BY POLICY, never by sentence, or
sentences from one policy leak across the split and flatter results.
"""

import argparse
import json
from pathlib import Path

from .evaluate import annotator_agreement
from .parse import parse_document

ITEM_IDS = [f"C{i}" for i in range(1, 11)] + [f"T{i}" for i in range(1, 7)]
STATES = ("stated", "partially stated", "contradictory", "not stated")
STANCES = ("states", "denies", "mentions")


def _norm(text):
    import re
    return re.sub(r"\s+", " ", text).strip()


def load_annotation(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_annotation(ann):
    """Return a list of error strings (empty = valid)."""
    errors = []
    for key in ("policy_id", "annotator", "documents", "items"):
        if key not in ann:
            errors.append(f"missing key: {key}")
    if errors:
        return errors
    known = {}  # (document_name, sentence_id) -> True
    for doc in ann["documents"]:
        if "name" not in doc or "text" not in doc or "sentences" not in doc:
            errors.append(f"document missing name/text/sentences: {doc.get('name')}")
            continue
        parsed = parse_document(doc["text"])
        flat = [(s["title"], t, sid) for s in parsed["sections"]
                for t, sid in zip(s["sentences"], s["sentence_ids"])]
        listed = [(s.get("section"), s.get("text"), s.get("id"))
                  for s in doc["sentences"]]
        if len(flat) != len(listed):
            errors.append(f"{doc['name']}: {len(listed)} annotated sentences, "
                          f"parser found {len(flat)}")
        for (pt, ptxt, pid), (lt, ltxt, lid) in zip(flat, listed):
            if pid != lid:
                errors.append(f"{doc['name']}: sentence id {lid} != parser {pid}")
            if pt != lt:
                errors.append(f"{doc['name']} {lid}: section {lt!r} != parser {pt!r}")
            if _norm(ptxt) != _norm(ltxt or ""):
                errors.append(f"{doc['name']} {lid}: text does not match parsed sentence")
        for s in doc["sentences"]:
            known[(doc["name"], s.get("id"))] = True
            for lab in s.get("labels") or []:
                if lab.get("item") not in ITEM_IDS:
                    errors.append(f"{doc['name']} {s.get('id')}: unknown item {lab.get('item')}")
                if lab.get("stance") not in STANCES:
                    errors.append(f"{doc['name']} {s.get('id')}: bad stance {lab.get('stance')}")
    for item_id, gold in (ann["items"] or {}).items():
        if item_id not in ITEM_IDS:
            errors.append(f"items: unknown item {item_id}")
            continue
        if gold.get("state") not in STATES:
            errors.append(f"items {item_id}: bad state {gold.get('state')}")
        for ev in gold.get("evidence") or []:
            if (ev.get("document"), ev.get("sentence_id")) not in known:
                errors.append(f"items {item_id}: evidence {ev} not found in sentences")
    return errors


def sentence_dataset(annotations):
    """Flatten annotations into ML training rows."""
    rows = []
    for ann in annotations:
        for doc in ann["documents"]:
            for s in doc["sentences"]:
                labels = s.get("labels") or []
                rows.append({
                    "policy_id": ann["policy_id"],
                    "annotator": ann["annotator"],
                    "document": doc["name"],
                    "sentence_id": s["id"],
                    "section": s["section"],
                    "text": s["text"],
                    "items": sorted({lab["item"] for lab in labels}),
                    "labels": labels,
                })
    return rows


def item_gold(annotations):
    """{policy_id: {item_id: state}} from the items maps."""
    gold = {}
    for ann in annotations:
        gold[ann["policy_id"]] = {iid: g["state"]
                                  for iid, g in (ann["items"] or {}).items()}
    return gold


def annotator_pair_kappa(ann_a, ann_b):
    """Kappa between two annotators' item states for the same policy."""
    a = {(ann_a["policy_id"], iid): g["state"]
         for iid, g in (ann_a["items"] or {}).items()}
    b = {(ann_b["policy_id"], iid): g["state"]
         for iid, g in (ann_b["items"] or {}).items()}
    return annotator_agreement(a, b)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="traincheck-annotations")
    ap.add_argument("--dir", required=True, help="directory of *.json annotation files")
    ap.add_argument("--dataset-out", help="optional path to write sentence dataset JSONL")
    args = ap.parse_args(argv)
    anns, all_errors = [], {}
    for path in sorted(Path(args.dir).glob("*.json")):
        ann = load_annotation(path)
        anns.append(ann)
        errs = validate_annotation(ann)
        if errs:
            all_errors[path.name] = errs
    if all_errors:
        for name, errs in all_errors.items():
            print(f"{name}: INVALID")
            for e in errs:
                print(f"  - {e}")
        return 1
    rows = sentence_dataset(anns)
    print(f"{len(anns)} annotation files valid, {len(rows)} sentence rows")
    by_policy = {}
    for ann in anns:
        by_policy.setdefault(ann["policy_id"], []).append(ann)
    for policy, pair in by_policy.items():
        if len(pair) >= 2:
            print(f"{policy}: kappa {annotator_pair_kappa(pair[0], pair[1])}")
    if args.dataset_out:
        with open(args.dataset_out, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        print(f"dataset written to {args.dataset_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
