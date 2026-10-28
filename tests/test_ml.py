"""ML baseline tests (synthetic sentences). Run: python3 tests/test_ml.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.ml import (distill_rule_candidates, predict_candidates,  # noqa: E402
                           train_sentence_classifier)
from traincheck.parse import parse_document  # noqa: E402

T1_SENTS = [
    "We use your prompts to train our AI models.",
    "Your data helps train our models by default.",
    "We train machine learning models on user content.",
    "Model training uses conversation data.",
    "We may use uploads to train our systems.",
    "Training data includes your prompts and files.",
]
T2_SENTS = [
    "You can opt out of training in Settings.",
    "Opt out of model training from your privacy dashboard.",
    "Turn off training data use in account settings.",
    "You may opt out of AI training at any time.",
    "Disable training in the privacy controls to opt out.",
    "Choose to opt out of data use for training.",
]
FILLER = [
    "We collect your email address when you sign up.",
    "Contact us with questions about this policy.",
    "This policy was last updated in January.",
    "We store data on secure servers.",
    "You must be 18 to use this service.",
    "Our offices are located in California.",
    "We may update this policy from time to time.",
    "Please read the terms of service carefully.",
]


def _rows():
    rows = [{"text": t, "section": "Training", "items": ["T1"]} for t in T1_SENTS]
    rows += [{"text": t, "section": "Choices", "items": ["T2"]} for t in T2_SENTS]
    rows += [{"text": t, "section": "General", "items": []} for t in FILLER]
    return rows


def test_train_predict_distill():
    bundle = train_sentence_classifier(_rows())
    doc = parse_document("You can opt out of training in your settings. "
                         "We use your data to train our models. "
                         "Contact us with questions.")
    cands = predict_candidates(bundle, doc)
    t2_quotes = [e["quote"] for e in cands.get("T2", [])]
    t1_quotes = [e["quote"] for e in cands.get("T1", [])]
    assert any("opt out" in q for q in t2_quotes), cands
    assert any("train" in q for q in t1_quotes), cands
    assert all(e["source"] == "ml:tfidf-lr-v1" for evs in cands.values() for e in evs)
    distilled = distill_rule_candidates(bundle, top_n=10)
    assert any("opt" in d["phrase"] for d in distilled["T2"]), distilled["T2"]
    assert any("train" in d["phrase"] for d in distilled["T1"]), distilled["T1"]


def test_degenerate_label_rejected():
    rows = [{"text": "Always training.", "section": "X", "items": ["T1"]} for _ in range(4)]
    try:
        train_sentence_classifier(rows)
    except ValueError as exc:
        assert "T1" in str(exc)
    else:
        raise AssertionError("expected ValueError for all-positive label")


if __name__ == "__main__":
    test_train_predict_distill()
    test_degenerate_label_rejected()
    print("ml tests passed")
