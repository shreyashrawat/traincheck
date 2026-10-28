"""Plain-language layer for normal users.

The audit speaks in rubric items; users speak in questions. This module
translates, with three rules:
- The top layer never shows internal information: no sentence IDs, no
  rule IDs, no model names, no decision rules. Those live only in the
  full report.
- "What's missing" covers disclosure gaps only: contradictory, partially
  stated, not stated. Whether the company trains is substance, and it
  goes in the bottom line and the actions, not the gaps.
- Every action must be supported by the audit. Nothing is invented:
  no guessed settings page, no named alternative app.
"""

PHRASES = {
    "T1": "whether it trains on your data",
    "T2": "whether you can opt out of training, and where",
    "T3": "what data it trains on",
    "T4": "how long it keeps data for training",
    "T5": "whether training rules differ for API or business users",
    "T6": "whether humans review training data, or opt-outs apply retroactively",
    "C1": "what data it collects",
    "C2": "whether it shares data with third parties",
    "C3": "what choices you have over your data",
    "C4": "whether you can access or delete your data",
    "C5": "how long it keeps your data",
    "C6": "how it protects your data",
    "C7": "how it tells you about policy changes",
    "C8": "Do Not Track",
    "C9": "international transfers",
    "C10": "children and contact details",
}


def plain_problem(item_id, result):
    """One plain sentence for a gap item, or None when it is clearly stated."""
    state = result["state"]
    phrase = PHRASES.get(item_id, item_id)
    if state == "contradictory":
        return f"Says two different things about {phrase}."
    if state == "partially stated":
        return f"Only vaguely covers {phrase}."
    if state == "not stated":
        return f"Doesn't say {phrase}."
    return None


def bottom_line(results):
    """One or two plain sentences: the substance a user acts on."""
    t1 = results.get("T1", {})
    t2 = results.get("T2", {})
    t1_value = t1.get("value")
    if t1.get("state") == "contradictory":
        first = "This policy says two different things about whether it trains on your data."
    elif t1.get("state") == "stated" and t1_value == "trains_by_default":
        first = "This policy trains on your data by default."
    elif t1.get("state") == "stated" and t1_value in ("trains",):
        first = "This policy trains on your data."
    elif t1.get("state") == "stated" and t1_value == "does_not_train":
        first = "This policy says it doesn't train on your data."
    elif t1.get("state") == "not stated":
        first = "This policy doesn't say whether it trains on your data."
    else:
        first = "This policy's training stance is unclear."
    second = ""
    if t2.get("state") == "stated" and isinstance(t2.get("value"), dict):
        choice = t2["value"].get("choice")
        location = t2["value"].get("control_location")
        if choice == "opt_out" and location:
            second = f"You can opt out: {location}"
        elif choice == "opt_out":
            second = "You can opt out, but the policy doesn't say where the control lives."
        elif choice == "opt_in":
            second = "Training is opt-in, so it's off unless you agree."
    elif t2.get("state") == "partially stated":
        second = "It mentions an opt-out, but doesn't tie it to training."
    return " ".join(s for s in (first, second) if s)


def next_actions(results, score):
    """What the user can do next. Every action is grounded in the audit.

    Order: contradiction warning, then the training control (or why none
    is needed), then deleting existing data, then limiting sharing, then
    comparing with another app.
    """
    actions = []
    t1 = results.get("T1", {})
    t2 = results.get("T2", {})
    c4 = results.get("C4", {})
    trains = t1.get("state") == "stated" and t1.get("value") in ("trains", "trains_by_default")
    if t1.get("state") == "contradictory":
        actions.append({
            "title": "Don't trust either clause yet",
            "detail": "The policy says one thing in one place and the opposite in another "
                      "about training. If this matters to you, ask the company which "
                      "version is current before relying on either.",
        })
    t2_value = t2.get("value") if isinstance(t2.get("value"), dict) else None
    if t2.get("state") == "stated" and t2_value and t2_value.get("choice") == "opt_out":
        location = t2_value.get("control_location")
        actions.append({
            "title": "Turn training off",
            "detail": location or "Look for a training or AI-data control in Settings or Privacy.",
        })
    elif t2.get("state") == "stated" and t2_value and t2_value.get("choice") == "opt_in":
        actions.append({
            "title": "Nothing to turn off",
            "detail": "Training is opt-in, so it's off unless you agree.",
        })
    elif t1.get("state") == "stated" and t1.get("value") == "does_not_train":
        actions.append({
            "title": "Nothing to turn off",
            "detail": "This policy says it doesn't train on your data.",
        })
    if trains and c4.get("state") == "stated":
        actions.append({
            "title": "Delete what it already has",
            "detail": "The policy says you can access or delete your data — use that to "
                      "remove past content from training.",
        })
    if trains and not (t2.get("state") == "stated" and t2_value
                       and t2_value.get("choice") in ("opt_out", "opt_in")):
        actions.append({
            "title": "Share less",
            "detail": "No training opt-out is stated. Avoid pasting sensitive personal "
                      "content, or use an account with minimal personal data.",
        })
    if t1.get("state") == "not stated":
        actions.append({
            "title": "Ask the company",
            "detail": "The policy doesn't say whether it trains on your data — worth asking "
                      "before you share sensitive content.",
        })
    if score["score"] < 8:
        actions.append({
            "title": "Compare with another app",
            "detail": "Paste a competing app's policy below to see which one scores higher — "
                      "a better-scoring alternative does the same job with a clearer policy.",
        })
    return actions
