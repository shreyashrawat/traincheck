# TrainCheck policy dataset (v1.2, raw)

Raw privacy-policy texts for all 34 target consumer AI products — the source material
for TrainCheck's ML training dataset. Each file is the full text of one
product's official privacy policy, saved for annotation (sentence-level
labels against the 16-item TrainCheck rubric) and classifier training.

## Layout

- `raw/<slug>.md` — one file per product. YAML frontmatter at the top
  (`product`, `company`, `source_url`, `fetched_date`, `policy_date`),
  then the full policy text. Only navigation menus, cookie banners, and
  footer boilerplate were stripped; policy wording is intact.
- `manifest.json` — one entry per product (slug, product, company,
  source URL, fetched date, policy date, word/sentence counts, status,
  failure reason when failed, and sourcing notes).
- `../annotation/templates/<slug>.json` — annotation templates generated
  from these raw files (see below). Templates live under `annotation/`,
  not here, per `annotation/schema.md`.

## How it was collected (2026-11-12)

Each policy was located on the company's own domain via web search and
fetched in full with a browser read. No text was summarized, paraphrased,
or invented: where a fetch failed (blocks, rate limits), the product is
recorded as failed in the manifest instead of being substituted with a
stale or third-party copy. A few files were completed from alternate
copies of the *identical* document version (same policy date) when the
primary read was rate-limited mid-fetch; those cases are noted per-file
in the manifest.

Texts are reproduced here for research and annotation use, with the
source URL and the policy's stated effective/last-updated date recorded
in each file's frontmatter and in the manifest. Policies change: the
`policy_date` is the version that was annotated, and re-fetching later
may return a newer version.

## Collection status (2026-11-12, v1.2)

34 of 34 fetched OK (**222,996 words, 9,200 sentences**). 0 failed,
0 provisional. v1 shipped 28 of 30; the v1.1 round added 3 new policies
(Canva, Fireflies.ai, Nomi), landed the Character.AI retry, and
re-fetched Stability AI and Runway from their current official policies.
The v1.2 round closed the collection:

- **Khanmigo** — recovered via a live-browser read of Khan Academy's
  main privacy policy (Khanmigo is governed by the main policy, not the
  separate Kids policy); automated fetches were Cloudflare-blocked and
  the Wayback retry failed. Policy dated 2026-01-30.
- **QuillBot** — recovered via a live-browser read of the Learneo, Inc.
  umbrella policy covering QuillBot (JS-rendered page; Wayback 403).
  Policy updated 2026-08-17.
- **ElevenLabs** — re-fetched from the official policy via a
  live-browser read, replacing the provisional 2026-05-20 Fineprinted
  snapshot. Current version updated 2026-10-09.
- **Suno** — re-fetched from the official https://suno.com/privacy via a
  live-browser read, replacing the provisional suno.tech copy. Current
  version last modified 2026-06-23.

Navigation-only table-of-contents lists were stripped from ElevenLabs
(`Quicklinks`) and Suno (the Overview contents list), matching the
Khanmigo and QuillBot files, so templates contain policy text only.

## From raw text to annotations

`annotation/templates/<slug>.json` holds one template per fetched
policy, generated from the raw text with the repo's own parser
(`traincheck.parse.parse_document`), so sentence IDs already match what
the validator expects. Each template has `annotator: "TEMPLATE"`, empty
sentence labels, and all 16 rubric items set to `"not stated"` with
empty evidence.

To annotate (per `annotation/schema.md` and `annotation/guide.md`):

1. Copy a template to `annotation/policies/<policy-id>.<annotator>.json`
   (e.g. `openai-chatgpt.shrey.json`) and label from the text.
   Two annotators label each policy independently from the same template.
2. Validate: `python -m traincheck.annotations --dir annotation/policies`
   (the validator rejects any file whose sentences drift from
   `parse_document()` output, and prints kappa for same-policy pairs).
3. Adjudicate disagreements into the gold item states.

Train/dev/test splits are **by policy, never by sentence** — two files
for the same policy always land in the same split.

## Separate AI-training terms documents (not fetched — v2 candidates)

Several companies publish AI-training terms separately from the main
privacy policy. These were noted during collection but deliberately NOT
fetched for v1 (primary policy only). They are candidates for the
multi-document ingest layer later:

- Anthropic — Non-User Privacy Policy: https://www.anthropic.com/legal/non-user-privacy-policy
- Google — Gemini Apps Privacy Notice: https://support.google.com/gemini/answer/13594961?hl=en
- Microsoft — Transparency Note for Microsoft Copilot: https://support.microsoft.com/topic/transparency-note-for-microsoft-copilot-c1541cad-8bb4-410a-954c-07225892dbc2
- Midjourney — Public Summary of Training Content: https://docs.midjourney.com/hc/en-us/articles/48067080311309-Public-Summary-of-Training-Content
- Perplexity — API Privacy & Security (API-specific): https://docs.perplexity.ai/docs/resources/privacy-security
- DeepSeek — Model Mechanism and Training Methods: https://cdn.deepseek.com/policies/en-US/model-algorithm-disclosure.html
- Notion — Notion AI Learning and Early Access Program Terms: https://notion.notion.site/Notion-AI-Learning-and-Early-Access-Program-Terms-0c55d702d0154a788d9e70c4ee396399
- Grammarly — Product Improvement and Training Control: https://support.grammarly.com/hc/en-us/articles/25555503115277-Product-Improvement-and-Training-Control
- Adobe — Generative AI User Guidelines: http://www.adobe.com/uk/legal/licenses-terms/adobe-gen-ai-user-guidelines.html
- GitHub — ToS Section J announcement (AI features, training, and your data): https://github.blog/changelog/2026-03-25-updates-to-our-privacy-statement-and-terms-of-service-how-we-use-your-data/
- Cursor — Data-use page: https://cursor.com/data-use (verify directly; found via search snippet)
- Character.AI — model-training settings FAQ: https://support.character.ai/hc/en-us/articles/42788047758747-How-do-I-manage-update-my-model-training-settings
- Mistral — Memories data handling (Help Center): https://help.mistral.ai/en/articles/396497-how-do-you-handle-my-data-when-using-the-memories-feature
- Zoom — "How Zoom AI features handle your data" support article (KB0057861); no-training clause is in the Terms of Service: https://www.zoom.com/en/trust/terms/
