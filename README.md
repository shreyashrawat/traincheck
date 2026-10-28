# TrainCheck (local scaffold, v0.1)

An evidence-anchored audit of what AI products' privacy policies actually say
about training on your data. Paste a policy URL or text, get a per-item audit
against a 16-item rubric. Every finding carries a verbatim quoted clause, a
section, and a policy date/version. The headline is **completeness of
disclosure, never an "unsafe company" verdict**. Not legal advice.

This extends the 2021 POCASUM paper (completeness vs. an ideal policy) into
the AI-training question: trains by default? opt-out and where it lives? what
inputs count? retention for training? consumer vs API/enterprise scope? human
review and retroactivity?

## Quickstart (stdlib only, no dependencies)

```bash
cd ~/workspace/traincheck
python3 -m traincheck.cli --text samples/sample_policy.txt
python3 -m traincheck.cli --url https://example.com/privacy
python3 -m traincheck.cli --text samples/sample_policy.txt --json
```

## Web app (Streamlit Cloud target)

```bash
streamlit run streamlit_app.py
```

Paste a policy URL or text, optionally add related documents (AI terms, FAQ,
settings page) — training answers often span several documents — and get the
same quote-anchored audit in the browser. Deploy: push this repo to GitHub,
then connect it at share.streamlit.io and pick `streamlit_app.py`.
`requirements.txt` pins the Cloud runtime deps.

## Layout

- `rubric_v1.json` — the 16-item rubric (frozen for the pilot).
- `traincheck/parse.py` — section segmentation, sentence splitting, effective-date extraction.
- `traincheck/detectors.py` — high-precision detectors. T1–T6 are the fully
  specified novel items; core-10 detectors are provisional keyword baselines
  (labels pinned from the OPP-115 schema at annotation setup).
- `traincheck/llm.py` — model-agnostic LLM layer: quote-or-abstain
  extraction prompt, mechanical verbatim verification (non-matching quotes
  are dropped, never trusted), and plain-language explanations attached to
  verified quotes. Takes any `callable(prompt) -> str` client; no API key
  needed to use or test it. A live model client is still to be wired in.
- `traincheck/evaluate.py` — evaluation harness: per-item and overall
  accuracy, confusion counts, and Cohen's kappa for the double-annotation
  protocol, so both tool accuracy and dataset reliability are measured.
- `traincheck/score.py` — completeness aggregation.
- `traincheck/report.py` — Markdown report rendering.
- `traincheck/cli.py` — command-line audit tool.
- `samples/sample_policy.txt` — a SYNTHETIC policy written to exercise the
  detectors, including an intentional T1 contradiction (main text vs FAQ).

## Design rules (from the spec)

1. Deterministic first: no model calls in the core path.
2. Quote-or-abstain: no span found means "not stated", never invented.
3. "Not stated" and "contradictory" are first-class answers.
4. Multi-document ingest is required in the real app: a single-document audit
   misses FAQ opt-outs. The CLI currently audits one document; the web app
   adds multi-document support with per-quote document labels.
5. No leaderboard auto-published without human spot-checks.

## Status

Local scaffold only — not yet pushed to GitHub. Deploy target picked:
Streamlit Cloud (connect the GitHub repo at share.streamlit.io, pick
`streamlit_app.py`). Push is waiting on `gh auth login`.
