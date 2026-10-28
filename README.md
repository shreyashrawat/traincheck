# TrainCheck (v0.2)

An evidence-anchored audit of what AI products' privacy policies actually say
about training on your data. Paste a policy URL or text, get a per-item audit
against a 16-item rubric. Every finding carries a verbatim quoted clause, a
section, and a policy date/version. The headline is **completeness of
disclosure, never an "unsafe company" verdict**. Not legal advice.

This extends the 2021 POCASUM paper (completeness vs. an ideal policy) into
the AI-training question: trains by default? opt-out and where it lives? what
inputs count? retention for training? consumer vs API/enterprise scope? human
review and retroactivity?

## Quickstart

```bash
cd ~/workspace/traincheck
.venv/bin/python -m traincheck.cli --text samples/sample_policy.txt
.venv/bin/python -m traincheck.cli --url https://example.com/privacy
.venv/bin/python -m traincheck.cli --text samples/sample_policy.txt --json
# LLM gap-fill for unresolved items (needs OPENAI_API_KEY in the environment):
.venv/bin/python -m traincheck.cli --text samples/sample_policy.txt --gapfill
```

## Web app (Streamlit Cloud)

```bash
streamlit run streamlit_app.py
```

Paste a policy URL or text, optionally add related documents (AI terms, FAQ,
settings page) — training answers often span several documents — and get the
same quote-anchored audit in the browser. Live at the Streamlit URL connected
to https://github.com/shreyashrawat/traincheck (`streamlit_app.py`).
`requirements.txt` pins the Cloud runtime deps.

## Architecture: models propose, rules decide

The design rule that keeps the tool both powerful and explainable: **no model
output ever sets an item state directly.** Models surface candidate sentences;
deterministic rules turn evidence into decisions. Every decision is recorded
with the exact lines behind it.

- **Layer 0 — canonical text** (`parse.py`): sections split, sentences
  numbered S1, S2, … across the document. Every layer refers to sentence IDs.
- **Layer 1 — deterministic rules** (`detectors.py`, `merge.py`): the audit
  backbone. T1–T6 fully specified; core-10 keyword baselines. Merge rule:
  contradictory > stated > partially stated > not stated, with a
  cross-document contradiction check for T1.
- **Layer 2 — ML candidates** (`ml.py`): TF-IDF + logistic regression
  sentence classifier trained on annotation rows. It returns candidate
  sentences per item with confidences, shown in the app as review-only —
  they never change an item's state. Its second job is **distillation**:
  `distill_rule_candidates()` surfaces top phrases per item for a human to
  review and promote into deterministic rules, re-measuring after each
  promotion.
- **Layer 3 — LLM gap-fill** (`llm.py`, `gapfill.py`, `clients.py`): runs
  ONLY on items the rules left "not stated" or "partially stated", per
  document, before merging. Prompt is quote-or-abstain; every returned quote
  is mechanically verified as an exact substring of the source, and anything
  unverified is dropped and reported. Live calls use temperature 0, top_p 1,
  a fixed seed, and a pinned model version. Keys come from the environment
  or Streamlit secrets — never from the repo or chat.
- **Layer 4 — decision records** (`decisions.py`): per item, the state, the
  aggregation rule that set it, and every evidence line with its provenance
  (`rule:<item>` / `ml:<model>` / `llm:<model>`), plus an audit manifest
  (pipeline version + SHA-256 of the exact inputs) so any run is replayable.

## Layout

- `rubric_v1.json` — the 16-item rubric (frozen for the pilot).
- `traincheck/parse.py` — section segmentation, sentence splitting + IDs, effective-date extraction.
- `traincheck/detectors.py` — high-precision detectors with sentence-ID and source tagging.
- `traincheck/merge.py` — multi-document merge with a named decision rule per item.
- `traincheck/decisions.py` — decision records + audit manifest.
- `traincheck/llm.py` — model-agnostic LLM layer: quote-or-abstain
  extraction prompt, mechanical verbatim verification (non-matching quotes
  are dropped, never trusted), and plain-language explanations attached to
  verified quotes. Takes any `callable(prompt) -> str` client.
- `traincheck/clients.py` — live OpenAI-compatible client factory (env /
  secrets keys, temperature 0, pinned model). No key in code or repo.
- `traincheck/gapfill.py` — gap-fill orchestration: unresolved items only,
  verified quotes only, quote location back to section + sentence ID.
- `traincheck/annotations.py` — annotation validation, sentence-dataset
  builder, item gold, annotator kappa. CLI: `python -m traincheck.annotations
  --dir annotation/policies`.
- `traincheck/ml.py` — TF-IDF + logistic regression sentence classifier,
  candidate prediction, rule distillation, model save/load.
- `traincheck/evaluate.py` — evaluation harness: per-item and overall
  accuracy, confusion counts, and Cohen's kappa for the double-annotation
  protocol, so both tool accuracy and dataset reliability are measured.
- `traincheck/score.py` — completeness aggregation.
- `traincheck/report.py` — Markdown report rendering.
- `traincheck/cli.py` — command-line audit tool (`--json` now includes
  decision records + manifest; `--gapfill` enables the LLM layer).
- `annotation/` — schema, annotation guide, and a parser-matched template.
  Annotation files live in `annotation/policies/` (not yet populated —
  the annotation sprint is the next data step).
- `samples/sample_policy.txt` — a SYNTHETIC policy written to exercise the
  detectors, including an intentional T1 contradiction (main text vs FAQ).

## Annotation workflow

1. Generate a template from a policy's text (sentences must match the
   parser exactly), label sentences with item + stance, and set item states
   with evidence sentence IDs. See `annotation/schema.md` and
   `annotation/guide.md`.
2. Two annotators label each policy independently; validate, then adjudicate
   disagreements from the quotes, not from memory.
3. Split train/dev/test BY POLICY, never by sentence.
4. Train: `train_sentence_classifier(sentence_dataset(...))`; distill
   phrases; promote reviewed phrases into `detectors.py`; re-measure with
   `evaluate.py` against item gold.

## Design rules (from the spec)

1. Deterministic first: no model calls in the core path; model layers are
   gap-fillers and proposers, never deciders.
2. Quote-or-abstain: no span found means "not stated", never invented.
3. "Not stated" and "contradictory" are first-class answers.
4. Multi-document ingest is required in the real app: a single-document audit
   misses FAQ opt-outs.
5. No leaderboard auto-published without human spot-checks.
6. No distilled phrase becomes a rule without human review + re-measurement.

## Status

Deployed: public repo https://github.com/shreyashrawat/traincheck, Streamlit
app live (URL to record). Rules audit + decision records + annotation
tooling + ML baseline + LLM gap-fill wiring are in and tested. Still to come:
the annotation sprint (20 policies, double-annotated) — the data that trains
the classifier and produces the first real accuracy numbers — then the user
pilot, then the filing evidence bundle.
