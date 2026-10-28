"""Decision-record tests. Run: python3 tests/test_decisions.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.decisions import audit_manifest, build_decision_records  # noqa: E402
from traincheck.detectors import detect_all  # noqa: E402
from traincheck.merge import merge_results  # noqa: E402
from traincheck.parse import parse_document  # noqa: E402


def test_cross_document_record():
    merged = merge_results([
        ("Policy", detect_all(parse_document(
            "We may use your prompts to train and improve our AI models by default."))),
        ("FAQ", detect_all(parse_document("We do not use your data to train our models."))),
    ])
    rec = build_decision_records(merged)["T1"]
    assert rec["state"] == "contradictory", rec
    assert rec["decision_rule"] == "cross-document-contradiction", rec
    assert {e["document"] for e in rec["evidence"]} == {"Policy", "FAQ"}
    assert all(e["sentence_id"] for e in rec["evidence"]), rec["evidence"]
    assert all(e["source"].startswith("rule:") for e in rec["evidence"])


def test_single_doc_record():
    rec = build_decision_records(
        detect_all(parse_document("You can opt out of training in Settings > Privacy.")))["T2"]
    assert rec["state"] == "stated", rec
    assert rec["decision_rule"] == "detector", rec
    assert rec["evidence"][0]["sentence_id"] == "S1", rec["evidence"]
    assert rec["evidence"][0]["source"] == "rule:T2"


def test_manifest_hash_stable():
    a = audit_manifest(["same text"])
    b = audit_manifest(["same text"])
    c = audit_manifest(["different text"])
    assert a["input_sha256"] == b["input_sha256"]
    assert a["input_sha256"] != c["input_sha256"]
    assert a["pipeline_version"] == "0.2.0"


if __name__ == "__main__":
    test_cross_document_record()
    test_single_doc_record()
    test_manifest_hash_stable()
    print("decision tests passed")
