"""Viz tests. Run: python3 tests/test_viz.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traincheck.viz import bar_html, donut_html, hero_css  # noqa: E402


def test_donut():
    counts = {"stated": 14, "partially stated": 0, "contradictory": 1, "not stated": 1}
    html = donut_html(counts, 8.6, "Clear")
    assert "conic-gradient" in html, html
    assert "8.6" in html and "Clear" in html, html
    # Text legend, not color-only: counts in words.
    assert "14 clearly stated" in html, html
    assert "1 contradictory" in html, html
    assert "1 not stated" in html, html
    # Green segment dominates: 14/16 = 87.5%.
    assert "#22c55e 0.0% 87.5%" in html, html


def test_bar():
    assert "width:50%" in bar_html(0.5), bar_html(0.5)
    assert "width:100%" in bar_html(2.0)  # clamped
    assert "width:0%" in bar_html(-1.0)  # clamped


def test_hero_css():
    assert "tc-hero-num" in hero_css()


if __name__ == "__main__":
    test_donut()
    test_bar()
    test_hero_css()
    print("viz tests passed")
