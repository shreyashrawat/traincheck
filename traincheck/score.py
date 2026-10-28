"""Aggregate rubric results into a completeness summary and a user-facing score."""

T_WEIGHT = 2  # AI-training questions count double: that is what this tool is about.
C_WEIGHT = 1


def summarize(results):
    counts = {"stated": 0, "partially stated": 0, "contradictory": 0, "not stated": 0}
    for r in results.values():
        state = r["state"]
        if state in counts:
            counts[state] += 1
    return counts


def transparency_score(results):
    """Headline score out of 10 for a normal user.

    stated = full points, partially stated = half, contradictory and
    not stated = zero. Training questions (T1-T6) are double-weighted.
    The score measures how CLEARLY the policy discloses, not how
    safely the company behaves: a policy can score high while still
    training on everything, as long as it says so openly. The
    bottom-line sentence (plain.py) carries the substance.
    """
    points = max_points = 0.0
    t_points = t_max = 0.0
    c_points = c_max = 0.0
    t_clear = c_clear = 0
    for item_id, r in results.items():
        weight = T_WEIGHT if item_id.startswith("T") else C_WEIGHT
        frac = {"stated": 1.0, "partially stated": 0.5}.get(r["state"], 0.0)
        points += frac * weight
        max_points += weight
        if item_id.startswith("T"):
            t_points += frac * weight
            t_max += weight
            t_clear += 1 if r["state"] == "stated" else 0
        else:
            c_points += frac * weight
            c_max += weight
            c_clear += 1 if r["state"] == "stated" else 0
    score = round(points / max_points * 10, 1) if max_points else 0.0
    label = "Clear" if score >= 8 else "Patchy" if score >= 5 else "Vague"
    return {
        "score": score,
        "label": label,
        "training": {"points": t_points, "max": t_max, "clear": t_clear, "total": 6},
        "basics": {"points": c_points, "max": c_max, "clear": c_clear, "total": 10},
    }


def compare_scores(a_results, b_results):
    """Compare two audits. Returns scores and which side is higher."""
    a = transparency_score(a_results)["score"]
    b = transparency_score(b_results)["score"]
    better = "A" if a > b else "B" if b > a else "tie"
    return {"a": a, "b": b, "better": better, "delta": round(abs(a - b), 1)}
