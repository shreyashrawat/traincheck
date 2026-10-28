"""TrainCheck web app (Streamlit Cloud target).

Built for a normal user, Robinhood-style: the eye gets the answer before
any text is read. In order:
1. One giant number (the score) + one plain sentence.
2. A donut of the 16 questions + two clarity bars.
3. Cards: what's missing, what to do next.
4. Compare with another app, side by side.
5. Full report, collapsed — the 16-item audit plus "Why this decision"
   detail (sentence IDs, sources, decision rules) for anyone who wants it.

Internal information (sentence IDs, rule IDs, model names, decision
rules, pipeline manifest) appears ONLY in layer 5, never above it.
"""

import os
from pathlib import Path

import streamlit as st

from traincheck.cli import fetch_url
from traincheck.decisions import audit_manifest, build_decision_records
from traincheck.detectors import detect_all
from traincheck.gapfill import gapfill_doc_results
from traincheck.merge import merge_results
from traincheck.parse import parse_document
from traincheck.plain import bottom_line, next_actions, plain_problem
from traincheck.score import compare_scores, summarize, transparency_score
from traincheck.viz import bar_html, donut_html, hero_css

MODEL_PATH = Path("models/sentence_classifier.joblib")

st.set_page_config(page_title="TrainCheck", page_icon="🔍")
st.markdown(hero_css(), unsafe_allow_html=True)
st.title("TrainCheck")
st.write("Paste an AI product's privacy policy. See in seconds how clearly "
         "it explains what happens to your data.")


def _resolve_api_key():
    try:
        key = st.secrets.get("OPENAI_API_KEY")
        if key:
            return key
    except Exception:  # noqa: BLE001 - secrets file may not exist
        pass
    return os.environ.get("OPENAI_API_KEY")


def _run_audit(docs, use_llm):
    """docs: [(name, text)]. Returns (merged, records, manifest, gapfill_diags)."""
    client, model_name = None, None
    if use_llm:
        api_key = _resolve_api_key()
        if not api_key:
            st.info("LLM gap-fill is off: add OPENAI_API_KEY to Streamlit "
                    "secrets (or the environment) to enable it. The "
                    "rules-only audit below is unaffected.")
        else:
            from traincheck.clients import DEFAULT_MODEL, openai_compatible_client
            model_name = os.environ.get("TRAINCHECK_MODEL", DEFAULT_MODEL)
            client = openai_compatible_client(api_key, model_name)
    per_doc = []
    gapfill_diags = []
    for name, text in docs:
        doc = parse_document(text)
        results = detect_all(doc)
        if client is not None:
            results, diag = gapfill_doc_results(results, doc, text, client, model_name)
            gapfill_diags.append((name, diag))
        per_doc.append((name, results))
    merged = merge_results(per_doc)
    records = build_decision_records(merged)
    manifest = audit_manifest(
        [text for _, text in docs],
        models={"llm": model_name} if model_name else {})
    return merged, records, manifest, gapfill_diags


def _collect_docs(url, policy_text, doc2_name, doc2_text, doc3_name, doc3_text):
    docs = []
    if url.strip():
        try:
            docs.append(("Policy (URL)", fetch_url(url.strip())))
        except Exception as exc:  # noqa: BLE001 - surface fetch failures plainly
            st.error(f"Could not fetch that URL: {exc}")
    elif policy_text.strip():
        docs.append(("Policy", policy_text))
    if doc2_text.strip():
        docs.append((doc2_name.strip() or "Document 2", doc2_text))
    if doc3_text.strip():
        docs.append((doc3_name.strip() or "Document 3", doc3_text))
    return docs


if st.button("Load sample policy", key="load_sample"):
    with open("samples/sample_policy.txt", encoding="utf-8") as f:
        st.session_state["policy_text"] = f.read()

url = st.text_input("Policy URL (fetched if provided, otherwise pasted text is used)")
policy_text = st.text_area("Paste the policy text", key="policy_text", height=280)

st.subheader("Additional documents for the same app (optional)")
st.caption("Training answers often span several documents — an FAQ opt-out is "
           "missed by a single-document audit. Add AI terms, FAQ, or settings pages here.")
doc2_name = st.text_input("Document 2 name", "AI terms")
doc2_text = st.text_area("Document 2 text", height=120, key="doc2")
doc3_name = st.text_input("Document 3 name", "FAQ / Help page")
doc3_text = st.text_area("Document 3 text", height=120, key="doc3")

with st.expander("Advanced options"):
    use_llm = st.checkbox("Use LLM gap-fill for unresolved items (needs API key)")
    use_ml = False
    if MODEL_PATH.exists():
        use_ml = st.checkbox("Show ML-surfaced candidate sentences (review only)")

if st.button("Audit policy", key="audit"):
    docs = _collect_docs(url, policy_text, doc2_name, doc2_text, doc3_name, doc3_text)
    if not docs:
        st.warning("Paste policy text or enter a URL first.")
    else:
        merged, records, manifest, gapfill_diags = _run_audit(docs, use_llm)
        ml_candidates = {}
        if use_ml:
            from traincheck.ml import load_bundle, predict_candidates
            bundle = load_bundle(str(MODEL_PATH))
            for name, text in docs:
                ml_candidates[name] = predict_candidates(bundle, parse_document(text))
        st.session_state["audit_result"] = {
            "merged": merged, "records": records, "manifest": manifest,
            "gapfill_diags": gapfill_diags, "ml_candidates": ml_candidates,
            "doc_names": [name for name, _ in docs],
        }

