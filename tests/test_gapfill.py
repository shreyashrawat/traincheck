"""Gap-fill tests (fake clients, no network). Run: python3 tests/test_gapfill.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.detectors import detect_all  # noqa: E402
from traincheck.gapfill import gapfill_doc_results, locate_quote  # noqa: E402
from traincheck.parse import parse_document  # noqa: E402

# Rules miss this paraphrase (no "train"/"model" wording), so T1 starts
# "not stated" — exactly the gap the LLM layer is meant to fill.
TEXT = ("Your conversations help our systems learn. "
        "We collect your data to improve our services.")


def _setup():
    doc = parse_document(TEXT)
    return doc, detect_all(doc)


def test_verbatim_quote_upgrades():
    doc, results = _setup()
    assert results["T1"]["state"] == "not stated", results["T1"]

    def fake(prompt):
        return json.dumps({"T1": {"quote": "Your conversations help our systems learn."}})

    new, diag = gapfill_doc_results(results, doc, TEXT, fake, "test-model")
    assert new["T1"]["state"] == "stated", new["T1"]
    assert new["T1"]["gapfilled"] is True
    ev = new["T1"]["quotes"][0]
    assert ev["source"] == "llm:test-model"
    assert ev["section"] == "Introduction"
    assert ev["sentence_id"] == "S1", ev
    assert diag["upgraded"] == ["T1"]
    # Input untouched.
    assert results["T1"]["state"] == "not stated"


def test_hallucinated_quote_dropped():
    doc, results = _setup()

    def fake(prompt):
        return json.dumps({"T1": {"quote": "We sell your data to advertisers."}})

    new, diag = gapfill_doc_results(results, doc, TEXT, fake, "test-model")
    assert new["T1"]["state"] == "not stated"
    assert "T1" in diag["dropped"], diag


def test_garbled_output_abstains():
    doc, results = _setup()
    new, _diag = gapfill_doc_results(results, doc, TEXT, lambda p: "not json", "test-model")
    assert new["T1"]["state"] == "not stated"


def test_no_client_no_change():
    doc, results = _setup()
    new, _diag = gapfill_doc_results(results, doc, TEXT, None, "test-model")
    assert new is results


def test_locate_quote():
    doc, _ = _setup()
    section, sid = locate_quote(doc, "Your conversations help our systems learn.")
    assert (section, sid) == ("Introduction", "S1")
    assert locate_quote(doc, "absent sentence") == (None, None)


if __name__ == "__main__":
    test_verbatim_quote_upgrades()
    test_hallucinated_quote_dropped()
    test_garbled_output_abstains()
    test_no_client_no_change()
    test_locate_quote()
    print("gapfill tests passed")
