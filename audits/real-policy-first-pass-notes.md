# Real-policy first pass (Oct 27, 2026) — NOT final annotations

Fetched + audited 3 live policies with the deterministic CLI. Outputs in
`audits/*.md`. This pass validated the detectors on real text and fixed
precision bugs. It is not the double-annotated pilot set (that still needs
the Nov 10 sprint + a second annotator).

## Fixes made + verified (sample still 14/16; merge + app tests pass)

1. **T6 retroactivity false positive:** bare "does not apply to" no longer
   counts as retroactivity. OpenAI's and Anthropic's scope carve-outs
   ("This Privacy Policy does not apply to ... API/Enterprise") were
   misread as retroactivity addressed. Now retroactivity needs "already
   used", "retroactive", or an opt-out-tied "does not affect" clause.
2. **T2 training scope:** a generic opt-out (e.g. Google's profiling /
   targeted-advertising opt-out) no longer reports as a training opt-out.
   Training-scoped opt-out = stated; generic opt-out = partially stated.
   Control location is only taken from a training sentence now.
3. **T5 scope context:** scope terms need a training/applicability context
   sentence. Residual gap: "applicable" still trips the context rule
   (Google's education hit comes from "applicable age"), so T5 stays noisy
   on real pages — the LLM layer is the real fix.
4. **T3 inputs/outputs added:** Anthropic's training list ("Inputs and
   Outputs from our Services ... Feedback") now yields inputs, outputs,
   feedback instead of just feedback.
5. **fetch_url:** strips nav/header/footer/script/style and converts
   h1–h3 to Markdown sections, so audits now carry real section names
   instead of one giant "Introduction" plus nav boilerplate.

## Genuine multi-document findings (validates the design)

- OpenAI T3 partially stated + T2 control location None: input types and
  the training control live in the linked help-center article, not the
  policy itself. The app's additional-document slots exist for this.
- Anthropic T4 partially stated: retention-for-training detail lives in
  their separate Non-User Privacy Policy document.

## Known keyword-baseline limits (LLM layer's job, not more regex)

- Rights/change sections phrased unusually are missed (OpenAI C4,
  Anthropic C2, Google C7 all have relevant sections the keyword patterns
  don't catch). Do not keep patching regex for these; the quote-or-abstain
  LLM layer is the planned fix.
- OpenAI effective date not found by the date extractor (format differs
  from the patterns); needs a format check, not a guess.
