# Annotation schema

One file per policy per annotator, in `annotation/policies/`, named
`<policy-id>.<annotator>.json`. Start from a template generated from the
policy text so sentence IDs and text already match the parser — the
validator (`python -m traincheck.annotations --dir annotation/policies`)
rejects any file whose sentences drift from `parse_document()` output.

## File shape

```json
{
  "policy_id": "anthropic-2026-09",
  "source_url": "https://www.anthropic.com/legal/privacy",
  "annotator": "shrey",
  "documents": [
    {"name": "Policy", "text": "<full text>",
     "sentences": [
       {"id": "S1", "section": "Introduction", "text": "...",
        "labels": [{"item": "T1", "stance": "states"}]}
     ]}
  ],
  "items": {
    "T1": {"state": "stated",
           "evidence": [{"document": "Policy", "sentence_id": "S4"}]}
  }
}
```

## Sentence labels

A sentence can carry several labels. `stance` values:

- `states` — the sentence asserts the thing (e.g. "We use your prompts
  to train our models" → T1 `states`, T3 `states`).
- `denies` — the sentence denies or carves it out (e.g. "We do not use
  API data to train" → T1 `denies` for the API scope, T5 `states`).
- `mentions` — the sentence touches the item without settling it (e.g.
  a generic "you can control your data" sentence for T2 when no
  training control is named).

Label generously at sentence level: the classifier learns from these
rows, and an extra `mentions` label is cheaper than a missing one.

## Item states

The `items` map is the adjudicated gold for evaluation: the item's
final state (`stated` / `partially stated` / `contradictory` /
`not stated`) plus the evidence sentences that justify it. When two
annotators disagree, the adjudicated file keeps the agreed state and
both evidence sets can be listed.

## Splitting

Train/dev/test splits are BY POLICY, never by sentence. Two files for
the same policy (two annotators) always land in the same split.
