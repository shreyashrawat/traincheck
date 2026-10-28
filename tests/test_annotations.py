"""Annotation tests. Run: python3 tests/test_annotations.py"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.annotations import (annotator_pair_kappa, item_gold,  # noqa: E402
                                    load_annotation, sentence_dataset,
                                    validate_annotation)
from traincheck.parse import parse_document  # noqa: E402

TEXT = ("We use your prompts to train our models. "
        "You can opt out of training in Settings.")


def _make_ann(annotator, t1_state):
    doc = parse_document(TEXT)
    sentences = []
    for s in doc["sections"]:
        for t, sid in zip(s["sentences"], s["sentence_ids"]):
            sentences.append({"id": sid, "section": s["title"], "text": t, "labels": []})
    sentences[0]["labels"] = [{"item": "T1", "stance": "states"},
                              {"item": "T3", "stance": "states"}]
    sentences[1]["labels"] = [{"item": "T2", "stance": "states"}]
    items = {f"C{i}": {"state": "not stated", "evidence": []} for i in range(1, 11)}
    items.update({f"T{i}": {"state": "not stated", "evidence": []} for i in range(1, 7)})
    items["T1"] = {"state": t1_state,
                   "evidence": [{"document": "Policy", "sentence_id": "S1"}] if t1_state == "stated" else []}
    items["T2"] = {"state": "stated", "evidence": [{"document": "Policy", "sentence_id": "S2"}]}
    return {"policy_id": "test-policy", "source_url": "", "annotator": annotator,
            "documents": [{"name": "Policy", "text": TEXT, "sentences": sentences}],
            "items": items}


def test_validate_and_dataset_and_kappa():
    a, b = _make_ann("ann-a", "stated"), _make_ann("ann-b", "not stated")
    assert validate_annotation(a) == [], validate_annotation(a)
    assert validate_annotation(b) == [], validate_annotation(b)
    rows = sentence_dataset([a, b])
    assert len(rows) == 4, rows
    assert rows[0]["items"] == ["T1", "T3"], rows[0]
    gold = item_gold([a])
    assert gold["test-policy"]["T1"] == "stated"
    kappa = annotator_pair_kappa(a, b)
    assert kappa["pairs"] == 16, kappa
    assert 0 < kappa["kappa"] < 1, kappa  # one disagreement out of 16


def test_validate_catches_drift():
    bad = _make_ann("ann-a", "stated")
    bad["documents"][0]["sentences"][0]["text"] = "Tampered sentence."
    errors = validate_annotation(bad)
    assert errors, "expected validation errors for tampered text"


def test_cli_validates_directory():
    with tempfile.TemporaryDirectory() as tmp:
        for name, ann in (("p.ann-a.json", _make_ann("ann-a", "stated")),
                          ("p.ann-b.json", _make_ann("ann-b", "stated"))):
            Path(tmp, name).write_text(json.dumps(ann), encoding="utf-8")
        from traincheck.annotations import main
        assert main(["--dir", tmp]) == 0


if __name__ == "__main__":
    test_validate_and_dataset_and_kappa()
    test_validate_catches_drift()
    test_cli_validates_directory()
    print("annotation tests passed")
