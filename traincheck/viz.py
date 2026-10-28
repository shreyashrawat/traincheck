"""Visual layer for the TrainCheck app: charts as HTML, no new dependencies.

Robinhood-style rule: the eye should get the answer before any text is
read. So the audit becomes, in order: a giant number, a donut, two bars,
then cards — and text only where it adds something the picture cannot.

Colors are semantic and consistent everywhere:
- stated: green, partially stated: amber, contradictory: red,
  not stated: gray.
Color is never the only signal: every chart carries a text legend with
counts, so the picture is readable without color too.
"""

COLORS = {
    "stated": "#22c55e",
    "partially stated": "#f59e0b",
    "contradictory": "#ef4444",
    "not stated": "#9ca3af",
}

LABELS = {
    "stated": "clearly stated",
    "partially stated": "vague",
    "contradictory": "contradictory",
    "not stated": "not stated",
}


def donut_html(counts, score, label, size=190):
    """Donut chart (conic-gradient) with the score in the middle.

    counts: {state: n} over the 16 items. Returns an HTML string plus a
    text legend. Pure CSS — no matplotlib, no plotly, nothing to install.
    """
    total = sum(counts.values()) or 1
    stops, acc = [], 0.0
    for state in ("stated", "partially stated", "contradictory", "not stated"):
        n = counts.get(state, 0)
        if not n:
            continue
        frac = n / total * 100
        stops.append(f"{COLORS[state]} {acc:.1f}% {acc + frac:.1f}%")
        acc += frac
    gradient = ", ".join(stops) if stops else f"{COLORS['not stated']} 0% 100%"
    hole = int(size * 0.62)
    legend = " · ".join(
        f"<span style='color:{COLORS[s]}'>●</span> {counts.get(s, 0)} {LABELS[s]}"
        for s in ("stated", "partially stated", "contradictory", "not stated")
        if counts.get(s, 0)
    )
    return f"""
<div style="display:flex;flex-direction:column;align-items:center;gap:10px">
  <div style="position:relative;width:{size}px;height:{size}px">
    <div style="width:100%;height:100%;border-radius:50%;
                background:conic-gradient({gradient})"></div>
    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                width:{hole}px;height:{hole}px;border-radius:50%;background:white;
                display:flex;flex-direction:column;align-items:center;justify-content:center">
      <div style="font-size:44px;font-weight:800;line-height:1">{score}</div>
      <div style="font-size:14px;color:#6b7280">/ 10 · {label}</div>
    </div>
  </div>
  <div style="font-size:13px;text-align:center">{legend}</div>
</div>
"""


def bar_html(frac, color="#22c55e", height=10):
    """Thin progress bar. frac is 0.0-1.0, clamped."""
    pct = max(0.0, min(1.0, frac)) * 100
    return f"""
<div style="background:#e5e7eb;border-radius:999px;height:{height}px;width:100%">
  <div style="background:{color};border-radius:999px;height:{height}px;width:{pct:.0f}%"></div>
</div>
"""


def hero_css():
    """Page CSS: big hero number, breathing room, no Streamlit clutter."""
    return """
<style>
  .tc-hero-num { font-size: 76px; font-weight: 800; line-height: 1; letter-spacing: -2px; }
  .tc-hero-sub { font-size: 20px; color: #374151; line-height: 1.35; }
  .tc-section { margin-top: 8px; }
  div[data-testid="stExpander"] { border: 1px solid #e5e7eb; border-radius: 12px; }
</style>
"""
