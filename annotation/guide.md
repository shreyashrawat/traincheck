# Annotation guide

## Protocol

1. Two annotators label each policy independently, from the same
   template file. Do not discuss labels mid-pass.
2. Validate: `python -m traincheck.annotations --dir annotation/policies`.
   Fix structural errors before comparing.
3. Compare item states. For every disagreement, read the sentences
   together and pick the state the quotes actually support — not the
   state you wish the policy had. Record the agreed state in the
   adjudicated file.
4. Report kappa (the validator prints it for same-policy pairs).
   Below ~0.6 on an item, the item's definition needs tightening
   before its labels are trusted for training.

## Judgment calls

- **Hedging counts as stated, weakly.** "May use" still states a
  practice; note it in the sentence label (`mentions` if you judge it
  too weak to count, but be consistent).
- **Scope carve-outs are evidence, not absence.** "Does not apply to
  API data" is T5 `states` and T1 `denies` for that scope — never
  "not stated".
- **Cross-document answers stay per-document.** If the opt-out lives
  in the FAQ, the Policy file's T2 is `not stated` and the FAQ file's
  T2 is `stated`. The merge step combines them; annotators do not.
- **Paraphrase counts.** "Improve our services using your inputs"
  with no mention of training is T1 `mentions`, not `states` — the
  classifier must learn that paraphrase is weaker than an explicit
  training statement, so label the distinction, don't erase it.
- **Retention needs a training link for T4.** A generic "we retain
  data for 2 years" sentence is C5, not T4, unless the sentence ties
  retention to training.

## What not to do

- Do not copy the tool's current output as labels. Annotate from the
  text; the tool is what is being measured.
- Do not label from memory of a policy version you read last month.
  Label the text in the file, with its date.
