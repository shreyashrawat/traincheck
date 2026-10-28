"""Live model clients for the LLM gap-fill layer (stdlib only).

No API key is stored in the repo or in code. Keys come from the
environment (local runs, CI) or Streamlit secrets (deployed app).
The client is a plain callable(prompt) -> str, so tests can substitute
a fake and the gap-fill layer never depends on a vendor SDK.

Determinism settings for live calls: temperature 0, top_p 1, and a
fixed seed where the endpoint supports it. Note the honest caveat:
hosted APIs do not guarantee bit-for-bit reproducibility even at
temperature 0 (batching, kernel nondeterminism, model updates), so the
pipeline pins the model version and treats the *verified quote set* as
the decision input — the decision function over verified quotes is
deterministic, and the manifest records model + prompt version so any
run can be audited.
"""

import json
import os
import urllib.request

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


def openai_compatible_client(api_key, model=DEFAULT_MODEL,
                             base_url=DEFAULT_BASE_URL, timeout=60):
    """Return a callable(prompt) -> str hitting a /chat/completions endpoint.

    The seed parameter is only sent to the default OpenAI endpoint, since
    other OpenAI-compatible endpoints may reject unknown fields.
    """
    url = base_url.rstrip("/") + "/chat/completions"

    def call(prompt):
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "top_p": 1,
        }
        if base_url.rstrip("/") == DEFAULT_BASE_URL:
            body["seed"] = 0
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"model API error {exc.code}: {detail}") from exc
        return payload["choices"][0]["message"]["content"]

    return call


def client_from_env():
    """Build a client from the environment. Returns (client, model) or
    (None, None) when no key is configured — the caller must handle that
    by skipping gap-fill, never by asking for a key in chat."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, None
    model = os.environ.get("TRAINCHECK_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("TRAINCHECK_BASE_URL", DEFAULT_BASE_URL)
    return openai_compatible_client(api_key, model, base_url), model
