# Annotation files

One file per policy per annotator, named `<policy-id>.<annotator>.json`
(see `../schema.md` and `../guide.md`).

## AI first pass (draft — pending human adjudication)

Files named `*.ai-pass1.json` (annotator `ai-pass1`) are **AI first-pass
draft labels** produced 2026-11-12 by labeling each policy text against
the 16-item rubric from the text alone. They are a starting point, not
gold labels: every item state and sentence label needs human review
before it is used as training or evaluation data.

- **All 34 policies are now labeled.** The follow-up pass (same blind
  rules) completed 2026-11-12 for khanmigo, quillbot, elevenlabs, and
  suno — the elevenlabs/suno labels are against the current official
  texts, not the replaced provisional versions. Full totals: 353 stated
  / 67 partially stated / 124 not stated / 0 contradictory (of 544
  items).
- Zero items were judged "contradictory" in this pass; treat that as
  a property of the pass, not of the policies.

## Workflow

1. Copy a template from `../templates/<slug>.json` to
   `<slug>.<annotator>.json` and label from the text. Two annotators
   label each policy independently from the same template.
2. Validate: `python -m traincheck.annotations --dir annotation/policies`
   (the validator rejects any file whose sentences drift from
   `parse_document()` output, and prints kappa for same-policy pairs).
3. Adjudicate disagreements into the gold item states.

Train/dev/test splits are **by policy, never by sentence** — two files
for the same policy always land in the same split.
