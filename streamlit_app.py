"""TrainCheck web app (Streamlit Cloud target).

Paste a policy URL or text, optionally add related documents (AI terms,
FAQ, settings page), and get a quote-anchored audit against rubric v1.0.
"""

import streamlit as st

from traincheck.cli import fetch_url
from traincheck.detectors import detect_all
from traincheck.merge import merge_results
from traincheck.parse import parse_document
from traincheck.score import summarize

st.set_page_config(page_title="TrainCheck", page_icon="🔍")
st.title("TrainCheck")
st.write(
    "Audit what an AI product's privacy policy actually says about training "
    "on your data. Every finding is anchored to a verbatim quoted clause, a "
    "section, and the document it came from. The headline is completeness of "
    "disclosure, never an 'unsafe company' verdict. Not legal advice."
)

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
        per_doc = [(name, detect_all(parse_document(text))) for name, text in docs]
        merged = merge_results(per_doc)
        s = summarize(merged)
        st.success(
            f"Completeness: {s['stated']}/16 items stated, "
            f"{s['contradictory']} contradictory, "
            f"{s['partially stated']} partially stated, "
            f"{s['not stated']} not stated"
        )
        st.caption("Documents consulted: " + ", ".join(name for name, _ in docs))
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
        for item_id, r in merged.items():
            with st.expander(f"{item_id} — {r['title']} ({r['state']})"):
                if not r["quotes"]:
                    st.write("No evidence found — this item is not stated in the documents provided.")
                for q in r["quotes"]:
                    st.write(f"> {q['quote']}")
                    st.caption(f"{q['document']} — {q['section']}")
