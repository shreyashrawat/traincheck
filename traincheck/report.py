"""Render a TrainCheck audit as Markdown."""

from .score import summarize


def render_markdown(doc, results):
    s = summarize(results)
    lines = ["# TrainCheck audit", ""]
    lines.append(f"Effective date: {doc['effective_date'] or 'not found'}")
    lines.append(
        f"Completeness: {s['stated']}/16 items stated, "
        f"{s['contradictory']} contradictory, "
        f"{s['partially stated']} partially stated, "
        f"{s['not stated']} not stated"
    )
    lines.append("")
    lines.append("Headline: completeness of disclosure, not safety. "
                 "Not legal advice — verify against the current policy.")
    lines.append("")
    lines.append("| Item | State | Value | Evidence |")
    lines.append("|---|---|---|---|")
    for item_id, r in results.items():
        quotes = r.get("quotes") or []
        ev = ""
        if quotes:
            q = quotes[0]
            ev = f"\"{q['quote']}\" ({q['section']})"
        value = r.get("value")
        if isinstance(value, (list, dict)):
            value = str(value)
        lines.append(f"| {item_id} — {r.get('title', '')} | {r['state']} | {value or ''} | {ev} |")
    return "\n".join(lines)
