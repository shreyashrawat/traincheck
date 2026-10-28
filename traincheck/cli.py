"""TrainCheck CLI: audit a pasted policy file or URL, print a quote-anchored report."""

import argparse
import html
import json
import re
import sys
import urllib.request

from .detectors import detect_all
from .parse import parse_document
from .report import render_markdown


def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "TrainCheck/0.1 (research prototype)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
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
    args = ap.parse_args(argv)
    text = fetch_url(args.url) if args.url else open(args.text, encoding="utf-8").read()
    doc = parse_document(text)
    results = detect_all(doc)
    if args.json:
        print(json.dumps({"effective_date": doc["effective_date"], "items": results}, indent=2))
    else:
        print(render_markdown(doc, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
