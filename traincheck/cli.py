"""TrainCheck CLI: audit a pasted policy file or URL, print a quote-anchored report."""

import argparse
import html
import json
import re
import sys
import urllib.request

from .clients import client_from_env
from .decisions import audit_manifest, build_decision_records
from .detectors import detect_all
from .gapfill import gapfill_doc_results
from .parse import parse_document
from .plain import bottom_line, next_actions
from .report import render_markdown
from .score import transparency_score


def fetch_url(url):
    # A real browser user-agent: many policy pages (behind Cloudflare etc.)
    # reject obviously-automated clients outright. Note the honest limit:
    # some hosts also block datacenter IPs (e.g. Streamlit Cloud), in which
    # case no user-agent helps and the caller must fall back to pasted text.
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/126.0.0.0 Safari/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "This site blocks automated fetching (HTTP 403). Open the policy "
                "in your browser, copy the text, and paste it into the text box "
                "instead — the audit works the same from pasted text.") from exc
        raise
    # Drop boilerplate containers before stripping tags, so nav menus don't
    # collapse into giant pseudo-sentences.
    for tag in ("script", "style", "nav", "header", "footer", "noscript"):
        raw = re.sub(rf"<{tag}\b.*?</{tag}>", " ", raw, flags=re.S | re.I)
    # Preserve headings as Markdown so the parser can section the document.
    for level in (1, 2, 3):
        raw = re.sub(rf"<h{level}\b[^>]*>(.*?)</h{level}>", rf"\n{'#' * level} \1\n", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    text = html.unescape(raw)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(prog="traincheck")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="path to a plain-text policy file")
    group.add_argument("--url", help="policy URL to fetch")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON")
    ap.add_argument("--gapfill", action="store_true",
                    help="LLM gap-fill for unresolved items (needs OPENAI_API_KEY)")
    args = ap.parse_args(argv)
    text = fetch_url(args.url) if args.url else open(args.text, encoding="utf-8").read()
    doc = parse_document(text)
    results = detect_all(doc)
    models = {}
    if args.gapfill:
        client, model_name = client_from_env()
        if client is None:
            print("gap-fill needs OPENAI_API_KEY in the environment", file=sys.stderr)
            return 2
        results, diag = gapfill_doc_results(results, doc, text, client, model_name)
        models = {"llm": model_name, "gapfill": diag}
    if args.json:
        sc = transparency_score(results)
        print(json.dumps({
            "effective_date": doc["effective_date"],
            "score": sc,
            "bottom_line": bottom_line(results),
            "actions": next_actions(results, sc),
            "items": results,
            "decisions": build_decision_records(results),
            "manifest": audit_manifest([text], models),
        }, indent=2))
    else:
        print(render_markdown(doc, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