audit = st.session_state.get("audit_result")
if audit:
    merged = audit["merged"]
    records = audit["records"]
    score = transparency_score(merged)
    s = summarize(merged)

    # Layer 1: one giant number + one plain sentence.
    st.markdown(f"<div class='tc-hero-num'>{score['score']}</div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='tc-hero-sub'>/ 10 · {score['label']} — "
                f"{bottom_line(merged)}</div>", unsafe_allow_html=True)
    st.caption("How clearly this policy explains what happens to your data — "
               "higher means clearer, not safer.")

    # Layer 2: the picture — donut + two clarity bars.
    col_donut, col_bars = st.columns([1, 1])
    with col_donut:
        st.markdown(donut_html(s, score["score"], score["label"]),
                    unsafe_allow_html=True)
    with col_bars:
        st.write(f"**Training questions: {score['training']['clear']}/6 clear**")
        st.markdown(bar_html(score["training"]["clear"] / 6),
                    unsafe_allow_html=True)
        st.write(f"**Basics: {score['basics']['clear']}/10 clear**")
        st.markdown(bar_html(score["basics"]["clear"] / 10),
                    unsafe_allow_html=True)
        st.caption(f"{s['stated']} of 16 questions answered clearly.")

    # Layer 3a: what's missing or unclear — cards, not a wall of text.
    st.subheader("What's missing or unclear")
    gaps = [(iid, r) for iid, r in merged.items() if plain_problem(iid, r)]
    if not gaps:
        st.write("Nothing missing — every question is answered clearly.")
    for iid, r in gaps:
        with st.container(border=True):
            st.write(f"**{iid} — {r['title']}**")
            st.write(plain_problem(iid, r))
            for q in r["quotes"]:
                st.write(f"> {q['quote']}")
                st.caption(f"{q.get('document') or 'Policy'} — {q['section']}")

    # Layer 3b: what you can do next — cards.
    st.subheader("What you can do next")
    actions = next_actions(merged, score)
    if not actions:
        st.write("Nothing needed — this policy is clear and states its training stance.")
    for a in actions:
        with st.container(border=True):
            st.write(f"**{a['title']}** — {a['detail']}")

    # Layer 4: compare with another app, side by side.
    st.subheader("Compare with another app")
    st.caption("Paste a competing app's policy — the higher score has the clearer policy.")
    cmp_url = st.text_input("Competing app's policy URL")
    cmp_text = st.text_area("Or paste the competing app's policy text", height=150, key="cmp_text")
    if st.button("Compare", key="compare"):
        cmp_docs = _collect_docs(cmp_url, cmp_text, "", "", "", "")
        if not cmp_docs:
            st.warning("Paste the competing app's policy text or enter its URL first.")
        else:
            cmp_merged, _, _, _ = _run_audit(cmp_docs, False)
            cmp = compare_scores(merged, cmp_merged)
            col_a, col_b = st.columns(2)
            col_a.metric("This app", f"{cmp['a']}/10")
            col_b.metric("Other app", f"{cmp['b']}/10")
            if cmp["better"] == "tie":
                st.write(f"It's a tie — both score {cmp['a']}/10.")
            elif cmp["better"] == "A":
                st.write(f"This app scores higher by {cmp['delta']}.")
            else:
                st.write(f"The other app scores higher by {cmp['delta']}.")
            st.write("Other app: " + bottom_line(cmp_merged))

    # Layer 5: full report, collapsed.
    with st.expander("Full report — all 16 questions"):
        rows = []
        for item_id, r in merged.items():
            first = r["quotes"][0] if r["quotes"] else None
            ev = f"\"{first['quote']}\" ({first.get('document') or 'Policy'} — {first['section']})" if first else ""
            value = r["value"]
            if isinstance(value, (list, dict)):
                value = str(value)
            rows.append({"Item": f"{item_id} — {r['title']}", "State": r["state"],
                         "Value": value or "", "Evidence": ev})
        st.table(rows)
        for item_id, rec in records.items():
            with st.expander(f"{item_id} — {rec['title']} ({rec['state']})"):
                st.caption(f"Decision rule: {rec['decision_rule']}"
                           + (" · LLM gap-filled" if rec["gapfilled"] else ""))
                if not rec["evidence"]:
                    st.write("No evidence found — this item is not stated in the documents provided.")
                for ev in rec["evidence"]:
                    st.write(f"> {ev['quote']}")
                    st.caption(f"{ev['document']} — {ev['section']} · {ev['sentence_id']} · via {ev['source']}")
                for doc_name, cands in audit["ml_candidates"].items():
                    for ev in cands.get(item_id, []):
                        st.write(f"> {ev['quote']} (candidate, review only)")
                        st.caption(f"{doc_name} — {ev['section']} · {ev['sentence_id']} · "
                                   f"via {ev['source']} (confidence {ev['confidence']})")
        st.caption("Documents consulted: " + ", ".join(audit["doc_names"]))
        st.caption(f"Pipeline {audit['manifest']['pipeline_version']} · "
                   f"input {audit['manifest']['input_sha256'][:12]}")
        for name, diag in audit["gapfill_diags"]:
            if diag["upgraded"]:
                st.caption(f"LLM gap-fill ({name}, {diag['model']}, temp 0): "
                           f"upgraded {', '.join(diag['upgraded'])}; "
                           f"dropped {len(diag['dropped'])} unverified quotes.")
