"""TrainCheck web app (Streamlit Cloud target).

Paste a policy URL or text, optionally add related documents (AI terms,
FAQ, settings page), and get a quote-anchored audit against rubric v1.0.

Layers, in order:
1. Deterministic rules (always run) — the audit.
2. LLM gap-fill (optional, needs an API key) — fills only items the
   rules left unresolved, with mechanically verified quotes only.
3. ML candidates (optional, needs a trained model file) — surfaced for
   review only; they never change an item's state.

Every item shows a "Why this decision" expansion: the aggregation rule
that set its state and the exact lines behind it, with each line's
provenance (rule / ML / LLM).
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
from traincheck.score import summarize

MODEL_PATH = Path("models/sentence_classifier.joblib")

st.set_page_config(page_title="TrainCheck", page_icon="🔍")
st.title("TrainCheck")
st.write(
    "Audit what an AI product's privacy policy actually says about training "
    "on your data. Every finding is anchored to a verbatim quoted clause, a "
    "section, and the document it came from. The headline is completeness of "
    "disclosure, never an 'unsafe company' verdict. Not legal advice."
)


def _resolve_api_key():
    try:
        key = st.secrets.get("OPENAI_API_KEY")
        if key:
            return key
    except Exception:  # noqa: BLE001 - secrets file may not exist
        pass
    return os.environ.get("OPENAI_API_KEY")


if st.button("Load sample policy", key="load_sample"):
    with open("samples/sample_policy.txt", encoding="utf-8") as f:
        st.session_state["policy_text"] = f.read()

url = st.text_input("Policy URL (fetched if provided, otherwise pasted text is used)")
policy_text = st.text_area("Paste the policy text", key="policy_text", height=280)

st.subheader("Additional documents (optional)")
st.caption("Training answers often span several documents — an FAQ opt-out is "
           "missed by a single-document audit. Add AI terms, FAQ, or settings pages here.")
doc2_name = st.text_input("Document 2 name", "AI terms")
doc2_text = st.text_area("Document 2 text", height=120, key="doc2")
doc3_name = st.text_input("Document 3 name", "FAQ / Help page")
doc3_text = st.text_area("Document 3 text", height=120, key="doc3")

st.subheader("Optional layers")
use_llm = st.checkbox("Use LLM gap-fill for unresolved items (needs API key)")
use_ml = False
if MODEL_PATH.exists():
    use_ml = st.checkbox("Show ML-surfaced candidate sentences (review only, do not change the audit)")

if st.button("Audit policy", key="audit"):
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
    if not docs:
        st.warning("Paste policy text or enter a URL first.")
    else:
        client, model_name = None, None
        if use_llm:
            api_key = _resolve_api_key()
            if not api_key:
                st.info("LLM gap-fill is off: add OPENAI_API_KEY to Streamlit "
                        "secrets (or the environment) to enable it. The "
                        "rules-only audit below is unaffected.")
            else:
                from traincheck.clients import openai_compatible_client
                from traincheck.clients import DEFAULT_MODEL
                model_name = os.environ.get("TRAINCHECK_MODEL", DEFAULT_MODEL)
                client = openai_compatible_client(api_key, model_name)
        ml_bundle, ml_candidates = None, {}
        if use_ml:
            from traincheck.ml import load_bundle, predict_candidates
            ml_bundle = load_bundle(str(MODEL_PATH))
        per_doc = []
        gapfill_diags = []
        for name, text in docs:
            doc = parse_document(text)
            results = detect_all(doc)
            if client is not None:
                results, diag = gapfill_doc_results(results, doc, text, client, model_name)
                gapfill_diags.append((name, diag))
            if ml_bundle is not None:
                ml_candidates[name] = predict_candidates(ml_bundle, doc)
            per_doc.append((name, results))
        merged = merge_results(per_doc)
        records = build_decision_records(merged)
        manifest = audit_manifest(
            [text for _, text in docs],
            models={"llm": model_name} if model_name else {})
        s = summarize(merged)
        st.success(
            f"Completeness: {s['stated']}/16 items stated, "
            f"{s['contradictory']} contradictory, "
            f"{s['partially stated']} partially stated, "
            f"{s['not stated']} not stated"
        )
        st.caption("Documents consulted: " + ", ".join(name for name, _ in docs))
        st.caption(f"Pipeline {manifest['pipeline_version']} · input {manifest['input_sha256'][:12]}")
        if gapfill_diags:
            for name, diag in gapfill_diags:
                if diag["upgraded"]:
                    st.caption(f"LLM gap-fill ({name}, {diag['model']}, temp 0): "
                               f"upgraded {', '.join(diag['upgraded'])}; "
                               f"dropped {len(diag['dropped'])} unverified quotes.")
        rows = []
        for item_id, r in merged.items():
            first = r["quotes"][0] if r["quotes"] else None
            ev = f"\"{first['quote']}\" ({first['document']} — {first['section']})" if first else ""
            value = r["value"]
            if isinstance(value, (list, dict)):
                value = str(value)
            rows.append({
                "Item": f"{item_id} — {r['title']}",
                "State": r["state"],
                "Value": value or "",
                "Evidence": ev,
            })
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
                for doc_name, cands in ml_candidates.items():
                    for ev in cands.get(item_id, []):
                        st.write(f"> {ev['quote']} (candidate, review only)")
                        st.caption(f"{doc_name} — {ev['section']} · {ev['sentence_id']} · "
                                   f"via {ev['source']} (confidence {ev['confidence']})")
