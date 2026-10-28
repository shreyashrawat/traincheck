"""Merge tests (stdlib only). Run: python3 tests/test_merge.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.detectors import detect_all  # noqa: E402
from traincheck.merge import merge_results  # noqa: E402
from traincheck.parse import parse_document  # noqa: E402


def test_cross_document_t1_contradiction():
    main = "We may use your prompts to train and improve our AI models by default."
    faq = "We do not use your data to train our models."
    merged = merge_results([
        ("Policy", detect_all(parse_document(main))),
        ("FAQ", detect_all(parse_document(faq))),
    ])
    assert merged["T1"]["state"] == "contradictory", merged["T1"]
    docs = {q["document"] for q in merged["T1"]["quotes"]}
    assert docs == {"Policy", "FAQ"}, docs


def test_merge_prefers_stated_over_not_stated():
    main = "You can opt out of training in Settings > Privacy."
    empty = "This document says nothing relevant."
    merged = merge_results([
        ("Policy", detect_all(parse_document(main))),
        ("Other", detect_all(parse_document(empty))),
    ])
    assert merged["T2"]["state"] == "stated", merged["T2"]
    assert merged["T2"]["quotes"][0]["document"] == "Policy"


if __name__ == "__main__":
    test_cross_document_t1_contradiction()
    test_merge_prefers_stated_over_not_stated()
    print("merge tests passed")
