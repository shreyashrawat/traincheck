"""Score + plain-language tests. Run: python3 tests/test_score_plain.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.detectors import detect_all  # noqa: E402
from traincheck.parse import parse_document  # noqa: E402
from traincheck.plain import bottom_line, next_actions, plain_problem  # noqa: E402
from traincheck.score import compare_scores, transparency_score  # noqa: E402


def _sample():
    text = (Path(__file__).resolve().parent.parent
            / "samples" / "sample_policy.txt").read_text(encoding="utf-8")
    return detect_all(parse_document(text))


def test_sample_score():
    sc = transparency_score(_sample())
    # T: T1 contradictory (0) + T2-T6 stated (5 x 2) = 10; C: C1-C9 stated (9),
    # C10 not stated (0) = 9; total 19/22 -> 8.6.
    assert sc["score"] == 8.6, sc
    assert sc["label"] == "Clear", sc
    assert sc["training"]["clear"] == 5 and sc["training"]["total"] == 6
    assert sc["basics"]["clear"] == 9 and sc["basics"]["total"] == 10


def test_weighting_and_labels():
    def fake(t_state, c_state):
        r = {f"T{i}": {"state": t_state} for i in range(1, 7)}
        r.update({f"C{i}": {"state": c_state} for i in range(1, 11)})
        return r
    assert transparency_score(fake("stated", "stated"))["score"] == 10.0
    assert transparency_score(fake("not stated", "not stated"))["score"] == 0.0
    assert transparency_score(fake("not stated", "not stated"))["label"] == "Vague"
    # Training-only stated: 12/22 -> 5.5 (Patchy), not the unweighted 3.8.
    mid = transparency_score(fake("stated", "not stated"))
    assert mid["score"] == 5.5 and mid["label"] == "Patchy", mid


def test_plain_problems():
    sample = _sample()
    assert plain_problem("T1", sample["T1"]) == \
        "Says two different things about whether it trains on your data."
    assert plain_problem("C10", sample["C10"]) == "Doesn't say children and contact details."
    assert plain_problem("T2", sample["T2"]) is None
    assert plain_problem("T3", {"state": "partially stated"}) == \
        "Only vaguely covers what data it trains on."


def test_bottom_line_and_actions_sample():
    sample = _sample()
    bl = bottom_line(sample)
    assert "two different things" in bl, bl
    assert "You can opt out:" in bl, bl
    titles = [a["title"] for a in next_actions(sample, transparency_score(sample))]
    assert titles == ["Don't trust either clause yet", "Turn training off"], titles


def test_actions_trains_no_optout():
    results = detect_all(parse_document(
        "We use your prompts to train our models. We collect your email address."))
    assert results["T1"]["state"] == "stated" and results["T1"]["value"] == "trains"
    titles = [a["title"] for a in next_actions(results, transparency_score(results))]
    assert "Share less" in titles, titles
    assert "Turn training off" not in titles


def test_compare():
    sample = _sample()
    empty = detect_all(parse_document("This document says nothing relevant."))
    cmp = compare_scores(sample, empty)
    assert cmp["better"] == "A" and cmp["a"] == 8.6 and cmp["b"] == 0.0, cmp
    assert compare_scores(sample, sample)["better"] == "tie"


if __name__ == "__main__":
    test_sample_score()
    test_weighting_and_labels()
    test_plain_problems()
    test_bottom_line_and_actions_sample()
    test_actions_trains_no_optout()
    test_compare()
    print("score/plain tests passed")
