"""Evaluation harness tests (stdlib only). Run: python3 tests/test_evaluate.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.evaluate import (  # noqa: E402
    annotator_agreement,
    cohen_kappa,
    per_item_accuracy,
    summarize,
)


def test_per_item_accuracy():
    gold = {"p1": {"T1": "stated", "T2": "not stated"}}
    pred = {"p1": {"T1": "stated", "T2": "stated"}}
    acc = per_item_accuracy(gold, pred)
    assert acc["T1"] == 1.0 and acc["T2"] == 0.0 and acc["overall"] == 0.5, acc


def test_missing_prediction_counts_as_mismatch():
    gold = {"p1": {"T1": "stated"}}
    acc = per_item_accuracy(gold, {})
    assert acc["T1"] == 0.0, acc


def test_cohen_kappa_known_value():
    # po = 2/3, pe = 4/9, kappa = 0.4
    assert abs(cohen_kappa(["s", "s", "n"], ["s", "n", "n"]) - 0.4) < 1e-9
    assert cohen_kappa(["s", "n"], ["s", "n"]) == 1.0


def test_annotator_agreement():
    a = {("p1", "T1"): "stated", ("p1", "T2"): "not stated"}
    b = {("p1", "T1"): "stated", ("p1", "T2"): "stated"}
    out = annotator_agreement(a, b)
    assert out["pairs"] == 2 and out["agreement"] == 0.5, out


def test_summarize_shape():
    gold = {"p1": {"T1": "stated"}}
    pred = {"p1": {"T1": "stated"}}
    rep = summarize(gold, pred)
    assert rep["accuracy"]["overall"] == 1.0
    assert rep["confusion"]["T1"][("stated", "stated")] == 1


if __name__ == "__main__":
    test_per_item_accuracy()
    test_missing_prediction_counts_as_mismatch()
    test_cohen_kappa_known_value()
    test_annotator_agreement()
    test_summarize_shape()
    print("evaluate tests passed")
