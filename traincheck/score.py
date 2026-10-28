"""Aggregate rubric results into a completeness summary."""


def summarize(results):
    counts = {"stated": 0, "partially stated": 0, "contradictory": 0, "not stated": 0}
    for r in results.values():
        state = r["state"]
        if state in counts:
            counts[state] += 1
    return counts
