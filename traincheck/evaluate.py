"""Evaluation harness for TrainCheck (stdlib only).

Inputs are plain dicts so the harness works before any live data exists:
- gold: {policy_name: {item_id: state}}
- pred: {policy_name: {item_id: state}}
States are the rubric states: stated / partially stated / contradictory /
not stated. A gold item missing from pred counts as a mismatch.

Also provides Cohen's kappa for the double-annotation protocol: two
annotators label the same (policy, item) pairs and their agreement is
reported alongside accuracy, so the dataset's reliability is measured,
not just the tool's.
"""

from collections import Counter


def per_item_accuracy(gold, pred):
    """Returns {item_id: accuracy} plus 'overall' (mean over items)."""
    totals, correct = Counter(), Counter()
    for policy, items in gold.items():
        for item_id, gold_state in items.items():
            pred_state = pred.get(policy, {}).get(item_id)
            totals[item_id] += 1
            if pred_state == gold_state:
                correct[item_id] += 1
    acc = {item_id: (correct[item_id] / n if n else 0.0) for item_id, n in totals.items()}
    acc["overall"] = sum(acc.values()) / len(acc) if acc else 0.0
    return acc


def confusion(gold, pred):
    """Returns {item_id: {(gold_state, pred_state): count}}."""
    conf = {}
    for policy, items in gold.items():
        for item_id, gold_state in items.items():
            pred_state = pred.get(policy, {}).get(item_id, "missing")
            conf.setdefault(item_id, Counter())[(gold_state, pred_state)] += 1
    return {item_id: dict(c) for item_id, c in conf.items()}


def cohen_kappa(a, b):
    """Cohen's kappa for two equal-length label lists."""
    if len(a) != len(b) or not a:
        raise ValueError("kappa needs two non-empty, equal-length label lists")
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def annotator_agreement(ann_a, ann_b):
    """ann_a / ann_b: {(policy, item_id): state}. Returns kappa + agreement."""
    keys = sorted(set(ann_a) & set(ann_b))
    if not keys:
        raise ValueError("no overlapping annotations to compare")
    a = [ann_a[k] for k in keys]
    b = [ann_b[k] for k in keys]
    return {
        "pairs": len(keys),
        "agreement": sum(1 for x, y in zip(a, b) if x == y) / len(keys),
        "kappa": cohen_kappa(a, b),
    }


def summarize(gold, pred, ann_a=None, ann_b=None):
    """Full evaluation report dict (JSON-serializable)."""
    report = {
        "accuracy": per_item_accuracy(gold, pred),
        "confusion": confusion(gold, pred),
    }
    if ann_a is not None and ann_b is not None:
        report["annotator_agreement"] = annotator_agreement(ann_a, ann_b)
    return report
