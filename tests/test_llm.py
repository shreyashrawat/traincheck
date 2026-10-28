"""LLM layer tests (stdlib only, fake client — no API key needed).

Run: python3 tests/test_llm.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.llm import (  # noqa: E402
    build_extraction_prompt,
    extract_with_client,
    verify_quotes,
)

DOC = "We may use your prompts to train our models by default. You can opt out in Settings."
ITEMS = [("T1", "Does the product train on user inputs by default?"),
         ("T2", "Can the user opt out of training, and where?"),
         ("T3", "Which inputs count for training?")]


def fake_client_factory(response):
    def client(prompt):
        assert "T1" in prompt and "We may use your prompts" in prompt
        return response
    return client


def test_verified_quote_accepted_hallucination_dropped():
    response = (
        '{"T1": {"quote": "We may use your prompts to train our models by default."}, '
        '"T2": {"quote": "You can never opt out of anything, ever."}, '
        '"T3": {"quote": null}}'
    )
    out = extract_with_client(fake_client_factory(response), DOC, ITEMS)
    assert out["results"]["T1"]["state"] == "stated", out
    assert out["results"]["T2"]["state"] == "not stated", out
    assert out["results"]["T2"]["quote"] is None, out
    assert out["dropped"]["T2"] == "quote not found verbatim in source", out
    assert out["results"]["T3"]["state"] == "not stated", out


def test_whitespace_normalized_quote_still_verifies():
    verified, dropped = verify_quotes(DOC, {"T1": "We  may use\nyour prompts to train our models by default."})
    assert verified["T1"] and not dropped, (verified, dropped)


def test_garbled_response_abstains_everything():
    out = extract_with_client(fake_client_factory("not json at all"), DOC, ITEMS)
    assert all(r["state"] == "not stated" for r in out["results"].values()), out
    assert out["dropped"] == {}, out


def test_prompt_contains_items_and_policy():
    prompt = build_extraction_prompt(DOC, ITEMS)
    assert "NOT STATED" in prompt and "T2" in prompt and DOC in prompt


if __name__ == "__main__":
    test_verified_quote_accepted_hallucination_dropped()
    test_whitespace_normalized_quote_still_verifies()
    test_garbled_response_abstains_everything()
    test_prompt_contains_items_and_policy()
    print("llm tests passed")
